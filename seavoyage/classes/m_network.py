# MNetwork.py
import os
import geojson
import networkx as nx
import numpy as np
from shapely import LineString
from sklearn.neighbors import NearestNeighbors
from scipy.spatial import Delaunay
from typing import Optional

from searoute import Marnet
from searoute.utils import distance
from seavoyage.modules.restriction import CustomRestriction
from seavoyage.utils.coordinates import decdeg_to_degmin
from seavoyage.utils.shapely_utils import is_valid_edge
from seavoyage.log import logger
from searoute.classes.passages import Passage
from seavoyage.exceptions import (
    UnreachableDestinationError, 
    StartInRestrictionError, 
    DestinationInRestrictionError,
    IsolatedOriginError
)
from seavoyage.utils.shoreline import shoreline

class MNetwork(Marnet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 커스텀 제한 구역 저장 딕셔너리
        self.custom_restrictions: dict[str, CustomRestriction] = {}
        # 초기 제한 구역 상태 저장
        self._initial_restrictions = [Passage.northwest]

    def reset_restrictions(self):
        """
        모든 제한 구역을 초기 상태로 초기화합니다.
        커스텀 제한 구역은 모두 제거하고, 
        기본 제한 구역은 초기 상태로 되돌립니다.
        """
        # 기본 제한 구역 초기화
        self.restrictions = self._initial_restrictions.copy() if hasattr(self, '_initial_restrictions') else []
        
        # 커스텀 제한 구역 초기화
        self.custom_restrictions.clear()
        
        logger.debug(f"제한 구역이 초기화되었습니다: 기본={self.restrictions}, 커스텀={list(self.custom_restrictions.keys())}")
        
    def save_initial_state(self):
        """
        현재 기본 제한 구역 상태를 초기 상태로 저장합니다.
        """
        self._initial_restrictions = self.restrictions.copy() if hasattr(self, 'restrictions') else []
        logger.debug(f"초기 제한 구역 상태 저장: {self._initial_restrictions}")

    def add_node_with_edges(self, node: tuple[float, float], threshold: float = 100.0, land_polygon = None):
        """
        새로운 노드를 추가하고 임계값 내의 기존 노드들과 자동으로 엣지를 생성합니다.
        :param node: 추가할 노드의 (longitude, latitude) 좌표
        :param threshold: 엣지를 생성할 거리 임계값(km)
        :param land_polygon: 육지 폴리곤 (shapely MultiPolygon)
        :return: 생성된 엣지들의 리스트 [(node1, node2, weight), ...]
        """
        if threshold <= 0 or not isinstance(threshold, (int, float)):
            raise ValueError("Threshold must be a positive number.")
        
        if not isinstance(node, tuple) or len(node) != 2:
            raise TypeError("Node must be a tuple of (longitude, latitude).")
        
        if node in self.nodes:
            return []
        
        # 노드 추가
        self.add_node(node)
        
        # 생성된 엣지들을 저장할 리스트
        created_edges = []
        
        # 기존 노드들과의 거리를 계산하고 임계값 이내인 경우 엣지 생성
        for existing_node in list(self.nodes):
            if existing_node == node:
                continue
                
            dist = distance(node, existing_node, units="km")
            if dist <= threshold:
                # 육지 폴리곤이 주어진 경우, 엣지가 육지를 통과하는지 검사
                if land_polygon:
                    line = LineString([node, existing_node])
                    if not is_valid_edge(line, land_polygon):
                        continue
                
                self.add_edge(node, existing_node, weight=dist)
                created_edges.append((node, existing_node, dist))
                
        return created_edges

    # ② add_node_and_connect ------------------------------------
    # TODO: KNN 적용되지 않는 문제 해결
    def add_node_and_connect(
        self,
        new_node: tuple[float, float],
        k: int = 5,
        land_polygon = shoreline,
    ):
        # 0) 경도 정규화(선택) + 노드 등록
        new_node = self._norm_coord(new_node)
        if new_node not in self:
            self.add_node(new_node)

        created_edges: list[tuple] = []
        coords = np.array(list(self.nodes))

        if len(coords) <= 1:
            self.update_kdtree()
            return created_edges

        # 1) KNN ------------------------------------------------------
        coords_aug, idx_map = self._augment_coords(coords)
        new_node_aug = np.array(new_node)          # 동일 좌표계

        nbrs = NearestNeighbors(
            n_neighbors=min(k + 1, len(coords_aug)),
            algorithm="ball_tree",
        ).fit(coords_aug)

        dists, inds = nbrs.kneighbors([new_node_aug])

        for aug_idx in inds[0][1:]:                # 자기 자신 제외
            neighbor = tuple(coords[idx_map[aug_idx]])
            if neighbor == new_node:               # 동일 노드 스킵
                continue

            line = LineString([new_node, neighbor])
            if land_polygon and not is_valid_edge(line, land_polygon):
                continue

            w = float(distance(new_node, neighbor, units="km"))
            if not self.has_edge(new_node, neighbor):
                self.add_edge(new_node, neighbor, weight=w)
                created_edges.append((new_node, neighbor, w))

        # 2) Delaunay -------------------------------------------------
        if len(coords) >= 3:
            coords_with_new = np.vstack([coords, new_node])  # 원본 좌표만
            try:
                tri = Delaunay(coords_with_new)
                idx_new = len(coords_with_new) - 1

                for simplex in tri.simplices:
                    if idx_new not in simplex:
                        continue
                    for i in range(3):
                        for j in range(i + 1, 3):
                            a, b = simplex[i], simplex[j]
                            if idx_new not in (a, b):
                                continue
                            n1 = tuple(coords_with_new[a])
                            n2 = tuple(coords_with_new[b])

                            if self.has_edge(n1, n2):
                                continue
                            line = LineString([n1, n2])
                            if land_polygon and not is_valid_edge(line, land_polygon):
                                continue

                            w = float(distance(n1, n2, units="km"))
                            self.add_edge(n1, n2, weight=w)
                            created_edges.append((n1, n2, w))
            except Exception as e:
                logger.error(f"Delaunay 오류: {e}")

        # 3) 마무리 ----------------------------------------------------
        self.update_kdtree()
        logger.info(f"신규 엣지 {len(created_edges)}개 생성")
        return created_edges


    def add_nodes_with_edges(self, nodes: list[tuple[float, float]], threshold: float = 100.0, land_polygon = None):
        """
        여러 노드들을 추가하고 임계값 내의 모든 노드들(기존 + 새로운)과 자동으로 엣지를 생성합니다.

        :param nodes: 추가할 노드들의 [(longitude, latitude), ...] 좌표 리스트
        :param threshold: 엣지를 생성할 거리 임계값(km)
        :param land_polygon: 육지 폴리곤 (shapely MultiPolygon)
        :return: 생성된 엣지들의 리스트 [(node1, node2, weight), ...]
        """
        if not isinstance(nodes, list):
            raise TypeError("Nodes must be a list of tuples representing the coordinates.")
        if threshold <= 0 or not isinstance(threshold, (int, float)):
            raise ValueError("Threshold must be a positive number.")
        
        if any(not isinstance(node, tuple) or len(node) != 2 for node in nodes):
            raise TypeError("Each node must be a tuple of (longitude, latitude).")
        
        all_created_edges = []
        
        # 각 새로운 노드에 대해 처리
        for node in nodes:
            # 기존 노드들과의 엣지 생성 (육지 통과 검사 포함)
            edges = self.add_node_with_edges(node, threshold, land_polygon)
            all_created_edges.extend(edges)
            
            # 이미 추가된 새로운 노드들과의 엣지 생성 (육지 통과 검사 없음)
            for other_node in nodes:
                if other_node == node or other_node not in self.nodes:
                    continue
                    
                dist = distance(node, other_node, units="km")
                if dist <= threshold:
                    self.add_edge(node, other_node, weight=dist)
                    all_created_edges.append((node, other_node, dist))
                    
        logger.debug(f"Added {len(all_created_edges)} edges")
        return all_created_edges

    def _extract_point_coordinates(self, point: geojson.Point):
        """
        GeoJSON Point 객체에서 좌표를 추출합니다.

        :param point: 좌표를 추출할 Point 객체
        :return: (longitude, latitude) 좌표
        """
        if isinstance(point, dict):
            coords = point["coordinates"]
        elif isinstance(point, geojson.Point):
            coords = point.coordinates
        else:
            raise TypeError("Invalid point type. Must be a geojson.Point or dict.")
        
        if not coords or len(coords) < 2:
            raise ValueError("Invalid point coordinates")
        
        return tuple(coords[:2])  # (longitude, latitude)
    
    def add_geojson_point(self, point, threshold: float = 100.0):
        """
        GeoJSON Point 객체를 노드로 추가하고 임계값 내의 노드들과 엣지를 생성합니다.
        :param point: 추가할 Point 객체
        :param threshold: 엣지를 생성할 거리 임계값(km)
        :return: 생성된 엣지들의 리스트
        """
        coords = self._extract_point_coordinates(point)
        return self.add_node_with_edges(coords, threshold)

    def add_geojson_multipoint(self, multipoint, threshold: float = 100.0):
        """
        GeoJSON MultiPoint 객체의 모든 점들을 노드로 추가하고 임계값 내의 노드들과 엣지를 생성합니다.
        :param multipoint: 추가할 MultiPoint 객체
        :param threshold: 엣지를 생성할 거리 임계값(km)
        :return: 생성된 엣지들의 리스트
        """
        #TODO: 최적화 필요
        if isinstance(multipoint, dict):
            coords = multipoint.get('coordinates', [])
        else:
            coords = multipoint.coordinates
            
        nodes = [tuple(coord[:2]) for coord in coords]
        return self.add_nodes_with_edges(nodes, threshold)

    def add_geojson_feature_collection(self, feature_collection, threshold: float = 100.0, land_polygon = None):
        """
        GeoJSON FeatureCollection의 Point와 LineString 피처들을 노드와 엣지로 추가합니다.
        :param feature_collection: Point 또는 LineString 피처들을 포함한 FeatureCollection 객체
        :param threshold: 엣지를 생성할 거리 임계값(km)
        :param land_polygon: 육지 폴리곤 (shapely MultiPolygon)
        :return: 생성된 엣지들의 리스트
        """
        if isinstance(feature_collection, dict):
            features = feature_collection.get('features', [])
        else:
            features = feature_collection.features

        nodes = []
        direct_edges = []  # LineString에서 직접 추출한 엣지들을 저장할 리스트
        
        for feature in features:
            if isinstance(feature, dict):
                geometry = feature.get('geometry', {})
                properties = feature.get('properties', {})
                
                if geometry.get('type') == 'Point':
                    coords = geometry.get('coordinates')
                    if coords and len(coords) >= 2:
                        nodes.append(tuple(coords[:2]))
                        
                elif geometry.get('type') == 'LineString':
                    # LineString 처리
                    coords = geometry.get('coordinates')
                    if coords and len(coords) >= 2:
                        # LineString의 각 좌표를 노드로 추가
                        line_nodes = [tuple(coord[:2]) for coord in coords]
                        nodes.extend(line_nodes)
                        
                        # LineString의 연속된 좌표 사이에 직접 엣지 생성
                        for i in range(len(line_nodes) - 1):
                            node1 = line_nodes[i]
                            node2 = line_nodes[i + 1]
                            
                            # 가중치 계산 (properties에서 가져오거나 거리 계산)
                            if 'weight' in properties:
                                weight = properties['weight']
                            else:
                                weight = distance(node1, node2, units="km")
                                
                            direct_edges.append((node1, node2, weight, properties))
            else:
                geometry = feature.geometry
                properties = feature.properties if hasattr(feature, 'properties') else {}
                
                if isinstance(geometry, geojson.Point):
                    coords = geometry.coordinates
                    if coords and len(coords) >= 2:
                        nodes.append(tuple(coords[:2]))
                        
                elif isinstance(geometry, geojson.LineString):
                    # LineString 처리
                    coords = geometry.coordinates
                    if coords and len(coords) >= 2:
                        # LineString의 각 좌표를 노드로 추가
                        line_nodes = [tuple(coord[:2]) for coord in coords]
                        nodes.extend(line_nodes)
                        
                        # LineString의 연속된 좌표 사이에 직접 엣지 생성
                        for i in range(len(line_nodes) - 1):
                            node1 = line_nodes[i]
                            node2 = line_nodes[i + 1]
                            
                            # 가중치 계산 (properties에서 가져오거나 거리 계산)
                            if hasattr(properties, 'weight') or (isinstance(properties, dict) and 'weight' in properties):
                                weight = properties.get('weight') if isinstance(properties, dict) else properties.weight
                            else:
                                weight = distance(node1, node2, units="km")
                                
                            direct_edges.append((node1, node2, weight, properties))
        
        # 노드들 추가 및 임계값 내 엣지 생성
        all_created_edges = self.add_nodes_with_edges(nodes, threshold, land_polygon)
        
        # LineString에서 직접 추출한 엣지들 추가
        for node1, node2, weight, props in direct_edges:
            if node1 in self.nodes and node2 in self.nodes:
                # 육지 폴리곤이 주어진 경우, 엣지가 육지를 통과하는지 검사
                if land_polygon:
                    line = LineString([node1, node2])
                    if not is_valid_edge(line, land_polygon):
                        continue
                
                # 엣지 속성 설정
                edge_attrs = {'weight': weight}
                
                # properties의 다른 속성들도 엣지 속성에 추가
                if isinstance(props, dict):
                    for key, value in props.items():
                        if key != 'weight':  # weight는 이미 설정했으므로 중복 방지
                            edge_attrs[key] = value
                
                # 엣지 추가
                self.add_edge(node1, node2, **edge_attrs)
                all_created_edges.append((node1, node2, weight))
        
        logger.debug(f"Total {len(all_created_edges)} edges added")
        return all_created_edges
    
    def to_geojson(self, file_path: str = None) -> geojson.FeatureCollection:
        """노드와 엣지를 GeoJSON 형식으로 내보냅니다."""
        features = []
        
        for u, v, attrs in self.edges(data=True):
            line = geojson.LineString([[u[0], u[1]], [v[0], v[1]]])
            feature = geojson.Feature(geometry=line, properties=attrs)
            features.append(feature)
            
        feature_collection = geojson.FeatureCollection(features)
        
        if file_path:
            with open(file_path, "w") as f:
                geojson.dump(feature_collection, f)
                
        return feature_collection
    
    def to_line_string(self) -> list[LineString]:
        """노드와 엣지를 LineString 객체로 내보냅니다."""
        linestrings = []
        for u, v, attrs in self.edges(data=True):
            linestrings.append(LineString([[u[0], u[1]], [v[0], v[1]]]))
        return linestrings
    
    @classmethod
    def from_geojson(cls, *args):
        """
        GeoJSON 파일 경로 또는 GeoJSON 객체로부터 MNetwork 객체를 생성합니다.
        
        Parameters
        ----------
        *args : 파일 경로 또는 GeoJSON 객체
            - 문자열: GeoJSON 파일 경로로 해석됩니다.
            - dict: GeoJSON 객체(사전)로 해석됩니다.
            - geojson.GeoJSON: GeoJSON 객체로 해석됩니다.
            
        Returns
        -------
        MNetwork 객체
        """
        mnetwork = cls()
        mnetwork = mnetwork.load_from_geojson(*args)
        mnetwork.update_kdtree()
        return mnetwork

    @staticmethod
    def _norm_coord(coord: tuple[float, float]) -> tuple[float, float]:
        lon, lat = coord
        lon = (lon + 180.0) % 360.0 - 180.0   # →  -180 ~ <180
        return lon, lat

    def load_from_geojson(self, *args):
        """
        GeoJSON 파일 경로 또는 GeoJSON 객체로부터 그래프를 로드합니다.
        Polygon, MultiPolygon 도 지원하며 모든 경도를 [-180, 180) 범위로
        정규화해서 날짜변경선 문제를 방지합니다.
        """
        # ── 내부 유틸 ────────────────────────────────────────────
        def _fix_coords(coords):
            """
            재귀적으로 좌표 배열을 순회하면서 (lon, lat) 튜플을
            self._norm_coord()로 정규화한 뒤 리스트로 반환
            """
            if coords is None:
                return coords

            # 단일 점 [lon, lat]
            if isinstance(coords[0], (int, float)):
                return list(self._norm_coord(tuple(coords)))

            # 중첩 리스트   [[...], [...]]
            return [_fix_coords(c) for c in coords]

        def _cast_dict_to_geo(obj_dict):
            """dict → geojson 객체로 변환 (LineString 등)"""
            gtype = obj_dict.get("type")
            return {
                "LineString":    geojson.LineString,
                "MultiLineString": geojson.MultiLineString,
                "Point":         geojson.Point,
                "MultiPoint":    geojson.MultiPoint,
                "Polygon":       geojson.Polygon,
                "MultiPolygon":  geojson.MultiPolygon,
            }.get(gtype, geojson.GeoJSON)(obj_dict["coordinates"])

        # ── 본체 ────────────────────────────────────────────────
        for arg in args:
            # 1) 파일 경로 or 객체 로드 ---------------------------------
            if isinstance(arg, str):
                if not os.path.exists(arg):
                    raise FileNotFoundError(f"GeoJSON 파일 없음: {arg}")
                with open(arg, "r") as f:
                    data = geojson.load(f)
            elif isinstance(arg, (dict, geojson.base.GeoJSON)):
                data = arg
            else:
                raise TypeError("str 경로 또는 GeoJSON/dict 만 허용")

            # 2) 좌표 정규화 & 그래프에 반영 -----------------------------
            def handle_geometry(geometry, properties):
                # dict → geojson 객체 변환
                if isinstance(geometry, dict):
                    geometry = _cast_dict_to_geo(geometry)

                # 좌표 정규화
                geometry["coordinates"] = _fix_coords(geometry["coordinates"])

                # 이후 기존 로직과 동일 --------------------------------
                gtype = geometry.type
                if gtype == "LineString":
                    coords = geometry.coordinates
                    for u, v in zip(coords[:-1], coords[1:]):
                        self.add_edge(tuple(u), tuple(v), **properties)
                        self.add_edge(tuple(v), tuple(u), **properties)
                elif gtype == "MultiLineString":
                    for line in geometry.coordinates:
                        for u, v in zip(line[:-1], line[1:]):
                            self.add_edge(tuple(u), tuple(v), **properties)
                            self.add_edge(tuple(v), tuple(u), **properties)
                elif gtype == "Point":
                    self.add_node(tuple(geometry.coordinates), **properties)
                elif gtype == "MultiPoint":
                    for pt in geometry.coordinates:
                        self.add_node(tuple(pt), **properties)
                elif gtype == "Polygon":
                    outer = geometry.coordinates[0]
                    for u, v in zip(outer[:-1], outer[1:]):
                        self.add_edge(tuple(u), tuple(v), **properties)
                        self.add_edge(tuple(v), tuple(u), **properties)
                    if outer[0] != outer[-1]:
                        self.add_edge(tuple(outer[-1]), tuple(outer[0]), **properties)
                        self.add_edge(tuple(outer[0]), tuple(outer[-1]), **properties)
                elif gtype == "MultiPolygon":
                    for poly in geometry.coordinates:
                        outer = poly[0]
                        for u, v in zip(outer[:-1], outer[1:]):
                            self.add_edge(tuple(u), tuple(v), **properties)
                            self.add_edge(tuple(v), tuple(u), **properties)
                        if outer[0] != outer[-1]:
                            self.add_edge(tuple(outer[-1]), tuple(outer[0]), **properties)
                            self.add_edge(tuple(outer[0]), tuple(outer[-1]), **properties)
                else:
                    logger.debug(f"Unsupported geometry type: {gtype}")

            # 3) Feature / FeatureCollection 구분 -----------------------
            dtype = data["type"] if isinstance(data, dict) else data.type
            if dtype == "FeatureCollection":
                # CRS
                crs_name = (data.get("crs", {})
                               .get("properties", {})
                               .get("name")) if isinstance(data, dict) else \
                           (getattr(getattr(data, "crs", None), "properties", None)
                               or {}).get("name")
                if crs_name:
                    self.graph["crs"] = crs_name

                feats = data["features"] if isinstance(data, dict) else data.features
                for feat in feats:
                    geom = feat["geometry"] if isinstance(feat, dict) else feat.geometry
                    props = feat.get("properties", {}) if isinstance(feat, dict) else feat.properties
                    handle_geometry(geom, props)
            elif dtype == "Feature":
                geom = data["geometry"] if isinstance(data, dict) else data.geometry
                props = data.get("properties", {}) if isinstance(data, dict) else data.properties
                handle_geometry(geom, props)
            else:  # geometry 단독
                handle_geometry(data, {})

        # 4) KD-Tree 갱신 ---------------------------------------------
        self.update_kdtree()
        return self
    
    @classmethod
    def from_networkx(cls, graph: nx.Graph):
        """
        NetworkX 그래프를 MNetwork 객체로 변환합니다.
        :param graph: NetworkX 그래프
        :return: MNetwork 객체
        """
        mnetwork = cls()
        # 모든 노드 추가
        for node, attrs in graph.nodes(data=True):
            # 노드가 (longitude, latitude) 형식의 튜플인지 확인
            if isinstance(node, tuple) and len(node) >= 2:
                mnetwork.add_node(node, **attrs)
            else:
                # 노드가 좌표 형식이 아닌 경우, x와 y 속성이 있는지 확인
                if 'x' in attrs and 'y' in attrs:
                    coords = (attrs['x'], attrs['y'])
                    mnetwork.add_node(coords, **{k: v for k, v in attrs.items() if k not in ['x', 'y']})
                else:
                    logger.debug(f"Skipping node {node} - no coordinate information")
        
        # 모든 엣지 추가
        for u, v, attrs in graph.edges(data=True):
            # 원본 그래프에서 노드가 좌표 형식이 아닌 경우 처리
            u_node = u
            v_node = v
            
            if not isinstance(u, tuple) and u in graph:
                attrs_u = graph.nodes[u]
                if 'x' in attrs_u and 'y' in attrs_u:
                    u_node = (attrs_u['x'], attrs_u['y'])
            
            if not isinstance(v, tuple) and v in graph:
                attrs_v = graph.nodes[v]
                if 'x' in attrs_v and 'y' in attrs_v:
                    v_node = (attrs_v['x'], attrs_v['y'])
            
            # 두 노드가 모두 좌표 형식인 경우에만 엣지 추가
            if isinstance(u_node, tuple) and isinstance(v_node, tuple):
                mnetwork.add_edge(u_node, v_node, **attrs)
            else:
                logger.debug(f"Skipping edge {u}-{v} - no coordinate information")
        
        # 그래프 속성 복사
        for key, value in graph.graph.items():
            mnetwork.graph[key] = value
        
        # KDTree 업데이트
        mnetwork.update_kdtree()
        
        return mnetwork
    
    @classmethod
    def from_marnet(cls, marnet_obj: "Marnet") -> "MNetwork":
        """기존 Marnet 객체를 MNetwork 객체로 변환"""
        if not isinstance(marnet_obj, Marnet):
            raise TypeError("marnet_obj must be an instance of Marnet")

        mnetwork = cls.from_networkx(marnet_obj)

        mnetwork.restrictions = list(getattr(marnet_obj, "restrictions", []))
        mnetwork.custom_restrictions = dict(
            getattr(marnet_obj, "custom_restrictions", {})
        )

        mnetwork.update_kdtree()

        return mnetwork
    
    def add_restriction(self, restriction: CustomRestriction):
        """
        커스텀 제한 구역 추가
        
        Args:
            restriction: CustomRestriction 객체
        """
        self.custom_restrictions[restriction.name] = restriction
        logger.debug(f"Restriction added: {restriction.name}")
        
    def remove_restriction(self, name: str):
        """
        커스텀 제한 구역 제거
        
        Args:
            name: 제한 구역 이름
        """
        if name in self.custom_restrictions:
            del self.custom_restrictions[name]
    
    def _filter_custom_restricted_edge(self, u, v, data):
        """커스텀 제한 구역과 교차하는 엣지 필터링"""
        # 간선을 LineString으로 변환
        line = LineString([u, v])
        
        # 기존 제한 구역 필터링 
        restrictions_passed = data.get('passage')
        logger.debug(f"엣지 {u} -> {v}의 passage 정보: {restrictions_passed}")
        
        if isinstance(restrictions_passed, str):
            # 단일 passage인 경우
            if restrictions_passed in self.restrictions:
                logger.debug(f"엣지 {u} -> {v}가 기본 제한 구역 '{restrictions_passed}'와 교차")
                return False
        elif isinstance(restrictions_passed, list):
            # 여러 passage가 있는 경우, 하나라도 제한 구역에 해당하면 필터링
            for passage in restrictions_passed:
                if passage in self.restrictions:
                    logger.debug(f"엣지 {u} -> {v}가 기본 제한 구역 '{passage}'와 교차")
                    return False
        
        # 커스텀 제한 구역 필터링
        for name, restriction in self.custom_restrictions.items():
            # 선분이 제한 구역과 교차하거나 완전히 포함되는 경우
            if restriction.polygon.intersects(line) or restriction.polygon.contains(line):
                logger.debug(f"엣지 {u} -> {v}가 커스텀 제한 구역 '{name}'과 교차 또는 포함")
                return False
                
        # 모든 제한 구역을 통과하지 않는 경우
        logger.debug(f"엣지 {u} -> {v}는 모든 제한 구역을 통과하지 않음")
        return True
    
    def is_point_in_restriction(self, point: tuple) -> tuple[bool, Optional[str]]:
        """
        주어진 점이 제한 구역 내에 있는지 확인합니다.
        
        Args:
            point: (경도, 위도) 좌표
            
        Returns:
            tuple[bool, Optional[str]]: (점이 제한 구역 내에 있으면 True, 제한 구역 이름) 또는 (False, None)
        """
        # 명시적으로 custom_restrictions의 타입을 지정
        restrictions: dict[str, CustomRestriction] = self.custom_restrictions
        for name, restriction in restrictions.items():
            if restriction.contains_point(point):
                return True, name
        return False, None
    
    def shortest_path(self, origin, destination, method = "astar") -> list:
        """
        제한 구역을 피해 출발지와 목적지 사이의 최단 경로 계산
        
        Args:
            origin: 출발지 좌표 (경도, 위도)
            destination: 목적지 좌표 (경도, 위도)
            method: 경로 탐색 방법 (기본값: "dijkstra", "astar"도 가능)
        Returns:
            List: 최단 경로의 노드 리스트
            
        Raises:
            ValueError: 알고리즘이 'dijkstra'나 'astar'가 아닌 경우
            UnreachableDestinationError: 제한 구역으로 인해 목적지에 도달할 수 없는 경우
            StartInRestrictionError: 출발지가 제한 구역 내에 있는 경우
            DestinationInRestrictionError: 목적지가 제한 구역 내에 있는 경우
            IsolatedOriginError: 출발지가 제한 구역에 의해 고립되어 있는 경우
        """
        # 디버깅 로그 추가
        logger.debug(f"시작 좌표: {origin}, 목적지 좌표: {destination}")
        logger.debug(f"현재 적용된 기본 제한 구역: {self.restrictions}")
        logger.debug(f"현재 적용된 커스텀 제한 구역: {list(self.custom_restrictions.keys())}")
        
        # 출발점이 제한구역에 있는지 확인
        is_origin_restricted, origin_restriction = self.is_point_in_restriction(origin)
        if is_origin_restricted:
            logger.debug(f"출발점 {decdeg_to_degmin(origin)}이 제한 구역 '{origin_restriction}' 내에 있습니다")
            raise StartInRestrictionError(origin, origin_restriction)
            
        # 도착점이 제한구역에 있는지 확인
        is_dest_restricted, dest_restriction = self.is_point_in_restriction(destination)
        if is_dest_restricted:
            logger.debug(f"도착점 {decdeg_to_degmin(destination)}이 제한 구역 '{dest_restriction}' 내에 있습니다")
            raise DestinationInRestrictionError(destination, dest_restriction)
        
        if method not in ("dijkstra", "astar"):
            raise ValueError("Method must be either 'dijkstra' or 'astar'.")
        
        # KDTree에서 가장 가까운 노드 찾기
        origin_node = self.kdtree.query(origin)
        destination_node = self.kdtree.query(destination)
        
        # 출발점과 KDTree로 찾은 노드 사이의 선분이 제한 구역을 통과하는지 확인
        if origin != origin_node:  # 출발점과 네트워크 노드가 다른 경우
            line_to_origin = LineString([origin, origin_node])
            logger.debug(f"출발점 {origin}에서 가장 가까운 네트워크 노드: {origin_node}")
            
            # 커스텀 제한 구역 확인
            for name, restriction in self.custom_restrictions.items():
                if restriction.polygon.intersects(line_to_origin):
                    logger.debug(f"출발점 {origin}에서 가장 가까운 노드 {origin_node}까지의 경로가 제한 구역 '{name}'와 교차합니다")
                    raise IsolatedOriginError(origin, [name])
        
        # 이웃 노드 수 로깅
        neighbors = list(self.neighbors(origin_node))
        logger.debug(f"출발점 노드 {origin_node}의 이웃 노드 수: {len(neighbors)}")
        
        # 커스텀 제한 구역을 고려한 가중치 함수
        def custom_weight(u, v, data):
            is_valid = self._filter_custom_restricted_edge(u, v, data)
            if is_valid:
                weight = distance(u, v)
                return data.get('weight', weight)
            else:
                return float('inf')
        
        # 출발지 노드가 고립되었는지 확인
        is_isolated = True
        logger.debug(f"출발점 노드 {origin_node}의 고립 여부 검사 시작")
        
        for neighbor in neighbors:
            edge_data = self.get_edge_data(origin_node, neighbor)
            is_valid_edge = self._filter_custom_restricted_edge(origin_node, neighbor, edge_data)
            logger.debug(f"  - 이웃 노드 {neighbor}: 유효한 경로 = {is_valid_edge}")
            
            if is_valid_edge:
                is_isolated = False
                break
        
        if is_isolated:
            logger.debug(f"출발점 {origin}이 제한 구역에 의해 고립되어 있습니다")
            restriction_names = list(self.custom_restrictions.keys())
            if self.restrictions:
                restriction_names.extend([str(r) for r in self.restrictions])
            raise IsolatedOriginError(origin, restriction_names)
        
        try:
            if method == "dijkstra":
                result = nx.shortest_path(self, origin_node, destination_node, weight=custom_weight)
            elif method == "astar":
                result = nx.astar_path(self, origin_node, destination_node, weight=custom_weight)
            logger.debug(f"경로 탐색 성공: {len(result)} 노드")
            return result
        except nx.NetworkXNoPath:
            # NetworkX에서 경로를 찾지 못한 경우
            logger.debug(f"경로를 찾을 수 없습니다: {origin} -> {destination}")
            restriction_names = list(self.custom_restrictions.keys())
            if self.restrictions:
                restriction_names.extend([str(r) for r in self.restrictions])
            raise UnreachableDestinationError(origin, destination, restriction_names)
        
    # ① 경도 복제 헬퍼 ------------------------------------------
    @staticmethod
    def _augment_coords(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        coords: (N,2)  [lon, lat]
        return:
            coords_aug : (3N,2)  경도 ±360° 로 확장
            idx_map    : (3N,)   각 복제행이 가리키는 원본 좌표 인덱스
        """
        lons, lats = coords[:, 0], coords[:, 1]
        coords_minus = np.column_stack((lons - 360.0, lats))
        coords_plus  = np.column_stack((lons + 360.0, lats))

        coords_aug = np.vstack([coords, coords_minus, coords_plus])
        idx_map    = np.tile(np.arange(len(coords)), 3)

        return coords_aug, idx_map
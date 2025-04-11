# MNetwork.py
import geojson
import networkx as nx
from searoute import Marnet
from searoute.utils import distance, load_from_geojson as sr_load_from_geojson
from shapely import LineString
from seavoyage.utils.shapely_utils import is_valid_edge
import os

class MNetwork(Marnet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
                    
        print(f"Added {len(all_created_edges)} edges")
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
        
        print(f"총 {len(all_created_edges)}개의 엣지가 추가되었습니다.")
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
        return mnetwork.load_from_geojson(*args)

    def load_from_geojson(self, *args):
        """
        GeoJSON 파일 경로 또는 GeoJSON 객체로부터 그래프를 로드합니다.
        기존 searoute의 load_from_geojson에 Polygon 타입 지원을 추가했고,
        GeoJSON 객체를 직접 입력받을 수 있습니다.
        
        Parameters
        ----------
        *args : 파일 경로 또는 GeoJSON 객체
            - 문자열: GeoJSON 파일 경로로 해석됩니다.
            - dict: GeoJSON 객체(사전)로 해석됩니다.
            - geojson.GeoJSON: GeoJSON 객체로 해석됩니다.
            
        Returns
        -------
        MNetwork 객체 (self)
        """
        for arg in args:
            # 파일 경로인 경우 파일에서 데이터를 로드
            if isinstance(arg, str):
                if not os.path.exists(arg):
                    raise FileNotFoundError(f"GeoJSON 파일을 찾을 수 없습니다: {arg}")
                with open(arg, 'r') as f:
                    data = geojson.load(f)
            # dict 또는 geojson 객체인 경우 직접 사용
            elif isinstance(arg, (dict, geojson.base.GeoJSON)):
                data = arg
            else:
                raise TypeError(f"지원하지 않는 인자 타입입니다: {type(arg)}. 문자열 경로 또는 GeoJSON 객체가 필요합니다.")

            def handle_geometry(geometry, properties):
                # 문자열이나 dict 타입의 geometry를 geojson 객체로 변환
                if isinstance(geometry, dict):
                    geo_type = geometry.get('type')
                    coords = geometry.get('coordinates')
                    
                    # dict 형태의 geometry를 적절한 geojson 타입으로 변환
                    if geo_type == 'LineString':
                        geometry = geojson.LineString(coords)
                    elif geo_type == 'MultiLineString':
                        geometry = geojson.MultiLineString(coords)
                    elif geo_type == 'Point':
                        geometry = geojson.Point(coords)
                    elif geo_type == 'MultiPoint':
                        geometry = geojson.MultiPoint(coords)
                    elif geo_type == 'Polygon':
                        geometry = geojson.Polygon(coords)
                    elif geo_type == 'MultiPolygon':
                        geometry = geojson.MultiPolygon(coords)
                
                if not hasattr(geometry, 'type'):
                    raise ValueError(f"지오메트리에 'type' 속성이 없습니다: {geometry}")
                
                if geometry.type == 'LineString':
                    coords = geometry.coordinates
                    for u, v in zip(coords[:-1], coords[1:]):
                        self.add_edge(tuple(u), tuple(v), **properties)
                        # 양방향 엣지 추가
                        self.add_edge(tuple(v), tuple(u), **properties)
                elif geometry.type == 'MultiLineString':
                    for line_string in geometry.coordinates:
                        for u, v in zip(line_string[:-1], line_string[1:]):
                            self.add_edge(tuple(u), tuple(v), **properties)
                            # 양방향 엣지 추가
                            self.add_edge(tuple(v), tuple(u), **properties)
                elif geometry.type == 'Point':
                    coords = tuple(geometry.coordinates)
                    self.add_node(coords, **properties)
                elif geometry.type == 'MultiPoint':
                    for point_coords in geometry.coordinates:
                        coords = tuple(point_coords)
                        self.add_node(coords, **properties)
                elif geometry.type == 'Polygon':
                    # 폴리곤 테두리를 LineString처럼 처리
                    # 첫 번째 링(외부 링)만 처리
                    outer_ring = geometry.coordinates[0]
                    # 폴리곤의 각 점을 노드로 추가하고 인접한 점 사이에 엣지 생성
                    for u, v in zip(outer_ring[:-1], outer_ring[1:]):  # 마지막 점은 첫 점과 같으므로 제외
                        self.add_edge(tuple(u), tuple(v), **properties)
                        # 양방향 엣지 추가
                        self.add_edge(tuple(v), tuple(u), **properties)
                    # 폴리곤 닫기 (마지막 점과 첫 점 연결) - 이미 GeoJSON에서 닫혀있을 수 있지만 안전하게 처리
                    if outer_ring[0] != outer_ring[-1]:
                        self.add_edge(tuple(outer_ring[-1]), tuple(outer_ring[0]), **properties)
                        self.add_edge(tuple(outer_ring[0]), tuple(outer_ring[-1]), **properties)
                elif geometry.type == 'MultiPolygon':
                    # 각 폴리곤의 외부 링을 처리
                    for polygon in geometry.coordinates:
                        outer_ring = polygon[0]  # 첫 번째 링(외부 링)
                        for u, v in zip(outer_ring[:-1], outer_ring[1:]):
                            self.add_edge(tuple(u), tuple(v), **properties)
                            self.add_edge(tuple(v), tuple(u), **properties)
                        # 폴리곤 닫기
                        if outer_ring[0] != outer_ring[-1]:
                            self.add_edge(tuple(outer_ring[-1]), tuple(outer_ring[0]), **properties)
                            self.add_edge(tuple(outer_ring[0]), tuple(outer_ring[-1]), **properties)
                else:
                    # 다른 타입의 지오메트리 처리 (필요한 경우)
                    print(f"지원하지 않는 지오메트리 타입: {geometry.type}")

            # FeatureCollection, Feature 또는 직접 Geometry 객체인지 확인
            if hasattr(data, 'type'):
                data_type = data.type
            elif isinstance(data, dict) and 'type' in data:
                data_type = data['type']
            else:
                raise ValueError("입력된 GeoJSON 데이터에 'type' 속성이 없습니다.")
                
            # FeatureCollection 처리
            if data_type == 'FeatureCollection':
                # CRS 정보 추출
                if hasattr(data, 'crs'):
                    crs = data.crs
                elif isinstance(data, dict) and 'crs' in data:
                    crs = data['crs']
                else:
                    crs = None
                    
                if crs:
                    crs_name = None
                    if isinstance(crs, dict) and 'properties' in crs:
                        crs_name = crs['properties'].get('name')
                    elif hasattr(crs, 'properties') and hasattr(crs.properties, 'name'):
                        crs_name = crs.properties.name
                        
                    if crs_name:
                        self.graph['crs'] = crs_name
                
                # Features 처리
                features = data.features if hasattr(data, 'features') else data.get('features', [])
                for feature in features:
                    # 피처에서 geometry와 properties 추출
                    if hasattr(feature, 'geometry') and hasattr(feature, 'properties'):
                        geometry = feature.geometry
                        properties = feature.properties
                    elif isinstance(feature, dict):
                        geometry = feature.get('geometry', {})
                        properties = feature.get('properties', {})
                    else:
                        continue
                        
                    handle_geometry(geometry, properties)
            # Feature 처리
            elif data_type == 'Feature':
                if hasattr(data, 'geometry') and hasattr(data, 'properties'):
                    geometry = data.geometry
                    properties = data.properties
                elif isinstance(data, dict):
                    geometry = data.get('geometry', {})
                    properties = data.get('properties', {})
                else:
                    continue
                    
                handle_geometry(geometry, properties)
            # 직접 지오메트리 객체 처리
            else:
                # 지오메트리 타입인 경우
                geometry_types = ['Point', 'MultiPoint', 'LineString', 'MultiLineString', 'Polygon', 'MultiPolygon']
                if data_type in geometry_types:
                    handle_geometry(data, {})
                else:
                    print(f"지원하지 않는 GeoJSON 타입: {data_type}")

        # KDTree 업데이트
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
                    print(f"노드 {node}를 건너뜁니다 - 좌표 정보가 없습니다.")
        
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
                print(f"엣지 {u}-{v}를 건너뜁니다 - 좌표 정보가 없습니다.")
        
        # 그래프 속성 복사
        for key, value in graph.graph.items():
            mnetwork.graph[key] = value
        
        # KDTree 업데이트
        mnetwork.update_kdtree()
        
        return mnetwork
    


if __name__ == "__main__":
# 사용 예시
    marnet = MNetwork()
    marnet.load_geojson("apps/pathfinding/data/marnet/marnet_plus_100km.geojson")

    # 단일 노드 추가 및 엣지 자동 생성
    new_node = (129.165, 35.070)
    created_edges = marnet.add_node_with_edges(new_node, threshold=100.0)
    print(created_edges)

    # 여러 노드 추가 및 엣지 자동 생성
    new_nodes = [
        (129.170, 35.075),
        (129.180, 35.080),
        (129.175, 35.070)
    ]
    all_created_edges = marnet.add_nodes_with_edges(new_nodes, threshold=100.0)
    print(all_created_edges)
    
    marnet.print_graph_info()
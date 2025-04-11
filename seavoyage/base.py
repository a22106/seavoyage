from searoute import searoute
from seavoyage.classes import MNetwork
from seavoyage.utils import get_m_network_20km
import os
import json
import networkx as nx

from searoute.classes.passages import Passage
from shapely import Polygon, MultiPolygon, LineString

from seavoyage.utils.route_utils import get_restriction_path



# 원본 seavoyage 함수
def _original_seavoyage(start: tuple[float, float], end: tuple[float, float], **kwargs):
    """
    선박 경로 계산 (내부용)

    Args:
        start (tuple[float, float]): 출발 좌표
        end (tuple[float, float]): 종점 좌표

    Returns:
        geojson.FeatureCollection(dict): 경로 정보
    """
    if not kwargs.get("M"):
        kwargs["M"] = get_m_network_20km()
    return searoute(start, end, **kwargs)

# 전역 제한 구역 저장소
_CUSTOM_RESTRICTION_REGISTRY = {}

class CustomRestriction:
    """커스텀 제한 구역을 정의하는 클래스"""
    
    def __init__(self, name: str, polygon):
        """
        CustomRestriction 객체 초기화
        
        Args:
            name (str): 제한 구역 이름
            polygon: Shapely Polygon 또는 MultiPolygon
        """
        self.name = name
        
        if isinstance(polygon, (Polygon, MultiPolygon)):
            self.polygon = polygon
        else:
            raise TypeError("polygon은 Shapely Polygon 또는 MultiPolygon 타입이어야 합니다.")
        
    @classmethod
    def from_geojson(cls, name: str, geojson_data: dict) -> 'CustomRestriction':
        """
        GeoJSON 데이터로부터 CustomRestriction 생성
        
        Args:
            name (str): 제한 구역 이름
            geojson_data (dict): GeoJSON 데이터 (Feature 또는 FeatureCollection)
            
        Returns:
            CustomRestriction: 생성된 CustomRestriction 객체
        """
        if 'type' not in geojson_data:
            raise ValueError("유효하지 않은 GeoJSON 형식입니다.")
            
        if geojson_data['type'] == 'FeatureCollection':
            # 여러 Feature를 하나의 MultiPolygon으로 병합
            polygons = []
            for feature in geojson_data['features']:
                if feature['geometry']['type'] == 'Polygon':
                    coords = feature['geometry']['coordinates']
                    polygons.append(Polygon(coords[0], holes=coords[1:] if len(coords) > 1 else None))
                elif feature['geometry']['type'] == 'MultiPolygon':
                    for poly_coords in feature['geometry']['coordinates']:
                        polygons.append(Polygon(poly_coords[0], holes=poly_coords[1:] if len(poly_coords) > 1 else None))
            
            if not polygons:
                raise ValueError("GeoJSON에 Polygon 또는 MultiPolygon이 없습니다.")
                
            if len(polygons) == 1:
                return cls(name, polygons[0])
            else:
                return cls(name, MultiPolygon(polygons))
                
        elif geojson_data['type'] == 'Feature':
            if geojson_data['geometry']['type'] == 'Polygon':
                coords = geojson_data['geometry']['coordinates']
                return cls(name, Polygon(coords[0], holes=coords[1:] if len(coords) > 1 else None))
            elif geojson_data['geometry']['type'] == 'MultiPolygon':
                polygons = []
                for poly_coords in geojson_data['geometry']['coordinates']:
                    polygons.append(Polygon(poly_coords[0], holes=poly_coords[1:] if len(poly_coords) > 1 else None))
                return cls(name, MultiPolygon(polygons))
            else:
                raise ValueError("Feature는 Polygon 또는 MultiPolygon 타입이어야 합니다.")
        else:
            raise ValueError("지원되지 않는 GeoJSON 타입입니다. FeatureCollection 또는 Feature가 필요합니다.")

    @classmethod
    def from_geojson_file(cls, name: str, file_path: str) -> 'CustomRestriction':
        """
        GeoJSON 파일에서 CustomRestriction 생성
        
        Args:
            name (str): 제한 구역 이름
            file_path (str): GeoJSON 파일 경로
            
        Returns:
            CustomRestriction: 생성된 CustomRestriction 객체
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        return cls.from_geojson(name, geojson_data)


class RestrictedMarnet(MNetwork):
    """커스텀 제한 구역이 적용된 해양 네트워크 클래스"""
    
    def __init__(self, base_network=None):
        """
        RestrictedMarnet 객체 초기화
        
        Args:
            base_network: 기본 네트워크 (None인 경우 빈 네트워크 생성)
        """
        super().__init__()
        
        # 커스텀 제한 구역 저장 딕셔너리
        self.custom_restrictions = {}
        
        # 기본 네트워크 복사
        if base_network is not None:
            # 노드 복사
            for node, data in base_network.nodes(data=True):
                self.add_node(node, **data)
                
            # 엣지 복사
            for u, v, data in base_network.edges(data=True):
                self.add_edge(u, v, **data)
                
            # 그래프 속성 복사
            for key, value in base_network.graph.items():
                self.graph[key] = value
                
            # kdtree 업데이트
            self.update_kdtree()
    
    def add_restriction(self, restriction: CustomRestriction):
        """
        커스텀 제한 구역 추가
        
        Args:
            restriction: CustomRestriction 객체
        """
        self.custom_restrictions[restriction.name] = restriction
        print(f"제한 구역 추가: {restriction.name}")
        
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
        line = LineString([u, v])
        
        # 기존 제한 구역 필터링
        if data.get('passage') in self.restrictions:
            return False
        
        # 커스텀 제한 구역 필터링
        for restriction in self.custom_restrictions.values():
            if restriction.polygon.intersects(line):
                # print(f"제한 구역과 교차: {restriction.name}, 좌표: {u}, {v}")
                return False
        return True
        
    def shortest_path(self, origin, destination):
        """
        제한 구역을 피해 출발지와 목적지 사이의 최단 경로 계산
        
        Args:
            origin: 출발지 좌표 (경도, 위도)
            destination: 목적지 좌표 (경도, 위도)
            
        Returns:
            List: 최단 경로의 노드 리스트
        """
        origin_node = self.kdtree.query(origin)
        destination_node = self.kdtree.query(destination)
        
        # 커스텀 제한 구역을 고려한 가중치 함수
        def custom_weight(u, v, data):
            if self._filter_custom_restricted_edge(u, v, data):
                return data.get('weight', 1.0)
            else:
                return float('inf')
        
        return nx.shortest_path(
            self, origin_node, destination_node, weight=custom_weight)


def register_custom_restriction(name: str, geojson_file_path: str):
    """
    커스텀 제한 구역을 등록합니다.
    
    Args:
        name (str): 제한 구역 이름
        geojson_file_path (str): GeoJSON 파일 경로
    """
    restriction = CustomRestriction.from_geojson_file(name, geojson_file_path)
    _CUSTOM_RESTRICTION_REGISTRY[name] = restriction
    print(f"제한 구역 등록 성공: {name}, 파일: {geojson_file_path}")
    return restriction

# 시작 시 jwc.geojson 파일이 존재하면 자동으로 등록
# register_custom_restriction("jwc", get_restriction_path("jwc.geojson"))

def get_custom_restriction(name: str):
    """
    이름으로 등록된 커스텀 제한 구역을 가져옵니다.
    
    Args:
        name (str): 제한 구역 이름
        
    Returns:
        Optional[CustomRestriction]: 제한 구역 객체 또는 None
    """
    return _CUSTOM_RESTRICTION_REGISTRY.get(name)

def list_custom_restrictions():
    """
    등록된 모든 커스텀 제한 구역 이름을 반환합니다.
    
    Returns:
        List[str]: 등록된 제한 구역 이름 목록
    """
    return list(_CUSTOM_RESTRICTION_REGISTRY.keys())


def seavoyage(start: tuple[float, float], end: tuple[float, float], restrictions=None, **kwargs):
    """
    선박 경로 계산 (커스텀 제한 구역 지원)

    Args:
        start (tuple[float, float]): 출발 좌표
        end (tuple[float, float]): 종점 좌표
        restrictions (list, optional): 제한 구역 목록
        **kwargs: 추가 인자

    Returns:
        geojson.FeatureCollection(dict): 경로 정보
    """
    # 기본 해양 네트워크 가져오기
    base_network = kwargs.pop("M", get_m_network_20km())
    
    # 커스텀 제한 구역이 적용된 네트워크 생성
    restricted_network = RestrictedMarnet(base_network)
    
    # 기본 passage 제한 구역 설정 (searoute.classes.passages.Passage 클래스의 상수들)
    default_passages = []
    custom_restrictions = []
    
    if restrictions:
        print(f"요청된 제한 구역: {restrictions}")
        for r in restrictions:
            # 커스텀 제한 구역인지 확인
            custom_restriction = get_custom_restriction(r)
            if custom_restriction:
                print(f"커스텀 제한 구역 '{r}' 발견")
                custom_restrictions.append(custom_restriction)
            else:
                # 기본 passages 중 하나인지 확인
                if hasattr(Passage, r):
                    print(f"기본 제한 구역 '{r}' 발견")
                    default_passages.append(getattr(Passage, r))
                else:
                    print(f"알 수 없는 제한 구역: '{r}'")
    
    # 기본 제한 구역 설정
    restricted_network.restrictions = default_passages
    
    # 커스텀 제한 구역 추가
    for restriction in custom_restrictions:
        restricted_network.add_restriction(restriction)
    
    # 디버깅용 - 등록된 모든 제한 구역 출력
    print(f"등록된 제한 구역: {list_custom_restrictions()}")
    
    if "jwc" in list_custom_restrictions():
        jwc = get_custom_restriction("jwc")
        if jwc:
            print(f"JWC 제한구역: {jwc.name}, Bounds: {jwc.polygon.bounds}")
    
    # searoute 호출
    kwargs["M"] = restricted_network
    return _original_seavoyage(start, end, **kwargs)

# 이전 버전과의 호환성을 위한 함수
def custom_seavoyage(start: tuple[float, float], end: tuple[float, float], custom_restrictions=None, default_restrictions=None, **kwargs):
    """
    커스텀 제한 구역을 고려한 선박 경로 계산
    
    Args:
        start (tuple[float, float]): 출발 좌표 (경도, 위도)
        end (tuple[float, float]): 목적지 좌표 (경도, 위도)
        custom_restrictions (List[str]): 커스텀 제한 구역 이름 목록
        default_restrictions (List[str]): 기본 제한 구역 목록 (Passage 클래스의 상수들)
        **kwargs: searoute에 전달할 추가 인자
        
    Returns:
        geojson.Feature: 경로 정보
    """
    restrictions = []
    
    # 기본 제한 구역 추가
    if default_restrictions:
        restrictions.extend(default_restrictions)
    
    # 커스텀 제한 구역 추가
    if custom_restrictions:
        restrictions.extend(custom_restrictions)
    
    return seavoyage(start, end, restrictions=restrictions, **kwargs)

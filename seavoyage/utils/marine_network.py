import numpy as np
from shapely import LineString
from sklearn.neighbors import NearestNeighbors
from scipy.spatial import Delaunay
from searoute.utils import distance

from seavoyage.utils.shapely_utils import is_valid_edge
from seavoyage.classes.m_network import MNetwork
from seavoyage.settings import MARNET_DIR

def get_marnet() -> MNetwork:
    """기본 MARNET 네트워크 반환"""
    return MNetwork()

def get_m_network_5km() -> MNetwork:
    """5km 간격의 확장된 MARNET 네트워크 반환"""
    return MNetwork().load_geojson(str(MARNET_DIR / 'marnet_plus_5km.geojson'))

def get_m_network_10km() -> MNetwork:
    """10km 간격의 확장된 MARNET 네트워크 반환"""
    return MNetwork().load_geojson(str(MARNET_DIR / 'marnet_plus_10km.geojson'))

def get_m_network_20km() -> MNetwork:
    """20km 간격의 확장된 MARNET 네트워크 반환"""
    return MNetwork().load_geojson(str(MARNET_DIR / 'marnet_plus_20km.geojson'))

def get_m_network_50km() -> MNetwork:
    """50km 간격의 확장된 MARNET 네트워크 반환"""
    return MNetwork().load_geojson(str(MARNET_DIR / 'marnet_plus_50km.geojson'))

def get_m_network_100km() -> MNetwork:
    """100km 간격의 확장된 MARNET 네트워크 반환"""
    return MNetwork().load_geojson(str(MARNET_DIR / 'marnet_plus_100km.geojson'))

def _get_mnet_path(file_name: str) -> str:
    return str(MARNET_DIR / file_name)

def get_marnet_sample() -> MNetwork:
    return MNetwork().load_geojson('./data/samples/cross_land.geojson')


def add_node_and_connect(mnet: MNetwork, new_node: tuple[float, float], k: int = 5, land_polygon = None):
    """
    기존 MNetwork 객체에 신규 노드를 추가한 뒤,
    해당 노드에 대해서만 기존 노드들과 KNN, Delaunay Triangulation 기반 엣지를 생성합니다.
    (기존 class는 수정하지 않음)

    :param mnet: MNetwork 객체
    :param new_node: (lon, lat) 튜플
    :param k: KNN에서 연결할 이웃 수
    :param land_polygon: 육지 폴리곤 (선택사항)
    :return: 생성된 엣지 리스트 [(node1, node2, 거리), ...]
    """
    # 신규 노드 추가
    mnet.add_node(new_node)
    
    # 노드 좌표 배열 가져오기
    coords = np.array(list(mnet.nodes))
    if len(coords) <= 1:
        print("노드가 1개뿐이므로 엣지 생성 없음")
        return []
        
    created_edges = []
    
    # KNN 기반 엣지 생성
    knn_edges = _create_knn_edges(mnet, coords, new_node, k, land_polygon)
    created_edges.extend(knn_edges)
    
    # Delaunay 기반 엣지 생성 (노드가 3개 이상일 때만)
    if len(coords) >= 3:
        delaunay_edges = _create_delaunay_edges(mnet, coords, new_node, land_polygon)
        created_edges.extend(delaunay_edges)
    
    print(f"신규 노드에 대해 KNN+Delaunay 엣지 생성 완료: {len(created_edges)}개")
    return created_edges


def _create_knn_edges(mnet: MNetwork, coords: np.ndarray, new_node: tuple[float, float], 
                     k: int, land_polygon) -> list:
    """
    KNN 알고리즘을 사용하여 신규 노드에서 가장 가까운 k개 노드와 엣지 생성
    
    :param mnet: MNetwork 객체
    :param coords: 모든 노드 좌표 배열
    :param new_node: 신규 노드 좌표
    :param k: 연결할 이웃 노드 수
    :param land_polygon: 육지 폴리곤 (None 가능)
    :return: 생성된 엣지 목록
    """
    # KNN 모델 학습 - 신규 노드 기준으로만
    n_neighbors = min(k+1, len(coords))  # 자기 자신 포함해서 k+1
    nbrs = NearestNeighbors(n_neighbors=n_neighbors, algorithm='ball_tree').fit(coords)
    distances, indices = nbrs.kneighbors([new_node])
    
    created_edges = []
    # 첫 번째는 자기 자신이므로 제외하고 순회
    for idx, dist in zip(indices[0][1:], distances[0][1:]):
        neighbor = tuple(coords[idx])
        # 유효한 엣지인지 확인하고 추가
        if _is_valid_and_add_edge(mnet, new_node, neighbor, land_polygon):
            edge_distance = float(distance(new_node, neighbor, units="km"))
            created_edges.append((new_node, neighbor, edge_distance))
            
    return created_edges


def _create_delaunay_edges(mnet: MNetwork, coords: np.ndarray, new_node: tuple[float, float], 
                          land_polygon) -> list:
    """
    Delaunay 삼각분할을 사용하여 엣지 생성
    
    :param mnet: MNetwork 객체
    :param coords: 모든 노드 좌표 배열
    :param new_node: 신규 노드 좌표
    :param land_polygon: 육지 폴리곤 (None 가능)
    :return: 생성된 엣지 목록
    """
    # 기존 노드 + 신규 노드로 좌표 배열 생성
    coords_with_new = np.vstack([coords, new_node])
    # Delaunay 삼각분할 수행
    tri = Delaunay(coords_with_new)
    # 신규 노드의 인덱스 (마지막 인덱스)
    new_node_idx = len(coords_with_new) - 1
    
    created_edges = []
    # 신규 노드가 포함된 심플렉스만 처리
    for simplex in tri.simplices:
        if new_node_idx in simplex:
            # 해당 심플렉스에서 가능한 모든 엣지 쌍 처리
            delaunay_edges = _process_simplex_edges(mnet, coords_with_new, simplex, 
                                                  new_node_idx, land_polygon)
            created_edges.extend(delaunay_edges)
            
    return created_edges


def _process_simplex_edges(mnet: MNetwork, coords: np.ndarray, simplex: np.ndarray, 
                          new_node_idx: int, land_polygon) -> list:
    """
    하나의 Delaunay 심플렉스(삼각형)에서 신규 노드가 포함된 엣지 처리
    
    :param mnet: MNetwork 객체
    :param coords: 모든 노드 좌표 배열 (신규 노드 포함)
    :param simplex: 처리할 심플렉스 (삼각형의 3개 노드 인덱스)
    :param new_node_idx: 신규 노드의 인덱스
    :param land_polygon: 육지 폴리곤 (None 가능)
    :return: 생성된 엣지 목록
    """
    created_edges = []
    
    # 심플렉스 내 모든 노드 쌍에 대해
    for i in range(3):
        for j in range(i+1, 3):
            idx_i, idx_j = simplex[i], simplex[j]
            # 신규 노드가 포함된 엣지만 처리
            if new_node_idx in (idx_i, idx_j):
                node_i = tuple(coords[idx_i])
                node_j = tuple(coords[idx_j])
                
                # 이미 엣지가 존재하면 건너뜀
                if mnet.has_edge(node_i, node_j):
                    continue
                    
                # 유효한 엣지인지 확인하고 추가
                if _is_valid_and_add_edge(mnet, node_i, node_j, land_polygon):
                    edge_distance = float(distance(node_i, node_j, units="km"))
                    created_edges.append((node_i, node_j, edge_distance))
                    
    return created_edges


def _is_valid_and_add_edge(mnet: MNetwork, node1: tuple, node2: tuple, land_polygon) -> bool:
    """
    두 노드 간 엣지가 유효한지 확인하고 유효하면 네트워크에 추가
    
    :param mnet: MNetwork 객체
    :param node1: 첫 번째 노드 좌표
    :param node2: 두 번째 노드 좌표
    :param land_polygon: 육지 폴리곤 (None 가능)
    :return: 엣지가 추가되었는지 여부
    """
    # 육지 폴리곤이 있으면 유효성 검사
    line = LineString([node1, node2])
    if land_polygon is not None and not is_valid_edge(line, land_polygon):
        return False
        
    # 엣지 추가 및 가중치 설정
    edge_distance = float(distance(node1, node2, units="km"))
    mnet.add_edge(node1, node2, weight=edge_distance)
    
    return True
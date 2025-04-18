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


def add_edges_for_new_node_knn_delaunay(mnet: MNetwork, new_node: tuple[float, float], k: int = 5, land_polygon = None):
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

    # 1. KNN 엣지 생성
    coords = np.array(list(mnet.nodes))
    if len(coords) <= 1:
        print("노드가 1개뿐이므로 엣지 생성 없음")
        return []

    # KNN: 신규 노드 기준으로만
    nbrs = NearestNeighbors(n_neighbors=min(k+1, len(coords)), algorithm='ball_tree').fit(coords)
    distances, indices = nbrs.kneighbors([new_node])
    created_edges = []
    for idx, dist in zip(indices[0][1:], distances[0][1:]):  # 첫 번째는 자기 자신
        neighbor = tuple(coords[idx])
        line = LineString([new_node, neighbor])
        if land_polygon is not None and not is_valid_edge(line, land_polygon):
            continue
        mnet.add_edge(new_node, neighbor, weight=float(distance(new_node, neighbor, units="km")))
        created_edges.append((new_node, neighbor, float(distance(new_node, neighbor, units="km"))))

    # 2. Delaunay: 기존 노드 + 신규 노드로 삼각분할, 신규 노드가 포함된 edge만 추가
    if len(coords) >= 3:
        coords_with_new = np.vstack([coords, new_node])
        tri = Delaunay(coords_with_new)
        idx_new = len(coords_with_new) - 1
        for simplex in tri.simplices:
            if idx_new in simplex:
                for i in range(3):
                    for j in range(i+1, 3):
                        idx_i, idx_j = simplex[i], simplex[j]
                        if idx_new in (idx_i, idx_j):
                            node_i = tuple(coords_with_new[idx_i])
                            node_j = tuple(coords_with_new[idx_j])
                            if mnet.has_edge(node_i, node_j):
                                continue
                            line = LineString([node_i, node_j])
                            if land_polygon is not None and not is_valid_edge(line, land_polygon):
                                continue
                            mnet.add_edge(node_i, node_j, weight=float(distance(node_i, node_j, units="km")))
                            created_edges.append((node_i, node_j, float(distance(node_i, node_j, units="km"))))
    print(f"신규 노드에 대해 KNN+Delaunay 엣지 생성 완료: {len(created_edges)}개")
    return created_edges
# seavoyage/utils/route_utils.py
import geojson
import searoute as sr
from searoute.utils import distance
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.geojson_utils import load_geojson
from seavoyage.settings import MARNET_DIR, RESTRICTIONS_DIR

def make_searoute_nodes(nodes: list[tuple[float, float]]):
    searoute_nodes = {}
    for node in nodes:
        searoute_nodes[node] = {'x': node[0], 'y': node[1]}
    return searoute_nodes


def get_additional_points() -> geojson.FeatureCollection:
    return load_geojson('./data/additional_points.geojson')

def make_searoute_edges(sr_nodes: dict[tuple[float, float], dict[str, float]], marnet: sr.Marnet, distance_threshold: float = 200):
    """
    :param sr_nodes: searoute format의 추가할 노드들의 좌표와 속성 example: {(129.170, 35.075): {'x': 129.170, 'y': 35.075}}
    :param marnet: searoute.Marnet 객체
    :param distance_threshold: 노드 간 거리 임계값(km). 임계값 이하(범위내)의 노드들은 엣지로 연결됨.
    :return: 새로운 노드와 엣지 딕셔너리
    """
    # validate nodes
    if not isinstance(sr_nodes, dict):
        raise ValueError("nodes must be a dictionary")
    if not isinstance(marnet, sr.Marnet):
        raise ValueError("marnet must be a searoute.Marnet object")
    if not isinstance(distance_threshold, float):
        raise ValueError("distance_threshold must be a float")
    
    # 기존 Marnet 그래프 가져오기
    existing_nodes = marnet.nodes
    existing_edges = marnet.edges
    
    # 새로운 엣지 딕셔너리 초기화
    new_edges = {}
    for new_node in sr_nodes:
        new_edges[new_node] = {}

    # 각 새로운 노드에 대해 가장 가까운 기존 노드들과 연결
    for new_node in sr_nodes:
        # 모든 기존 노드와의 거리 계산
        distances = []
        for existing_node, attrs in existing_nodes.items():
            dist = distance(
                new_node,
                (attrs['x'], attrs['y'])
            )
            distances.append((existing_node, dist))
        
        # 거리순으로 정렬
        distances.sort(key=lambda x: x[1])
        
        # 가장 가까운 10개의 노드와 연결
        for existing_node, dist in distances[:10]:
            if dist <= distance_threshold:
                new_edges[new_node][existing_node] = {"weight": dist}
                # 양방향 엣지 추가
                if existing_node not in existing_edges:
                    existing_edges[existing_node] = {}
                existing_edges[existing_node][new_node] = {"weight": dist}

    # 새로운 노드들 사이의 엣지 추가
    for i in range(len(sr_nodes)):
        for j in range(i+1, len(sr_nodes)):
            dist_between = distance(sr_nodes[i], sr_nodes[j])
            new_edges[sr_nodes[i]][sr_nodes[j]] = {"weight": dist_between}
            new_edges[sr_nodes[j]][sr_nodes[i]] = {"weight": dist_between}

    # 기존 노드와 엣지에 새로운 것들을 추가
    updated_edges = {**existing_edges, **new_edges}
    
    return updated_edges

def create_geojson_from_marnet(marnet: sr.Marnet, save=False) -> geojson.FeatureCollection:
    """
    :param marnet: searoute.Marnet 객체
    :param save: 파일 저장 여부
    :return: geojson.FeatureCollection 객체
    """
    # validate marnet
    if not isinstance(marnet, sr.Marnet):
        raise ValueError("marnet must be a searoute.Marnet object")
    
    features = []
        
    for u, v, attrs in marnet.edges(data=True): # Create a LineString from node u to node v  
        line = geojson.LineString([[u[0], u[1]], [v[0], v[1]]]) 
        feature = geojson.Feature(geometry=line, properties=attrs) 
        features.append(feature)
        
    feature_collection = geojson.FeatureCollection(features)

    if save:
        with open('marnet_network.geojson', 'w') as f: 
            geojson.dump(feature_collection, f)
        
    return feature_collection

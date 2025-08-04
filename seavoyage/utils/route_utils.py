# seavoyage/utils/route_utils.py
import geojson
import searoute as sr
from searoute.utils import distance
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.geojson_utils import load_geojson
from seavoyage.settings import MARNET_DIR, RESTRICTIONS_DIR
from haversine import haversine, Unit
from pathlib import Path
from typing import Dict, Any, Optional, Union

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

def marnet_to_geojson(marnet, save: bool = False, output_path: Optional[Union[str, Path]] = None) -> geojson.FeatureCollection:
    """
    Convert Marnet object to GeoJSON FeatureCollection.
    
    Parameters
    ----------
    marnet : Marnet
        Maritime network object
    save : bool, optional
        Whether to save the result to a file, by default False
    output_path : str or Path, optional
        Path to save the GeoJSON file. If save=True and output_path is None,
        defaults to 'marnet_network.geojson' in current directory.
        
    Returns
    -------
    geojson.FeatureCollection
        GeoJSON representation of the network
        
    Raises
    ------
    OSError
        If file cannot be written
    ValueError
        If output path is invalid
    """
    features = []
    
    # Convert nodes to Point features
    for node in marnet.nodes():
        point = geojson.Point((node[0], node[1]))
        properties = marnet.nodes[node] if node in marnet.nodes else {}
        feature = geojson.Feature(geometry=point, properties=properties)
        features.append(feature)
        
    # Convert edges to LineString features 
    for u, v, attrs in marnet.edges(data=True):
        line = geojson.LineString([[u[0], u[1]], [v[0], v[1]]]) 
        feature = geojson.Feature(geometry=line, properties=attrs) 
        features.append(feature)
        
    feature_collection = geojson.FeatureCollection(features)

    if save:
        # Use pathlib for consistent file handling
        if output_path is None:
            output_path = Path.cwd() / 'marnet_network.geojson'
        else:
            output_path = Path(output_path)
            
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f: 
                geojson.dump(feature_collection, f, indent=2)
            print(f"Network saved to: {output_path}")
        except (OSError, PermissionError) as e:
            raise OSError(f"Failed to save network to {output_path}: {e}") from e
        
    return feature_collection

def calculate_route_length(route, unit):
    """
    경로의 총 거리를 계산하는 함수
    
    Args:
        route (dict): 경로 GeoJSON 객체
        unit: 거리 단위 (haversine 패키지의 Unit 열거형)
        
    Returns:
        float: 계산된 총 거리
    """
    # 좌표 목록 가져오기
    coordinates = route['geometry']['coordinates']
    total_distance = 0
    
    # 각 좌표 구간의 거리 계산 및 합산
    for i in range(1, len(coordinates)):
        point1 = coordinates[i-1]
        point1 = (point1[1], point1[0])  # 위도, 경도 순서로 변환
        point2 = coordinates[i]
        point2 = (point2[1], point2[0])  # 위도, 경도 순서로 변환
        
        distance = haversine(point1, point2, unit=unit, normalize=True)
        total_distance += distance
    
    return total_distance

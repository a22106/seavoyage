def build_knn_edges(df, k=5, land_polygon=None):
    """
    1) K-NN 에지 생성:
        각 노드(좌표)에 대하여, 거리상 가장 가까운 k개의 이웃 노드와의 에지를 반환한다.
        에지는 ((lon1, lat1), (lon2, lat2), 거리) 형태로 저장.
        
    :param df: 위도/경도 데이터가 포함된 DataFrame (lon, lat 열 필요)
    :param k: 각 노드에 대해 연결할 최근접 이웃의 수
    :param land_polygon: 육지 폴리곤 (선택사항)
    :return: MNetwork 객체
    """
    from seavoyage.classes.m_network import MNetwork
    from seavoyage.utils.shapely_utils import is_valid_edge
    from shapely import LineString
    from sklearn.neighbors import NearestNeighbors
    from searoute.utils import distance
    
    # MNetwork 객체 생성
    mnet = MNetwork()
    
    coords = df[['lon','lat']].values
    n = len(coords)
    
    # 모든 좌표를 MNetwork에 노드로 추가
    for i in range(n):
        node = (coords[i][0], coords[i][1])  # (lon, lat) 형태로 변환
        mnet.add_node(node)
    
    # KNN 계산
    nbrs = NearestNeighbors(n_neighbors=k+1, algorithm='ball_tree').fit(coords)
    distances, indices = nbrs.kneighbors(coords)
    
    # 에지 생성 및 MNetwork에 추가
    for i in range(n):
        node_i = (coords[i][0], coords[i][1])
        # i 자체가 최근접 이웃 목록에 포함되므로 (k+1)개 중 첫 번째는 자기 자신
        # → 1부터 k까지가 실제 이웃
        for idx, _ in zip(indices[i][1:], distances[i][1:]):
            node_j = (coords[idx][0], coords[idx][1])
            
            # 육지 통과 여부 검사
            if land_polygon is not None:
                line = LineString([node_i, node_j])
                if not is_valid_edge(line, land_polygon):
                    continue
            
            # 거리를 km 단위로 계산
            # searoute의 distance 함수는 km 단위 반환
            dist_km = distance(node_i, node_j, units="km")
            
            # km 단위로 에지 추가
            mnet.add_edge(node_i, node_j, weight=float(dist_km))
    
    print(f"KNN 그래프 생성 완료: {len(mnet.nodes)} 노드, {len(mnet.edges)} 에지")
    return mnet

def build_delaunay_edges(df, land_polygon=None):
    """
    2) 델로네 삼각분할(Delaunay Triangulation) 기반 에지 생성:
       좌표 집합에 대해 삼각분할을 수행한 후, 각 삼각형 변에 해당하는 노드 쌍을 에지로 취급한다.
       
    :param df: 위도/경도 데이터가 포함된 DataFrame (lon, lat 열 필요)
    :param land_polygon: 육지 폴리곤 (선택사항)
    :return: MNetwork 객체
    """
    from seavoyage.classes.m_network import MNetwork
    from seavoyage.utils.shapely_utils import is_valid_edge
    from shapely import LineString
    from scipy.spatial import Delaunay
    import numpy as np
    from searoute.utils import distance
    
    # MNetwork 객체 생성
    mnet = MNetwork()
    
    coords = df[['lon','lat']].values
    
    # 모든 좌표를 MNetwork에 노드로 추가
    for i in range(len(coords)):
        node = (coords[i][0], coords[i][1])  # (lon, lat) 형태로 변환
        mnet.add_node(node)
    
    # 델로네 삼각분할 수행
    tri = Delaunay(coords)
    
    # 에지 생성 및 MNetwork에 추가
    for simplex in tri.simplices:
        # 한 simplex(삼각형)는 보통 3개의 꼭지점 인덱스를 가짐
        vertex_indices = list(simplex)
        m = len(vertex_indices)
        for i in range(m):
            for j in range(i+1, m):
                idx_i = vertex_indices[i]
                idx_j = vertex_indices[j]
                
                node_i = (coords[idx_i][0], coords[idx_i][1])
                node_j = (coords[idx_j][0], coords[idx_j][1])
                
                # 거리를 km 단위로 계산
                dist_km = distance(node_i, node_j, units="km")
                
                # 육지 통과 여부 검사
                if land_polygon is not None:
                    line = LineString([node_i, node_j])
                    if not is_valid_edge(line, land_polygon):
                        continue
                
                # MNetwork에 에지 추가
                mnet.add_edge(node_i, node_j, weight=float(dist_km))
    
    print(f"델로네 삼각분할 그래프 생성 완료: {len(mnet.nodes)} 노드, {len(mnet.edges)} 에지")
    return mnet

def build_network_graph(df, k=5, use_delaunay=True, land_polygon=None):
    """
    종합 알고리즘:
    1) K-NN 기반 에지 생성
    2) 선택적으로 델로네 삼각분할 기반 에지 추가
    3) 최종 MNetwork 반환
    
    :param df: 위도/경도 데이터가 포함된 DataFrame (lon, lat 열 필요)
    :param k: KNN에서 사용할 이웃 수
    :param use_delaunay: 델로네 삼각분할을 사용할지 여부
    :param land_polygon: 육지 폴리곤 (선택사항)
    :return: MNetwork 객체
    """
    from seavoyage.classes.m_network import MNetwork
    
    # 모든 좌표를 준비
    coords = df[['lon','lat']].values
    
    # 최종 MNetwork 객체
    mnet = MNetwork()
    
    # 우선 모든 노드 추가
    for i in range(len(coords)):
        node = (coords[i][0], coords[i][1])
        mnet.add_node(node)
    
    # 1) KNN 에지 계산
    knn_mnet = build_knn_edges(df, k=k, land_polygon=land_polygon)
    
    # KNN 에지 추가
    for u, v, attr in knn_mnet.edges(data=True):
        if not mnet.has_edge(u, v):
            mnet.add_edge(u, v, **attr)
    
    # 2) 옵션에 따라 델로네 에지 추가
    if use_delaunay:
        delaunay_mnet = build_delaunay_edges(df, land_polygon=land_polygon)
        
        # 델로네 에지 추가 (중복 방지)
        for u, v, attr in delaunay_mnet.edges(data=True):
            if not mnet.has_edge(u, v):
                mnet.add_edge(u, v, **attr)
    
    # KDTree 업데이트
    mnet.update_kdtree()
    
    print(f"최종 네트워크 그래프 생성 완료: {len(mnet.nodes)} 노드, {len(mnet.edges)} 에지")
    return mnet

if __name__ == "__main__":
    import pandas as pd
    from seavoyage.utils.shoreline import load_land_polygon, ShorelineType
    
    # 육지 폴리곤 로드
    land_polygon = load_land_polygon(ShorelineType.LOW)
    
    # 예시 데이터 생성
    data = {
        'lon': [126.0, 126.1, 126.2, 126.3, 126.4],
        'lat': [37.0, 37.1, 37.2, 37.3, 37.4]
    }
    
    df = pd.DataFrame(data)
    
    # 네트워크 그래프 생성
    mnet = build_network_graph(df, k=3, use_delaunay=True, land_polygon=land_polygon)
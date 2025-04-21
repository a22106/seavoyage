import seavoyage as sv
import pytest
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.marine_network import _get_mnet_path
import os
import numpy as np
from shapely.geometry import Polygon, LineString

class TestMnetwork:
    def test_init_mnetwork(self):
        # MNetwork 객체 초기화 테스트
        marine_network = sv.MNetwork()
        assert marine_network is not None
        assert isinstance(marine_network, sv.MNetwork)

    def test_multi_res_mnet(self):
        mnet5 = sv.get_m_network_5km()
        mnet10 = sv.get_m_network_10km()
        mnet20 = sv.get_m_network_20km()
        mnet50 = sv.get_m_network_50km()
        mnet100 = sv.get_m_network_100km()
        
        assert isinstance(mnet5, sv.MNetwork)
        assert isinstance(mnet10, sv.MNetwork)
        assert isinstance(mnet20, sv.MNetwork)
        assert isinstance(mnet50, sv.MNetwork)
        assert isinstance(mnet100, sv.MNetwork)
        assert mnet5 != mnet10
        assert mnet10 != mnet20
        assert mnet20 != mnet50
        assert mnet50 != mnet100

@pytest.fixture
def geojson_5km_path():
    # 실제 경로에 맞게 수정 필요
    return _get_mnet_path('marnet_plus_5km.geojson')

@pytest.fixture
def geojson_10km_path():
    return _get_mnet_path('marnet_plus_10km.geojson')

@pytest.fixture
def geojson_20km_path():
    return _get_mnet_path('marnet_plus_20km.geojson')

@pytest.fixture
def geojson_50km_path():
    return _get_mnet_path('marnet_plus_50km.geojson')

@pytest.fixture
def geojson_100km_path():
    return _get_mnet_path('marnet_plus_100km.geojson')

def test_load_geojson_5km(geojson_5km_path):
    mnet = MNetwork().load_from_geojson(geojson_5km_path)
    assert isinstance(mnet, MNetwork)
    assert len(mnet.nodes) > 0
    assert len(mnet.edges) > 0

def test_load_geojson_10km(geojson_10km_path):
    mnet = MNetwork().load_from_geojson(geojson_10km_path)
    assert isinstance(mnet, MNetwork)
    assert len(mnet.nodes) > 0

def test_load_geojson_20km(geojson_20km_path):
    mnet = MNetwork().load_from_geojson(geojson_20km_path)
    assert isinstance(mnet, MNetwork)
    assert len(mnet.nodes) > 0

def test_load_geojson_50km(geojson_50km_path):
    mnet = MNetwork().load_from_geojson(geojson_50km_path)
    assert isinstance(mnet, MNetwork)
    assert len(mnet.nodes) > 0

def test_load_geojson_100km(geojson_100km_path):
    mnet = MNetwork().load_from_geojson(geojson_100km_path)
    assert isinstance(mnet, MNetwork)
    assert len(mnet.nodes) > 0

def test_add_node_with_edges():
    mnet = MNetwork()
    node = (129.165, 35.070)
    edges = mnet.add_node_with_edges(node, threshold=100.0)
    assert isinstance(edges, list)

def test_add_nodes_with_edges():
    mnet = MNetwork()
    nodes = [
        (129.170, 35.075),
        (129.180, 35.080),
        (129.175, 35.070)
    ]
    edges = mnet.add_nodes_with_edges(nodes, threshold=100.0)
    assert isinstance(edges, list)

def test_add_invalid_node_type():
    mnet = MNetwork()
    with pytest.raises(TypeError):
        mnet.add_node_with_edges([129.165, 35.070], threshold=100.0)  # 리스트는 허용되지 않음

def test_add_invalid_threshold():
    mnet = MNetwork()
    with pytest.raises(ValueError):
        mnet.add_node_with_edges((129.165, 35.070), threshold=-1)

def test_load_geojson_file_not_found():
    mnet = MNetwork()
    with pytest.raises(FileNotFoundError):
        mnet.load_from_geojson('not_exist_file.geojson')

def test_load_geojson_invalid_type():
    mnet = MNetwork()
    with pytest.raises(TypeError):
        mnet.load_from_geojson(12345)  # 지원하지 않는 타입

def test_to_geojson(tmp_path):
    mnet = MNetwork()
    node = (129.165, 35.070)
    mnet.add_node_with_edges(node, threshold=100.0)
    out_path = tmp_path / "test.geojson"
    geojson_obj = mnet.to_geojson(str(out_path))
    assert os.path.exists(out_path)
    assert geojson_obj is not None

def test_to_line_string():
    mnet = MNetwork()
    node = (129.165, 35.070)
    mnet.add_node_with_edges(node, threshold=100.0)
    lines = mnet.to_line_string()
    assert isinstance(lines, list)

# add_node_and_connect 메소드 테스트 추가
def test_add_node_and_connect_empty_network():
    """빈 네트워크에 노드 추가 테스트"""
    mnet = MNetwork()
    new_node = (126.5, 35.5)
    edges = mnet.add_node_and_connect(new_node)
    
    # 노드가 하나뿐이므로 엣지가 생성되지 않아야 함
    assert isinstance(edges, list)
    assert len(edges) == 0
    assert new_node in mnet.nodes
    assert len(mnet.nodes) == 1

def test_add_node_and_connect_with_existing_nodes():
    """기존 노드가 있는 네트워크에 노드 추가 테스트"""
    mnet = MNetwork()
    
    # 기존 노드 몇 개 추가
    existing_nodes = [
        (126.0, 35.0),
        (126.1, 35.1),
        (126.2, 35.2),
        (126.3, 35.3),
        (126.4, 35.4)
    ]
    for node in existing_nodes:
        mnet.add_node(node)
    
    # 새 노드 추가 및 연결
    new_node = (126.5, 35.5)
    edges = mnet.add_node_and_connect(new_node, k=3, land_polygon=None)
    
    # 검증
    assert isinstance(edges, list)
    assert len(edges) > 0
    assert new_node in mnet.nodes
    assert len(mnet.nodes) == 6  # 기존 5개 + 새 노드 1개
    
    # 모든 엣지가 새 노드를 포함하는지 확인
    for edge in edges:
        assert new_node in (edge[0], edge[1])
        
    # k=3으로 설정했으므로 KNN에서 적어도 3개의 엣지가 생성되어야 함
    # (Delaunay에서 추가 엣지가 생성될 수 있음)
    assert len(edges) >= 3

def test_add_node_and_connect_params():
    """다양한 k 값으로 add_node_and_connect 테스트"""
    # 여러 k 값에 대해 테스트
    for k in [1, 3, 5, 10]:
        mnet = MNetwork()
        
        # 기존 노드 12개 추가 (k값보다 많게)
        existing_nodes = [(126.0 + i*0.1, 35.0 + i*0.1) for i in range(12)]
        for node in existing_nodes:
            mnet.add_node(node)
        
        # 새 노드 추가
        new_node = (127.0, 36.0)
        edges = mnet.add_node_and_connect(new_node, k=k, land_polygon=None)
        
        # KNN에서 생성되는 엣지 수는 k 이하여야 함 (노드 수가 충분한 경우 정확히 k개)
        # Delaunay에서 추가 엣지가 생성될 수 있음
        assert len(edges) >= min(k, len(existing_nodes))

def test_add_node_and_connect_returns_edge_format():
    """엣지 포맷 검증 테스트"""
    mnet = MNetwork()
    
    # 기존 노드 추가
    existing_nodes = [
        (126.0, 35.0),
        (126.1, 35.1),
        (126.2, 35.2)
    ]
    for node in existing_nodes:
        mnet.add_node(node)
    
    # 새 노드 추가
    new_node = (126.5, 35.5)
    edges = mnet.add_node_and_connect(new_node)
    
    # 엣지 형식 검증: (node1, node2, weight)
    for edge in edges:
        assert len(edge) == 3
        assert isinstance(edge[0], tuple) and len(edge[0]) == 2
        assert isinstance(edge[1], tuple) and len(edge[1]) == 2
        assert isinstance(edge[2], float)
        
        # weight는 거리(km)이므로 양수여야 함
        assert edge[2] > 0

def test_add_node_and_connect_kdtree_update():
    """KDTree 업데이트 테스트"""
    mnet = MNetwork()
    
    # 기존 노드 추가
    existing_nodes = [
        (126.0, 35.0),
        (126.1, 35.1),
        (126.2, 35.2)
    ]
    for node in existing_nodes:
        mnet.add_node(node)
    
    # KDTree 업데이트
    mnet.update_kdtree()
    
    # 새 노드 추가 전에 가장 가까운 노드 찾기
    new_node = (126.5, 35.5)
    closest_before = mnet.kdtree.query(new_node)
    
    # 새 노드 추가
    mnet.add_node_and_connect(new_node)
    
    # 새 노드가 추가된 후 가장 가까운 노드 찾기
    closest_after = mnet.kdtree.query(new_node)
    
    # KDTree가 업데이트되었으므로 새 노드 자신이 가장 가까운 노드여야 함
    assert closest_after == new_node
    assert closest_before != closest_after

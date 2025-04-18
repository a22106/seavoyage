import seavoyage as sv
import pytest
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.marine_network import _get_mnet_path
import os

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

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
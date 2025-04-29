try:
    # 패키지 내부에서 임포트할 때 사용되는 상대 경로
    from .coordinates import *
    from .geojson_utils import *
    from .map_utils import *
    from .marine_network import (
        get_marnet,  # 기본 MARNET 네트워크 반환
        get_m_network_5km,  # 5km 간격 네트워크 반환
        get_m_network_10km,  # 10km 간격 네트워크 반환
        get_m_network_20km,  # 20km 간격 네트워크 반환
        get_m_network_50km,  # 50km 간격 네트워크 반환
        get_m_network_100km,  # 100km 간격 네트워크 반환
        _get_mnet_path,  # 내부적으로 사용되는 네트워크 경로 반환 함수
        get_marnet_sample,  # 샘플 네트워크 반환
        add_node_and_connect
    )
    from .route_utils import *
    from .shapely_utils import *
    from .shoreline import *
except ImportError:
    # 외부에서 패키지를 임포트할 때 사용되는 절대 경로
    from seavoyage.utils.coordinates import *
    from seavoyage.utils.geojson_utils import *
    from seavoyage.utils.map_utils import *
    from seavoyage.utils.marine_network import (
        get_marnet,
        get_m_network_5km,
        get_m_network_10km,
        get_m_network_20km,
        get_m_network_50km,
        get_m_network_100km,
        _get_mnet_path,
        get_marnet_sample,
        add_node_and_connect
    )
    from seavoyage.utils.route_utils import *
    from seavoyage.utils.shapely_utils import *
    from seavoyage.utils.shoreline import *


__all__ = (
    # coordinates
    ["decdeg_to_degmin"]
    # geojson_utils
    + ["load_geojson"]
    # map_utils
    + ["map_folium", "map_folium_graph"]
    # marine_network
    + [
        "get_marnet",
        "get_m_network_5km",
        "get_m_network_10km",
        "get_m_network_20km",
        "get_m_network_50km",
        "get_m_network_100km",
        "_get_mnet_path",
        "get_marnet_sample",
        "add_node_and_connect"
    ]
    # route_utils
    + [
        "make_searoute_nodes",
        "get_additional_points",
        "make_searoute_edges",
        "create_geojson_from_marnet",
    ]
    # shapely_utils
    + [
        "extract_linestrings_from_geojson",
        "extract_linestrings_from_geojson_file",
        "is_valid_edge",
        "remove_edges_cross_land",
    ]
    # shoreline
    + [
        "ShorelineLevel",
        "shoreline",
    ]
)

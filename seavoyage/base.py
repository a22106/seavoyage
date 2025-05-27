from haversine import Unit
from searoute import searoute, setup_M
from searoute.classes.passages import Passage
from searoute.classes.marnet import Marnet
from searoute.classes.ports import Ports
from seavoyage.log import logger
from seavoyage.exceptions import RouteError, StartInRestrictionError, DestinationInRestrictionError, IsolatedOriginError

from seavoyage.modules.restriction import CustomRestriction, get_custom_restriction, list_custom_restrictions
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.coordinates import decdeg_to_degmin
from seavoyage.utils.route_utils import calculate_route_length

_DEFAULT_MNETWORK = MNetwork.from_marnet(setup_M())

units_map = {
    "km": Unit.KILOMETERS,
    "m": Unit.METERS,
    "mi": Unit.MILES,
    "nm": Unit.NAUTICAL_MILES,
    "ft": Unit.FEET,
    "in": Unit.INCHES,
    "rad": Unit.RADIANS,
    "deg": Unit.DEGREES,
}

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
        kwargs["M"] = setup_M()
    route = searoute(start, end, **kwargs)
    
    # 단위 별 length property 계산 
    units = kwargs.get("units", "nm")
    unit = units_map[units]
    
    # 총 거리 계산
    total_distance = calculate_route_length(route, unit)
    
    route['properties']['length'] = total_distance
    return route

def _classify_restrictions(restrictions):
    """
    제한 구역 이름 리스트를 커스텀/기본/알 수 없음으로 분류
    """
    custom = []
    default = []
    unknown = []
    for r in restrictions:
        custom_restriction = get_custom_restriction(r)
        if custom_restriction:
            logger.debug(f"커스텀 제한 구역 '{r}' 발견")
            custom.append(custom_restriction)
        elif hasattr(Passage, r):
            logger.debug(f"기본 제한 구역 '{r}' 발견")
            default.append(getattr(Passage, r))
        else:
            logger.warning(f"알 수 없는 제한 구역: '{r}'")
            unknown.append(r)
    return custom, default, unknown


def _apply_restrictions_to_network(mnetwork: MNetwork, custom_restrictions:list[CustomRestriction], default_passages:list[Passage]):
    """
    네트워크 객체에 제한 구역을 적용
    """
    if not isinstance(mnetwork, MNetwork | Marnet):
        raise ValueError(f"mnetwork must be an instance of MNetwork, not {type(mnetwork)}: {mnetwork}")
    
    # 기존 제한 구역을 덮어쓰지 않고 새로운 제한 구역만 추가
    for passage in default_passages:
        if passage not in mnetwork.restrictions:
            mnetwork.restrictions.append(passage)
    
    # 커스텀 제한 구역 추가
    for restriction in custom_restrictions:
        mnetwork.add_restriction(restriction)


def seavoyage(start: tuple[float, float], end: tuple[float, float], *,
              restrictions: list[str] | None = None,
              M: MNetwork | Marnet | None = None,
              units: str = "nm",
              speed_knot: float = 10,
              append_orig_dest: bool = False,
              include_ports: bool = False,
              port_params: dict| None = None,
              P: Ports | None = None,
              return_passages: bool = False,
              ) -> dict:
    """
    선박 경로 계산 (커스텀 제한 구역 지원)

    Args:
        start (tuple[float, float]): 출발 좌표
        end (tuple[float, float]): 종점 좌표
        restrictions (list[str], optional): 제한 구역 목록
        M (MNetwork | Marnet, optional): 해상 네트워크 객체
        units (str): 거리 단위 (기본값: "nm")
        speed_knot (float): 선박 속도 (기본값: 10 노트)
        append_orig_dest (bool): 출발지/목적지를 경로에 추가 여부 (기본값: False)
        include_ports (bool): 항구 포함 여부 (기본값: False)
        port_params (dict, optional): 항구 관련 설정
        P (Ports, optional): 항구 네트워크 객체
        return_passages (bool): 통과한 항로 반환 여부 (기본값: False)

    Returns:
        dict: 경로 정보 (GeoJSON Feature)
        
    Raises:
        RouteError: 경로 계산 중 오류가 발생한 경우
        StartInRestrictionError: 출발점이 제한 구역 내에 있는 경우
        DestinationInRestrictionError: 도착점이 제한 구역 내에 있는 경우
        UnreachableDestinationError: 제한 구역으로 인해 목적지에 도달할 수 없는 경우
        IsolatedOriginError: 출발점이 제한 구역에 의해 고립되어 있는 경우
    """
    mnetwork: MNetwork = M or _DEFAULT_MNETWORK
    mnetwork.reset_restrictions()  # 제한 구역 초기화
    custom_restrictions, default_passages, unknown_restrictions = [], [], []
    
    if restrictions is None:
        processed_restrictions = [Passage.northwest]
    else:
        if not isinstance(restrictions, list):
            raise ValueError("restrictions must be a list")
        logger.debug(f"요청된 제한 구역: {restrictions}")
        processed_restrictions = restrictions + [Passage.northwest]
    
    # 제한 구역 분류 (항상 수행)
    custom_restrictions, default_passages, unknown_restrictions = _classify_restrictions(processed_restrictions)
    

    if start == end:
        # 동일한 포인트 입력 시, 길이 0의 경로 반환
        return {
            "geometry": {
                "coordinates": [list(start)],
                "type": "LineString"
            },
            "properties": {
                "duration_hours": 0.0,
                "length": 0.0,
                "units": units
            },
            "type": "Feature"
        }


    # 네트워크에 제한 구역을 적용
    _apply_restrictions_to_network(mnetwork, custom_restrictions, default_passages)

    logger.debug(f"등록된 제한 구역: {list_custom_restrictions()}")
    logger.debug(f"적용된 기본 제한 구역: {mnetwork.restrictions}")
    logger.debug(f"적용된 커스텀 제한 구역: {list(mnetwork.custom_restrictions.keys())}")

    # kwargs 딕셔너리 구성
    kwargs = {
        "M": mnetwork,
        "units": units,
        "speed_knot": speed_knot,
        "append_orig_dest": append_orig_dest,
        "restrictions": processed_restrictions,
        "include_ports": include_ports,
        "return_passages": return_passages
    }
    
    # 선택적 파라미터들 추가
    if port_params is not None:
        kwargs["port_params"] = port_params
    if P is not None:
        kwargs["P"] = P
    
    try:
        # 고립 점 확인 로직: 먼저 출발점이 고립되었는지 확인
        logger.debug(f"출발점 {start}와 목적지 {end} 사이의 경로 계산 시작")
        
        # 출발점이 제한 구역 내에 있는지 확인
        is_origin_restricted, origin_restriction = mnetwork.is_point_in_restriction(start)
        if is_origin_restricted:
            logger.error(f"출발점 {decdeg_to_degmin(start)}이 제한 구역 '{origin_restriction}' 내에 있습니다")
            raise StartInRestrictionError(start, origin_restriction)
            
        # 도착점이 제한 구역 내에 있는지 확인
        is_dest_restricted, dest_restriction = mnetwork.is_point_in_restriction(end)
        if is_dest_restricted:
            logger.error(f"도착점 {decdeg_to_degmin(end)}이 제한 구역 '{dest_restriction}' 내에 있습니다")
            raise DestinationInRestrictionError(end, dest_restriction)
        
        # 출발점과 가장 가까운 네트워크 노드 찾기
        origin_node = mnetwork.kdtree.query(start)
        
        # 출발점과 KDTree로 찾은 노드 사이의 선분이 제한 구역을 통과하는지 확인
        if start != origin_node:  # 출발점과 네트워크 노드가 다른 경우
            from shapely import LineString
            
            line_to_origin = LineString([start, origin_node])
            logger.debug(f"출발점 {start}에서 가장 가까운 네트워크 노드: {origin_node}")
            
            # 커스텀 제한 구역 확인
            for name, restriction in mnetwork.custom_restrictions.items():
                if restriction.polygon.intersects(line_to_origin):
                    logger.error(f"출발점 {start}에서 가장 가까운 노드 {origin_node}까지의 경로가 제한 구역 '{name}'와 교차합니다")
                    raise IsolatedOriginError(start, [name])
        
        # 출발지 노드가 고립되었는지 확인
        is_isolated = True
        
        for neighbor in mnetwork.neighbors(origin_node):
            edge_data = mnetwork.get_edge_data(origin_node, neighbor)
            if mnetwork._filter_custom_restricted_edge(origin_node, neighbor, edge_data):
                is_isolated = False
                break
        
        if is_isolated:
            restriction_names = list(mnetwork.custom_restrictions.keys())
            if mnetwork.restrictions:
                restriction_names.extend([str(r) for r in mnetwork.restrictions])
            logger.error(f"출발점 {start}이 제한 구역에 의해 고립되어 있습니다: {restriction_names}")
            raise IsolatedOriginError(start, restriction_names)
            
        return _original_seavoyage(start, end, **kwargs)
        
    except (RouteError, IsolatedOriginError) as e:
        # 경로 관련 예외 처리
        logger.error(f"경로 오류: {str(e)}")
        raise
    except Exception as e:
        # 기타 예외는 원래 예외를 그대로 전달
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        raise

# 이전 버전과의 호환성을 위한 함수
def custom_seavoyage(start: tuple[float, float], end: tuple[float, float], custom_restrictions=None, default_restrictions=None, **kwargs):
    """
    커스텀 제한 구역을 고려한 선박 경로 계산
    
    Args:
        start: 출발 좌표 (경도, 위도)
        end: 목적지 좌표 (경도, 위도)
        custom_restrictions: 커스텀 제한 구역 이름 목록
        default_restrictions: 기본 제한 구역 목록 (Passage 클래스의 상수들)
        **kwargs: seavoyage에 전달할 추가 인자
    Returns:
        dict: 경로 정보 (GeoJSON Feature)
        
    Raises:
        RouteError: 경로 계산 중 오류가 발생한 경우
        IsolatedOriginError: 출발점이 제한 구역에 의해 고립되어 있는 경우
    """
    restrictions = []
    
    # 기본 제한 구역 추가
    if default_restrictions:
        restrictions.extend(default_restrictions)
    
    # 커스텀 제한 구역 추가
    if custom_restrictions:
        restrictions.extend(custom_restrictions)
    
    # kwargs에서 seavoyage의 새로운 parameter들 추출
    seavoyage_params = {
        'M': kwargs.pop('M', None),
        'units': kwargs.pop('units', 'nm'),
        'speed_knot': kwargs.pop('speed_knot', 10),
        'append_orig_dest': kwargs.pop('append_orig_dest', False),
        'include_ports': kwargs.pop('include_ports', False),
        'port_params': kwargs.pop('port_params', None),
        'P': kwargs.pop('P', None),
        'return_passages': kwargs.pop('return_passages', False)
    }
    
    # restrictions 추가 (빈 리스트가 아닌 경우에만)
    if restrictions:
        seavoyage_params['restrictions'] = restrictions
    
    # None 값인 선택적 parameter들 제거
    seavoyage_params = {k: v for k, v in seavoyage_params.items() if v is not None}
    
    return seavoyage(start, end, **seavoyage_params)

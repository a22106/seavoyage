import networkx as nx
import os
from searoute import searoute, setup_M
from searoute.classes.passages import Passage
from searoute.classes.marnet import Marnet
from seavoyage.log import logger
from seavoyage.exceptions import RouteError, UnreachableDestinationError, StartInRestrictionError, DestinationInRestrictionError, IsolatedOriginError

from seavoyage.utils import get_m_network_20km, _get_mnet_path
from seavoyage.modules.restriction import CustomRestriction, get_custom_restriction, list_custom_restrictions
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.coordinates import decdeg_to_degmin

_DEFAULT_MNETWORK = MNetwork.from_marnet(setup_M())

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
    return searoute(start, end, **kwargs)

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
    mnetwork.restrictions = default_passages
    for restriction in custom_restrictions:
        mnetwork.add_restriction(restriction)


def seavoyage(start: tuple[float, float], end: tuple[float, float], restrictions=None, **kwargs):
    """
    선박 경로 계산 (커스텀 제한 구역 지원)

    Args:
        start (tuple[float, float]): 출발 좌표
        end (tuple[float, float]): 종점 좌표
        restrictions (list, optional): 제한 구역 목록
        **kwargs: 추가 인자

    Returns:
        geojson.FeatureCollection(dict): 경로 정보
        
    Raises:
        RouteError: 경로 계산 중 오류가 발생한 경우
        StartInRestrictionError: 출발점이 제한 구역 내에 있는 경우
        DestinationInRestrictionError: 도착점이 제한 구역 내에 있는 경우
        UnreachableDestinationError: 제한 구역으로 인해 목적지에 도달할 수 없는 경우
        IsolatedOriginError: 출발점이 제한 구역에 의해 고립되어 있는 경우
    """
    mnetwork: MNetwork = kwargs.pop("M", _DEFAULT_MNETWORK)

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
                "units": "km"
            },
            "type": "Feature"
        }

    custom_restrictions, default_passages, unknown_restrictions = [], [], []
    if restrictions:
        logger.debug(f"요청된 제한 구역: {restrictions}")
        custom_restrictions, default_passages, unknown_restrictions = _classify_restrictions(restrictions)

    # 네트워크에 제한 구역을 적용
    _apply_restrictions_to_network(mnetwork, custom_restrictions, default_passages)

    logger.debug(f"등록된 제한 구역: {list_custom_restrictions()}")
    logger.debug(f"적용된 기본 제한 구역: {mnetwork.restrictions}")
    logger.debug(f"적용된 커스텀 제한 구역: {list(mnetwork.custom_restrictions.keys())}")

    kwargs["M"] = mnetwork
    
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
        start (tuple[float, float]): 출발 좌표 (경도, 위도)
        end (tuple[float, float]): 목적지 좌표 (경도, 위도)
        custom_restrictions (List[str]): 커스텀 제한 구역 이름 목록
        default_restrictions (List[str]): 기본 제한 구역 목록 (Passage 클래스의 상수들)
        **kwargs: searoute에 전달할 추가 인자
        
    Returns:
        geojson.Feature: 경로 정보
        
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
    
    return seavoyage(start, end, restrictions=restrictions, **kwargs)

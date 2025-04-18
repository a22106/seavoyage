import networkx as nx
import os
from searoute import searoute
from searoute.classes.passages import Passage
from seavoyage.log import logger

from seavoyage.utils import get_m_network_20km, _get_mnet_path
from seavoyage.modules.restriction import CustomRestriction, get_custom_restriction, list_custom_restrictions
from seavoyage.classes.m_network import MNetwork

_DEFAULT_MNETWORK = MNetwork().load_geojson(_get_mnet_path('10km_modified.geojson')) if os.path.exists(_get_mnet_path('10km_modified.geojson')) else get_m_network_20km()

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
        kwargs["M"] = get_m_network_20km()
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
            logger.info(f"커스텀 제한 구역 '{r}' 발견")
            custom.append(custom_restriction)
        elif hasattr(Passage, r):
            logger.info(f"기본 제한 구역 '{r}' 발견")
            default.append(getattr(Passage, r))
        else:
            logger.warning(f"알 수 없는 제한 구역: '{r}'")
            unknown.append(r)
    return custom, default, unknown


def _apply_restrictions_to_network(mnetwork: MNetwork, custom_restrictions:list[CustomRestriction], default_passages:list[Passage]):
    """
    네트워크 객체에 제한 구역을 적용
    """
    if not isinstance(mnetwork, MNetwork):
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
        logger.info(f"요청된 제한 구역: {restrictions}")
        custom_restrictions, default_passages, unknown_restrictions = _classify_restrictions(restrictions)

    _apply_restrictions_to_network(mnetwork, custom_restrictions, default_passages)

    logger.debug(f"등록된 제한 구역: {list_custom_restrictions()}")

    if "jwc" in list_custom_restrictions():
        jwc = get_custom_restriction("jwc")
        if jwc:
            logger.info(f"JWC 제한구역: {jwc.name}, Bounds: {jwc.polygon.bounds}")

    kwargs["M"] = mnetwork
    return _original_seavoyage(start, end, **kwargs)

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
    """
    restrictions = []
    
    # 기본 제한 구역 추가
    if default_restrictions:
        restrictions.extend(default_restrictions)
    
    # 커스텀 제한 구역 추가
    if custom_restrictions:
        restrictions.extend(custom_restrictions)
    
    return seavoyage(start, end, restrictions=restrictions, **kwargs)

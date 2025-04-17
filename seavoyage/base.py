import networkx as nx
from searoute import searoute
from searoute.classes.passages import Passage

from seavoyage.utils import get_m_network_20km
from seavoyage.modules.restriction import get_custom_restriction, list_custom_restrictions
from seavoyage.classes.m_network import MNetwork

_DEFAULT_MNETWORK = get_m_network_20km()

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
    # 기본 해양 네트워크 또는 parameter로 전달된 MNetwork네트워크 사용
    mnetwork: MNetwork = kwargs.pop("M", _DEFAULT_MNETWORK)
    
    # 기본 passage 제한 구역 설정 (searoute.classes.passages.Passage 클래스의 상수들)
    default_passages = []
    custom_restrictions = []
    
    if restrictions:
        print(f"요청된 제한 구역: {restrictions}")
        for r in restrictions:
            # 커스텀 제한 구역인지 확인
            custom_restriction = get_custom_restriction(r)
            if custom_restriction:
                print(f"커스텀 제한 구역 '{r}' 발견")
                custom_restrictions.append(custom_restriction)
            else:
                # 기본 passages 중 하나인지 확인
                if hasattr(Passage, r):
                    print(f"기본 제한 구역 '{r}' 발견")
                    default_passages.append(getattr(Passage, r))
                else:
                    print(f"알 수 없는 제한 구역: '{r}'")
    
    # 기본 제한 구역 설정
    mnetwork.restrictions = default_passages
    
    # 커스텀 제한 구역 추가
    for restriction in custom_restrictions:
        mnetwork.add_restriction(restriction)
    
    # 디버깅용 - 등록된 모든 제한 구역 출력
    print(f"등록된 제한 구역: {list_custom_restrictions()}")
    
    if "jwc" in list_custom_restrictions():
        jwc = get_custom_restriction("jwc")
        if jwc:
            print(f"JWC 제한구역: {jwc.name}, Bounds: {jwc.polygon.bounds}")
    
    # searoute 호출
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

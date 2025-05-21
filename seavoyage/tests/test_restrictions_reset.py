import pytest
import seavoyage as sv
from seavoyage.classes.m_network import MNetwork
from seavoyage.base import _DEFAULT_MNETWORK

def test_restriction_reset():
    """제한 구역 초기화가 제대로 동작하는지 테스트합니다."""
    # 테스트용 좌표 (싱가포르 - 방콕)
    start = (103.8198, 1.3521)  # 싱가포르
    end = (100.5167, 13.7500)  # 방콕
    
    # 첫 번째 호출: 말라카 해협 제한
    route1 = sv.seavoyage(start, end, restrictions=["malacca"])
    
    # 상태 확인 - 제한구역이 초기화되어야 함
    assert not _DEFAULT_MNETWORK.restrictions, "첫 번째 호출 후 제한 구역이 초기화되지 않았습니다."
    assert not _DEFAULT_MNETWORK.custom_restrictions, "첫 번째 호출 후 커스텀 제한 구역이 초기화되지 않았습니다."
    
    # 두 번째 호출: 제한 없음
    route2 = sv.seavoyage(start, end)
    
    # 두 경로가 달라야 함
    coords1 = route1['geometry']['coordinates']
    coords2 = route2['geometry']['coordinates']
    
    assert coords1 != coords2, "제한 구역을 설정한 경로와 설정하지 않은 경로가 동일합니다."
    
    # reset_restrictions=False로 테스트
    route3 = sv.seavoyage(start, end, restrictions=["malacca"], reset_restrictions=False)
    
    # 상태 확인 - 제한구역이 남아있어야 함
    assert "malacca" in _DEFAULT_MNETWORK.restrictions, "reset_restrictions=False 설정 후 제한 구역이 유지되지 않았습니다."
    
    # 이후 호출
    route4 = sv.seavoyage(start, end, reset_restrictions=True)
    
    # 상태 확인 - 제한구역이 초기화되어야 함
    assert not _DEFAULT_MNETWORK.restrictions, "마지막 호출 후 제한 구역이 초기화되지 않았습니다."
    
    # 경로 비교 - route4는 route2와 동일해야 함
    coords4 = route4['geometry']['coordinates']
    assert coords4 == coords2, "초기화 후 경로가 기대한 결과와 다릅니다."

def test_custom_seavoyage_restriction_reset():
    """custom_seavoyage 함수에서 제한 구역 초기화가 제대로 동작하는지 테스트합니다."""
    # 테스트용 좌표 (인도양 - 홍해 경로)
    start = (48.0, 12.0)  # 인도양
    end = (38.0, 25.0)    # 홍해 북부
    
    # 첫 번째 호출: 바브알만데브 해협 제한
    route1 = sv.custom_seavoyage(start, end, default_restrictions=["babalmandab"])
    
    # 상태 확인 - 제한구역이 초기화되어야 함
    assert not _DEFAULT_MNETWORK.restrictions, "첫 번째 호출 후 제한 구역이 초기화되지 않았습니다."
    
    # 두 번째 호출: 제한 없음
    route2 = sv.custom_seavoyage(start, end)
    
    # 두 경로가 달라야 함
    coords1 = route1['geometry']['coordinates']
    coords2 = route2['geometry']['coordinates']
    
    assert coords1 != coords2, "제한 구역을 설정한 경로와 설정하지 않은 경로가 동일합니다."
    
    # reset_restrictions=False로 테스트
    route3 = sv.custom_seavoyage(start, end, default_restrictions=["babalmandab"], reset_restrictions=False)
    
    # 상태 확인 - 제한구역이 남아있어야 함
    assert "babalmandab" in _DEFAULT_MNETWORK.restrictions, "reset_restrictions=False 설정 후 제한 구역이 유지되지 않았습니다."
    
    # 이후 호출
    route4 = sv.custom_seavoyage(start, end, reset_restrictions=True)
    
    # 상태 확인 - 제한구역이 초기화되어야 함
    assert not _DEFAULT_MNETWORK.restrictions, "마지막 호출 후 제한 구역이 초기화되지 않았습니다."
    
    # 경로 비교 - route4는 route2와 동일해야 함
    coords4 = route4['geometry']['coordinates']
    assert coords4 == coords2, "초기화 후 경로가 기대한 결과와 다릅니다." 
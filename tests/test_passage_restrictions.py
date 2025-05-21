import pytest
import numpy as np
from searoute.classes.passages import Passage
import seavoyage as sv

# 테스트에 사용할 좌표들
# 파나마 운하를 지나는 경로의 시작점과 종점
@pytest.fixture
def panama_coordinates():
    return {
        "start": [129.21748, 35.08084],  # 부산 근처
        "end": [-79.56988, 26.43456]     # 미국 플로리다 근처
    }

# 수에즈 운하를 지나는 경로의 시작점과 종점
@pytest.fixture
def suez_coordinates():
    return {
        "start": [129.21748, 35.08084],  # 부산 근처
        "end": [12.59, 55.68]            # 덴마크 코펜하겐 근처
    }

# 말라카 해협을 지나는 경로의 시작점과 종점
@pytest.fixture
def malacca_coordinates():
    return {
        "start": [129.21748, 35.08084],  # 부산 근처
        "end": [103.81, 1.35]            # 싱가포르 근처
    }

class TestPassageRestrictions:
    def test_panama_restriction(self, panama_coordinates):
        """파나마 제한 구역이 올바르게 적용되는지 테스트"""
        # 1. 제한 없이 경로 계산
        unrestricted_route = sv.seavoyage(
            panama_coordinates["start"], 
            panama_coordinates["end"]
        )
        
        # 2. 파나마 제한하여 경로 계산
        restricted_route = sv.seavoyage(
            panama_coordinates["start"], 
            panama_coordinates["end"], 
            restrictions=["panama"]
        )
        
        # 3. 두 경로의 길이 비교 (제한 경로가 더 길어야 함)
        unrestricted_length = unrestricted_route["properties"]["length"]
        restricted_length = restricted_route["properties"]["length"]
        
        # 제한 경로가 더 길어야 합니다 (우회하므로)
        assert restricted_length > unrestricted_length, \
            f"파나마 제한 경로({restricted_length})가 제한 없는 경로({unrestricted_length})보다 길어야 합니다"
    
    def test_suez_restriction(self, suez_coordinates):
        """수에즈 제한 구역이 올바르게 적용되는지 테스트"""
        # 1. 제한 없이 경로 계산
        unrestricted_route = sv.seavoyage(
            suez_coordinates["start"], 
            suez_coordinates["end"]
        )
        
        # 2. 수에즈 제한하여 경로 계산
        restricted_route = sv.seavoyage(
            suez_coordinates["start"], 
            suez_coordinates["end"], 
            restrictions=["suez"]
        )
        
        # 3. 두 경로의 길이 비교 (제한 경로가 더 길어야 함)
        unrestricted_length = unrestricted_route["properties"]["length"]
        restricted_length = restricted_route["properties"]["length"]
        
        # 제한 경로가 더 길어야 합니다 (우회하므로)
        assert restricted_length > unrestricted_length, \
            f"수에즈 제한 경로({restricted_length})가 제한 없는 경로({unrestricted_length})보다 길어야 합니다"
    
    def test_malacca_restriction(self, malacca_coordinates):
        """말라카 제한 구역이 올바르게 적용되는지 테스트"""
        # 1. 제한 없이 경로 계산
        unrestricted_route = sv.seavoyage(
            malacca_coordinates["start"], 
            malacca_coordinates["end"]
        )
        
        # 2. 말라카 제한하여 경로 계산
        restricted_route = sv.seavoyage(
            malacca_coordinates["start"], 
            malacca_coordinates["end"], 
            restrictions=["malacca"]
        )
        
        # 3. 두 경로의 길이 비교 (제한 경로가 더 길어야 함)
        unrestricted_length = unrestricted_route["properties"]["length"]
        restricted_length = restricted_route["properties"]["length"]
        
        # 제한 경로가 더 길어야 합니다 (우회하므로)
        assert restricted_length > unrestricted_length, \
            f"말라카 제한 경로({restricted_length})가 제한 없는 경로({unrestricted_length})보다 길어야 합니다"
    
    def test_multiple_restrictions(self, panama_coordinates):
        """여러 제한 구역이 동시에 올바르게 적용되는지 테스트"""
        # 1. 제한 없이 경로 계산
        unrestricted_route = sv.seavoyage(
            panama_coordinates["start"], 
            panama_coordinates["end"]
        )
        
        # 2. 여러 제한 구역을 설정하여 경로 계산
        restricted_route = sv.seavoyage(
            panama_coordinates["start"], 
            panama_coordinates["end"], 
            restrictions=["panama", "suez", "malacca"]
        )
        
        # 3. 두 경로의 길이 비교 (제한 경로가 더 길어야 함)
        unrestricted_length = unrestricted_route["properties"]["length"]
        restricted_length = restricted_route["properties"]["length"]
        
        # 제한 경로가 더 길어야 합니다 (우회하므로)
        assert restricted_length > unrestricted_length, \
            f"다중 제한 경로({restricted_length})가 제한 없는 경로({unrestricted_length})보다 길어야 합니다"
    
    def test_all_passage_restrictions(self):
        """Passage 클래스의 모든 제한 구역이 올바르게 처리되는지 테스트"""
        start = [129.21748, 35.08084]  # 부산 근처
        end = [-79.56988, 26.43456]    # 미국 플로리다 근처
        
        # 제한 없는 경로 계산
        unrestricted_route = sv.seavoyage(start, end)
        unrestricted_length = unrestricted_route["properties"]["length"]
        
        # Passage 클래스의 모든 유효한 제한 구역 가져오기
        valid_passages = Passage.valid_passages()
        
        # 각 제한 구역별로 테스트
        for passage_name in valid_passages:
            # 단일 제한 구역 설정
            restricted_route = sv.seavoyage(start, end, restrictions=[passage_name])
            restricted_length = restricted_route["properties"]["length"]
            
            # 경로가 제한 구역을 우회하는지 확인 (길이 변화를 통해)
            # 모든 제한 구역이 출발지-목적지 사이에 있지 않을 수 있으므로,
            # 길이가 같거나 길어야 합니다.
            assert restricted_length >= unrestricted_length, \
                f"{passage_name} 제한 시 경로 길이({restricted_length})가 " \
                f"제한 없는 경로 길이({unrestricted_length})보다 짧습니다."
    
    def test_preserving_existing_restrictions(self):
        """
        기존 제한 구역 설정이 유지되는지 테스트
        (이전 버그: 새 제한 구역이 기존 제한 구역을 덮어씀)
        """
        # 테스트 좌표
        start = [129.21748, 35.08084]  # 부산 근처
        end = [-79.56988, 26.43456]    # 미국 플로리다 근처
        
        # 1. northwest 제한으로 경로 계산
        route1 = sv.seavoyage(start, end, restrictions=["northwest"])
        
        # 2. panama 제한으로 경로 계산 
        route2 = sv.seavoyage(start, end, restrictions=["panama"])
        
        # 3. 둘 다 제한하여 경로 계산
        route3 = sv.seavoyage(start, end, restrictions=["northwest", "panama"])
        
        # 각 경로의 길이
        len1 = route1["properties"]["length"]
        len2 = route2["properties"]["length"]
        len3 = route3["properties"]["length"]
        
        # 두 제한을 모두 적용한 경로는 각각의 제한을 적용한 경로보다 길거나 같아야 함
        # (두 제한을 모두 우회해야 하므로)
        assert len3 >= len1, "두 제한 경로가 northwest 제한 경로보다 짧습니다"
        assert len3 >= len2, "두 제한 경로가 panama 제한 경로보다 짧습니다" 
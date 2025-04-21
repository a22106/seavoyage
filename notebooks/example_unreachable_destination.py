"""
경로 도달 불가능 예외 처리 예제
"""
import sys
sys.path.append("..")

import seavoyage as sv
from seavoyage.exceptions import (
    RouteError, 
    StartInRestrictionError, 
    DestinationInRestrictionError, 
    UnreachableDestinationError
)

# 제한구역 등록
print("=== 제한구역 등록 ===")
sv.register_custom_restriction('jwc', "./restrictions/jwc.geojson")

# 정상 경로 계산 (제한구역 밖의 출발점/도착점)
print("\n=== 정상 경로 계산 ===")
try:
    normal_start = (132.0, 34.3)     # JWC 바깥의 출발점
    normal_end = (136.0, 34.3)       # JWC 바깥의 도착점
    
    # 제한구역 없는 경로 계산
    print(f"출발점: {normal_start}, 도착점: {normal_end}")
    normal_route = sv.seavoyage(normal_start, normal_end)
    print(f"정상 경로 거리: {normal_route['properties']['length']:.2f} km")
except RouteError as e:
    print(f"경로 오류: {str(e)}")

# 도착점이 제한구역 내에 있는 경우
print("\n=== 도착점이 제한구역 내에 있는 경우 ===")
try:
    start = (132.0, 34.3)            # JWC 바깥의 출발점
    end_in_restriction = (57.0, 24.828)   # JWC 내부의 도착점
    
    print(f"출발점: {start}, 도착점: {end_in_restriction}")
    sv.seavoyage(start, end_in_restriction, restrictions=['jwc'])
except StartInRestrictionError as e:
    print(f"출발점 제한구역 오류: {str(e)}")
except DestinationInRestrictionError as e:
    print(f"도착점 제한구역 오류: {str(e)}")
except UnreachableDestinationError as e:
    print(f"경로 도달 불가 오류: {str(e)}")
except RouteError as e:
    print(f"기타 경로 오류: {str(e)}")

# 출발점이 제한구역 내에 있는 경우
print("\n=== 출발점이 제한구역 내에 있는 경우 ===")
try:
    start_in_restriction = (57.0, 24.828)  # JWC 내부의 출발점
    end = (132.0, 34.3)                   # JWC 바깥의 도착점
    
    print(f"출발점: {start_in_restriction}, 도착점: {end}")
    sv.seavoyage(start_in_restriction, end, restrictions=['jwc'])
except StartInRestrictionError as e:
    print(f"출발점 제한구역 오류: {str(e)}")
except DestinationInRestrictionError as e:
    print(f"도착점 제한구역 오류: {str(e)}")
except UnreachableDestinationError as e:
    print(f"경로 도달 불가 오류: {str(e)}")
except RouteError as e:
    print(f"기타 경로 오류: {str(e)}")

# 경로가 생성될 수 없는 경우 (제한구역으로 막힌 경우)
print("\n=== 경로가 제한구역으로 막혀 생성 불가능한 경우 ===")
try:
    # 제한구역으로 인해 경로가 불가능한 점 찾기
    start = (135.0, 50.0)  # 북위 50도, 동경 135도 (러시아 사할린 북부)
    end = (110.0, 20.0)    # 북위 20도, 동경 110도 (중국 남부)
    
    print(f"출발점: {start}, 도착점: {end}")
    sv.seavoyage(start, end, restrictions=['jwc'])
except StartInRestrictionError as e:
    print(f"출발점 제한구역 오류: {str(e)}")
except DestinationInRestrictionError as e:
    print(f"도착점 제한구역 오류: {str(e)}")
except UnreachableDestinationError as e:
    print(f"경로 도달 불가 오류: {str(e)}")
except RouteError as e:
    print(f"기타 경로 오류: {str(e)}")
except Exception as e:
    print(f"예상치 못한 오류: {str(e)}") 
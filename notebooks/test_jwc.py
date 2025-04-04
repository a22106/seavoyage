import sys
sys.path.append('..')

from seavoyage import seavoyage, list_custom_restrictions, get_custom_restriction
import json

def print_jwc_info():
    """JWC 제한구역 정보 출력"""
    if "jwc" in list_custom_restrictions():
        jwc = get_custom_restriction("jwc")
        if jwc:
            print(f"JWC 제한구역 경계: {jwc.polygon.bounds}")
            print(f"JWC 제한구역 면적: {jwc.polygon.area:.6f}")
    else:
        print("JWC 제한구역이 등록되지 않았습니다.")

def test_jwc_restriction():
    # JWC 제한구역 정보 출력
    print("==== JWC 제한구역 정보 ====")
    print_jwc_info()
    
    # JWC 제한구역: (132.35-135.55, 33.87-34.79)
    # 의도적으로 JWC를 통과하는 경로 지정
    start_point = (132.0, 34.3)  # JWC 서쪽 경계 바로 옆
    end_point = (136.0, 34.3)    # JWC 동쪽 경계 바로 옆

    print("\n==== 경로 테스트 ====")
    print(f"출발지: {start_point}")
    print(f"목적지: {end_point}")
    
    # 제한 구역 없는 경로 계산
    print("\n1. 일반 경로 계산 중...")
    normal_route = seavoyage(
        start_point, 
        end_point
    )
    
    # JWC 제한 구역 적용한 경로 계산
    print("\n2. JWC 제한 구역 적용 경로 계산 중...")
    restricted_route = seavoyage(
        start_point, 
        end_point,
        restrictions=['jwc']
    )
    
    # 경로 정보 출력
    print("\n==== 경로 비교 ====")
    print("일반 경로 좌표:")
    for coord in normal_route["geometry"]["coordinates"]:
        print(f"  {coord}")
    
    print("\nJWC 제한 구역 적용 경로 좌표:")
    for coord in restricted_route["geometry"]["coordinates"]:
        print(f"  {coord}")
    
    # 두 경로가 다른지 확인
    if normal_route == restricted_route:
        print("\n⚠️ 경로가 동일합니다! 제한구역이 올바르게 적용되지 않았을 수 있습니다.")
    else:
        print("\n✅ 경로가 다릅니다. 제한구역이 올바르게 적용되었습니다.")

    # 두 경로의 거리 비교
    normal_length = normal_route["properties"]["length"]
    restricted_length = restricted_route["properties"]["length"]
    
    print(f"\n일반 경로 거리: {normal_length:.2f} km")
    print(f"제한구역 적용 경로 거리: {restricted_length:.2f} km")
    
    if restricted_length > normal_length:
        diff = restricted_length - normal_length
        percent = (diff / normal_length) * 100
        print(f"차이: +{diff:.2f} km ({percent:.2f}% 증가)")
    else:
        diff = normal_length - restricted_length
        percent = (diff / normal_length) * 100
        print(f"차이: -{diff:.2f} km ({percent:.2f}% 감소)")
        
    return normal_route, restricted_route

if __name__ == "__main__":
    test_jwc_restriction() 
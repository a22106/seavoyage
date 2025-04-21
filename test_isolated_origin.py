#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
고립된 출발점 테스트 스크립트
"""

import sys
import os

# 현재 디렉토리의 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import seavoyage as sv
from seavoyage.exceptions import IsolatedOriginError, UnreachableDestinationError
    
def test_manual_isolation():
    """출발점 주변을 모든 방향에서 제한 구역으로 둘러싸 명시적으로 고립시킵니다."""
    try:
        # 원 모양의 제한 구역을 만들어 출발점을 둘러쌈
        import json
        from shapely.geometry import Point, mapping
        from shapely.geometry.polygon import Polygon
        import tempfile
        from shapely.ops import unary_union
        
        # 출발점
        origin = (30.0, 30.0)
        # 도착점 (멀리 떨어진 곳)
        destination = (35.0, 35.0)
        
        # 출발점 주변에 원 형태의 제한구역 생성
        center = Point(origin)
        buffer_distance = 0.5  # 반경 50km
        circle = center.buffer(buffer_distance)
        # 출발점 자체는 제외 (구멍)
        point_buffer = center.buffer(0.05)  # 작은 반경
        ring = Polygon(circle.exterior.coords, [point_buffer.exterior.coords])
        
        # GeoJSON으로 변환
        geo_json = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", 
                "properties": {}, 
                "geometry": mapping(ring)
            }]
        }
        
        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(suffix='.geojson', delete=False, mode='w') as temp:
            json.dump(geo_json, temp)
            temp_path = temp.name
        
        # 제한 구역 등록
        sv.register_custom_restriction('isolation_ring', temp_path)
        print(f"\n--- 명시적 고립 테스트 ---")
        print(f"출발점 {origin} 주변에 원형 제한 구역 생성")
        
        try:
            route = sv.seavoyage(
                origin,
                destination,
                restrictions=['isolation_ring']
            )
            print("고립된 출발점에서 경로 생성 성공 (실패해야 함)")
            # 임시 파일 삭제
            os.unlink(temp_path)
            return False
        except IsolatedOriginError as e:
            print(f"테스트 성공: {e}")
            # 임시 파일 삭제
            os.unlink(temp_path)
            return True
        except Exception as e:
            print(f"예상치 못한 오류: {e}")
            # 임시 파일 삭제
            os.unlink(temp_path)
            return False
            
    except Exception as e:
        print(f"테스트 준비 중 오류: {e}")
        return False

def main():
    print("고립된 출발점 테스트 시작...")
    
    # 명시적 고립 테스트
    test_result = test_manual_isolation()
    
    if test_result:
        print("\n테스트 성공!")
        return 0
    else:
        print("\n테스트 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
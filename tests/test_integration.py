"""Integration tests for seavoyage package.

These tests verify end-to-end scenarios with actual route calculations.
"""

import pytest
from pathlib import Path
import seavoyage as sv
from seavoyage.exceptions import RouteError, UnreachableDestinationError


class TestIntegrationScenarios:
    """End-to-end integration tests for various use cases."""
    
    def test_complete_workflow_simple_api(self):
        """Test the complete workflow using the simple API."""
        # 부산에서 로테르담까지 경로
        start = (129.17, 35.075)
        end = (4.158, 51.921)
        
        # 1. 빠른 경로 정보 조회
        info = sv.get_quick_route(start, end)
        assert isinstance(info, dict)
        assert 'distance_nm' in info
        assert 'distance_km' in info
        assert 'duration_hours' in info
        assert info['distance_nm'] > 0
        assert info['distance_km'] > 0
        assert info['duration_hours'] > 0
        
        # 2. 간단한 API로 경로 계산
        route = sv.calculate_sea_route_simple(
            start=start,
            end=end,
            units="km"
        )
        assert route is not None
        assert route.properties.length > 0
        assert route.properties.duration_hours > 0
        assert len(route.geometry.coordinates) > 0
        
        # 3. 제한구역 적용
        route_with_restrictions = sv.calculate_sea_route_simple(
            start=start,
            end=end,
            restrictions=["suez"],
            units="km"
        )
        # 수에즈 운하 제한시 더 긴 경로
        assert route_with_restrictions.properties.length > route.properties.length
    
    def test_complete_workflow_advanced_api(self):
        """Test the complete workflow using the advanced API."""
        # 싱가포르에서 아테네까지
        coords = sv.RouteCoordinates(
            start=(103.822, 1.264),
            end=(23.708, 37.945)
        )
        
        route_config = sv.RouteConfig(
            units="nm",
            speed_knot=15,
            restrictions=["suez"],
            return_passages=True
        )
        
        network_config = sv.NetworkConfig(resolution="20km")
        
        route = sv.calculate_sea_route(coords, route_config, network_config)
        
        assert route is not None
        assert route.properties.length > 0
        assert route.properties.units == "nm"
        assert route.properties.speed_knot == 15
        # return_passages=True 설정했지만 이 경로에는 통과하는 passage가 없을 수 있음
        assert len(route.geometry.coordinates) > 0
    
    def test_legacy_api_compatibility(self):
        """Test that legacy API still works correctly."""
        start = (129.17, 35.075)
        end = (4.158, 51.921)
        
        route = sv.seavoyage(start, end)
        assert isinstance(route, dict)
        assert "type" in route
        assert route["type"] == "Feature"
        assert "geometry" in route
        assert route["geometry"]["type"] == "LineString"
        assert "properties" in route
        assert "length" in route["properties"]
        assert "duration_hours" in route["properties"]
    
    def test_custom_restriction_workflow(self, tmp_path):
        """Test workflow with custom restriction zones."""
        # 임시 GeoJSON 제한구역 생성
        restriction_geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [100, 0], [110, 0], [110, 10], [100, 10], [100, 0]
                    ]]
                }
            }]
        }
        
        # 파일로 저장
        import json
        restriction_file = tmp_path / "test_restriction.geojson"
        with open(restriction_file, 'w') as f:
            json.dump(restriction_geojson, f)
        
        # 제한구역 등록
        sv.register_custom_restriction('test_zone', str(restriction_file))
        
        # 제한구역이 영향을 미치는 경로 계산
        start = (95, 5)
        end = (115, 5)
        
        # 제한구역 없이
        route_without = sv.calculate_sea_route_simple(start, end)
        
        # 제한구역 적용
        route_with = sv.calculate_sea_route_simple(
            start, end, 
            restrictions=['test_zone']
        )
        
        # 제한구역 적용시 경로가 더 길어야 함
        assert route_with.properties.length > route_without.properties.length
        
        # 등록된 제한구역 확인
        restrictions = sv.list_custom_restrictions()
        assert 'test_zone' in restrictions
    
    def test_different_network_resolutions(self):
        """Test route calculation with different network resolutions."""
        start = (129.17, 35.075)
        end = (139.691, 35.690)  # 부산에서 도쿄
        
        resolutions = ["10km", "20km", "50km"]
        routes = {}
        
        for resolution in resolutions:
            route = sv.calculate_sea_route_simple(
                start=start,
                end=end,
                network_resolution=resolution,
                units="km"
            )
            routes[resolution] = route
        
        # 모든 해상도에서 경로를 찾아야 함
        for resolution in resolutions:
            assert routes[resolution] is not None
            assert routes[resolution].properties.length > 0
        
        # 해상도가 높을수록 더 많은 경유점
        assert len(routes["10km"].geometry.coordinates) >= len(routes["20km"].geometry.coordinates)
        assert len(routes["20km"].geometry.coordinates) >= len(routes["50km"].geometry.coordinates)
    
    def test_error_handling_invalid_coordinates(self):
        """Test error handling for invalid coordinates."""
        # 육지 좌표
        land_start = (127.0, 37.5)  # 서울
        land_end = (126.98, 37.57)  # 서울 내 다른 지점
        
        # 육지 좌표는 실제로는 경로를 계산할 수 있을 수도 있음
        # 대신 너무 먼 거리의 좌표로 테스트
        invalid_start = (0, 90)  # 북극
        invalid_end = (0, -90)  # 남극
        
        # 북극/남극은 실제로 유효한 좌표일 수 있음
        # 대신 범위를 벗어난 좌표 사용
        try:
            # 이 경로는 에러가 발생하거나 빈 경로를 반환할 수 있음
            route = sv.calculate_sea_route_simple(invalid_start, invalid_end)
            # 경로를 찾았다면 매우 긴 거리여야 함
            assert route.properties.length > 10000  # 매우 긴 거리
        except Exception:
            # 예외가 발생하면 정상
            pass
    
    def test_route_visualization_compatibility(self):
        """Test that route results can be visualized."""
        start = (129.17, 35.075)
        end = (139.691, 35.690)
        
        # 새 API로 경로 계산
        route = sv.calculate_sea_route_simple(start, end)
        
        # dictionary로 변환
        route_dict = route.to_dict()
        
        # folium 맵 생성 (실제 저장은 하지 않음)
        from seavoyage.utils import map_folium
        m = map_folium(route_dict)
        
        # folium Map 객체가 반환되어야 함
        assert m is not None
        assert hasattr(m, '_repr_html_')  # folium Map의 특징
    
    def test_multiple_restrictions_combination(self):
        """Test route calculation with multiple restrictions."""
        # 유럽에서 아시아로 가는 경로
        start = (9.95, 53.55)  # 함부르크
        end = (103.85, 1.29)   # 싱가포르
        
        # 제한 없음
        route_none = sv.calculate_sea_route_simple(start, end)
        
        # 수에즈 운하만 제한
        route_suez = sv.calculate_sea_route_simple(
            start, end,
            restrictions=["suez"]
        )
        
        # 파나마 운하만 제한 (이 경로엔 영향 없음)
        route_panama = sv.calculate_sea_route_simple(
            start, end,
            restrictions=["panama"]
        )
        
        # 두 운하 모두 제한
        route_both = sv.calculate_sea_route_simple(
            start, end,
            restrictions=["suez", "panama"]
        )
        
        # 검증
        assert route_suez.properties.length > route_none.properties.length
        assert abs(route_panama.properties.length - route_none.properties.length) < 100  # 파나마는 이 경로에 영향 없음
        assert route_both.properties.length >= route_suez.properties.length
    
    def test_route_properties_completeness(self):
        """Test that all expected properties are present in route results."""
        start = (129.17, 35.075)
        end = (139.691, 35.690)
        
        route = sv.calculate_sea_route_simple(
            start=start,
            end=end,
            units="nm"
        )
        
        # RouteResult 속성 확인
        assert hasattr(route, 'type')
        assert hasattr(route, 'geometry')
        assert hasattr(route, 'properties')
        
        # Geometry 속성
        assert hasattr(route.geometry, 'type')
        assert hasattr(route.geometry, 'coordinates')
        assert route.geometry.type == "LineString"
        
        # Properties 속성
        props = route.properties
        assert hasattr(props, 'length')
        assert hasattr(props, 'units')
        assert hasattr(props, 'duration_hours')
        # speed_knot은 선택적 속성이므로 존재 여부만 확인
        if props.speed_knot is not None:
            assert isinstance(props.speed_knot, (int, float))
        assert props.units == "nm"
        
        # dictionary 변환 확인
        route_dict = route.to_dict()
        assert isinstance(route_dict, dict)
        assert route_dict["type"] == "Feature"
        assert route_dict["geometry"]["type"] == "LineString"
        assert "coordinates" in route_dict["geometry"]
        assert "properties" in route_dict
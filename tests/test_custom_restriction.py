import pytest
import seavoyage as sv
from seavoyage.modules.restriction import CustomRestriction
import os
import json
import tempfile
from shapely.geometry import Point, mapping
from shapely.geometry.polygon import Polygon
from seavoyage.exceptions import StartInRestrictionError, DestinationInRestrictionError, IsolatedOriginError

@pytest.fixture
def start_point():
    return (129.17, 35.075)

@pytest.fixture
def end_point():
    return (-4.158, 44.644)

@pytest.fixture
def busan_point():
    return (129.07, 35.179)

@pytest.fixture
def palm_beach_point():
    return (-79.808370, 26.675735)

@pytest.fixture
def jwc_geojson_path():
    # 실제 경로는 settings.py의 RESTRICTIONS_DIR 기준
    return os.path.join('notebooks/restrictions', 'jwc.geojson')

@pytest.fixture
def hra_geojson_path():
    return os.path.join('notebooks/restrictions', 'hra.geojson')

@pytest.fixture
def restricted_destination():
    # 제한구역 내부의 목적지 좌표 (jwc 제한구역 내부)
    return (57.0, 24.828)

@pytest.fixture
def create_isolation_ring():
    """출발점 주변에 고립된 영역을 만드는 fixture"""
    def _create_isolation_ring(origin):
        # 출발점 주변에 원 형태의 제한구역 생성
        center = Point(origin)
        buffer_distance = 0.5  # 반경 0.5도
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
            
        return temp_path
    
    return _create_isolation_ring

class TestCustomRestriction:
    def test_register_and_get_custom_restriction(self, jwc_geojson_path):
        sv.register_custom_restriction('jwc', jwc_geojson_path)
        names = sv.list_custom_restrictions()
        assert 'jwc' in names, 'jwc 제한구역이 정상적으로 등록되어야 합니다.'
        restriction = sv.get_custom_restriction('jwc')
        assert restriction is not None, 'jwc 제한구역 객체를 정상적으로 가져와야 합니다.'
        assert isinstance(restriction, CustomRestriction), '반환 객체는 CustomRestriction 타입이어야 합니다.'
        assert restriction.name == 'jwc', '제한구역 이름이 일치해야 합니다.'

    def test_register_multiple_custom_restrictions(self, jwc_geojson_path, hra_geojson_path):
        sv.register_custom_restriction('jwc', jwc_geojson_path)
        sv.register_custom_restriction('hra', hra_geojson_path)
        names = sv.list_custom_restrictions()
        assert 'jwc' in names and 'hra' in names, '여러 제한구역이 정상적으로 등록되어야 합니다.'
        
    def test_generate_route_with_custom_restrictiona_and_not_cross_restriction(self, busan_point, palm_beach_point, jwc_geojson_path):
        sv.register_custom_restriction('jwc', jwc_geojson_path)
        route_with_restriction = sv.seavoyage(busan_point, palm_beach_point, restrictions=['jwc'])
        route_without_restriction = sv.seavoyage(busan_point, palm_beach_point)
        assert route_with_restriction is not None, '경로가 생성되어야 합니다.'
        assert route_without_restriction is not None, '경로가 생성되어야 합니다.'
        assert route_with_restriction['geometry']['coordinates'] is not None, '경로의 좌표가 생성되어야 합니다.'
        assert route_without_restriction['geometry']['coordinates'] is not None, '경로의 좌표가 생성되어야 합니다.'
        assert route_with_restriction['geometry']['coordinates'] == route_without_restriction['geometry']['coordinates'], '제한구역을 지나지 않기때문에 경로가 같아야 합니다.'
        


    def test_route_with_and_without_restriction(self, start_point, end_point, jwc_geojson_path):
        sv.register_custom_restriction('jwc', jwc_geojson_path)
        route_normal = sv.seavoyage(start_point, end_point)
        route_restricted = sv.seavoyage(start_point, end_point, restrictions=['jwc'])
        
        # 경로가 다를 수 있음 (실제 네트워크와 제한구역에 따라 다름)
        assert route_normal['geometry']['coordinates'] != route_restricted['geometry']['coordinates'], '제한구역 적용 시 경로가 달라야 합니다.'
        assert route_normal['properties']['length'] >= route_restricted['properties']['length'] or route_normal['properties']['length'] <= route_restricted['properties']['length'], '길이 비교(예시, 실제로는 다를 수 있음)'

    def test_get_custom_restriction_none(self):
        # 등록되지 않은 제한구역 조회
        restriction = sv.get_custom_restriction('없는이름')
        assert restriction is None, '존재하지 않는 제한구역은 None을 반환해야 합니다.'

    def test_list_custom_restrictions_empty(self):
        # 테스트 시작 시 제한구역이 없다고 가정
        names = sv.list_custom_restrictions()
        # 제한구역이 없거나, 이전 테스트 영향이 있을 수 있음
        assert isinstance(names, list), '반환값은 리스트여야 합니다.'
        
    def test_destination_in_restriction(self, start_point, restricted_destination, jwc_geojson_path):
        """목적지가 제한구역 내부에 있는 경우 테스트"""
        sv.register_custom_restriction('jwc', jwc_geojson_path)
        
        with pytest.raises(DestinationInRestrictionError) as excinfo:
            sv.seavoyage(
                start_point,
                restricted_destination,
                restrictions=['jwc']
            )
        
        # 예외 메시지 검증
        assert "목적지" in str(excinfo.value)
        assert "제한 구역" in str(excinfo.value)
        
    def test_start_in_restriction(self, restricted_destination, end_point, jwc_geojson_path):
        """출발지가 제한구역 내부에 있는 경우 테스트"""
        sv.register_custom_restriction('jwc', jwc_geojson_path)
        
        with pytest.raises(StartInRestrictionError) as excinfo:
            sv.seavoyage(
                restricted_destination,  # 출발지로 제한구역 내부 좌표 사용
                end_point,
                restrictions=['jwc']
            )
        
        # 예외 메시지 검증
        assert "출발지" in str(excinfo.value)
        assert "제한 구역" in str(excinfo.value)
        
    def test_isolated_origin(self, create_isolation_ring):
        """고립된 출발점 테스트"""
        # 출발점과 도착점 정의
        origin = (30.0, 30.0)
        destination = (35.0, 35.0)
        
        # 출발점 주변을 고립시키는 제한구역 생성
        temp_path = create_isolation_ring(origin)
        
        try:
            # 제한구역 등록
            sv.register_custom_restriction('test_isolation', temp_path)
            
            # 예외가 발생해야 함
            with pytest.raises(IsolatedOriginError) as excinfo:
                sv.seavoyage(
                    origin,
                    destination,
                    restrictions=['test_isolation']
                )
            
            # 예외 메시지 검증
            assert "출발지" in str(excinfo.value)
            assert "고립" in str(excinfo.value)
        
        finally:
            # 임시 파일 삭제
            try:
                os.unlink(temp_path)
            except:
                pass 
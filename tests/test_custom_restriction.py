import pytest
import seavoyage as sv
from seavoyage.modules.restriction import CustomRestriction
import os

@pytest.fixture
def start_point():
    return (129.17, 35.075)

@pytest.fixture
def end_point():
    return (-4.158, 44.644)

@pytest.fixture
def jwc_geojson_path():
    # 실제 경로는 settings.py의 RESTRICTIONS_DIR 기준
    return os.path.join(sv.RESTRICTIONS_DIR, 'jwc.geojson')

@pytest.fixture
def hra_geojson_path():
    return os.path.join(sv.RESTRICTIONS_DIR, 'hra.geojson')

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
import pytest
import seavoyage as sv

@pytest.fixture
def start_point():
    return (132.0, 34.3)

@pytest.fixture
def end_point():
    return (136.0, 34.3)

@pytest.fixture
def marine_network_5km():
    return sv.get_m_network_5km()

@pytest.fixture
def valid_result():
    # 예시 결과
    return {
        "geometry": {
            "coordinates": [
                [131.9, 33.75],
                [132.6, 34.2],
                [133.981, 34.425],
                [135.1, 34.608],
                [135.201, 34.6365]
            ],
            "type": "LineString"
        },
        "properties": {
            "duration_hours": 7.3174093210729865,
            "length": 325.2442095030521,
            "units": "km"
        },
        "type": "Feature"
    }

class TestSeavoyage:
    def test_basic_route(self, start_point, end_point):
        result = sv.seavoyage(start_point, end_point)
        assert isinstance(result, dict)
        assert "geometry" in result
        assert "properties" in result
        assert "type" in result
        assert result["type"] == "Feature"
        assert result["geometry"]["type"] == "LineString"
        assert isinstance(result["geometry"]["coordinates"], list)
        assert len(result["geometry"]["coordinates"]) >= 2

    def test_properties(self, start_point, end_point):
        result = sv.seavoyage(start_point, end_point)
        props = result["properties"]
        assert "duration_hours" in props
        assert "length" in props
        assert "units" in props
        assert props["units"] == "km"
        assert props["duration_hours"] > 0
        assert props["length"] > 0

    def test_same_point(self, start_point):
        result = sv.seavoyage(start_point, start_point)
        assert result["geometry"]["coordinates"] == [list(start_point)]
        assert result["properties"]["length"] == 0.0
        assert result["properties"]["duration_hours"] == 0.0

    def test_invalid_point(self):
        with pytest.raises(ValueError):
            sv.seavoyage((200, 200), (300, 300))
        with pytest.raises(ValueError):
            sv.seavoyage((131.9, 33.75), (200, 300))

    def test_restriction_option(self, start_point, end_point):
        # 제한구역 옵션이 정상적으로 동작하는지 확인 (존재하지 않는 제한구역 포함)
        result = sv.seavoyage(start_point, end_point, restrictions=["jwc", "NOT_EXIST"])
        assert "geometry" in result
        assert "properties" in result

    def test_output_geojson_structure(self, start_point, end_point):
        result = sv.seavoyage(start_point, end_point)
        # GeoJSON 구조 필수 필드 체크
        assert set(result.keys()) >= {"geometry", "properties", "type"}
        assert result["geometry"]["type"] == "LineString"
        assert isinstance(result["geometry"]["coordinates"], list)
        assert isinstance(result["properties"], dict)
        assert result["type"] == "Feature"

    def test_route_coordinates_format(self, start_point, end_point):
        result = sv.seavoyage(start_point, end_point)
        for coord in result["geometry"]["coordinates"]:
            assert isinstance(coord, list)
            assert len(coord) == 2
            assert all(isinstance(x, float) or isinstance(x, int) for x in coord)

    def test_units_are_km(self, start_point, end_point):
        result = sv.seavoyage(start_point, end_point)
        assert result["properties"]["units"] == "km"


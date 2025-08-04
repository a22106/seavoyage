"""
Tests for the new improved API
"""
import pytest
from seavoyage import (
    calculate_sea_route, calculate_sea_route_simple, get_quick_route,
    RouteConfig, NetworkConfig, RouteCoordinates, RouteResult
)


def test_get_quick_route():
    """Test the quick route function"""
    start = (129.17, 35.075)  # Busan
    end = (4.158, 51.921)     # Rotterdam
    
    info = get_quick_route(start, end)
    
    assert isinstance(info, dict)
    assert "distance_nm" in info
    assert "distance_km" in info
    assert "duration_hours" in info
    assert "waypoints_count" in info
    
    assert info["distance_nm"] > 0
    assert info["distance_km"] > 0
    assert info["duration_hours"] > 0
    assert info["waypoints_count"] > 2


def test_calculate_sea_route_simple():
    """Test the simplified API"""
    start = (129.17, 35.075)
    end = (4.158, 51.921)
    
    route = calculate_sea_route_simple(
        start=start,
        end=end,
        units="km"
    )
    
    assert isinstance(route, RouteResult)
    assert route.type == "Feature"
    assert route.geometry.type == "LineString"
    assert len(route.geometry.coordinates) > 2
    assert route.properties.length > 0
    assert route.properties.duration_hours > 0
    assert route.properties.units == "km"


def test_calculate_sea_route_with_config():
    """Test the advanced API with configuration objects"""
    coords = RouteCoordinates(
        start=(103.822, 1.264),  # Singapore (lon, lat)
        end=(23.708, 37.945)     # Athens (lon, lat)
    )
    
    route_config = RouteConfig(
        units="nm",
        speed_knot=15
    )
    
    route = calculate_sea_route(coords, route_config)
    
    assert isinstance(route, RouteResult)
    assert route.properties.units == "nm"
    assert route.properties.length > 0
    
    # Duration should be different with 15 knots vs default 10
    default_route = calculate_sea_route(coords)
    assert route.properties.duration_hours < default_route.properties.duration_hours


def test_route_result_conversion():
    """Test conversion between dict and RouteResult"""
    start = (129.17, 35.075)
    end = (4.158, 51.921)
    
    route = calculate_sea_route_simple(start, end)
    
    # Convert to dict
    route_dict = route.to_dict()
    assert isinstance(route_dict, dict)
    assert route_dict["type"] == "Feature"
    
    # Convert back to RouteResult
    route2 = RouteResult.from_dict(route_dict)
    assert isinstance(route2, RouteResult)
    assert route2.properties.length == route.properties.length
    assert route2.properties.duration_hours == route.properties.duration_hours


def test_route_coordinates_validation():
    """Test RouteCoordinates validation"""
    # Valid coordinates
    coords = RouteCoordinates(
        start=(129.17, 35.075),
        end=(4.158, 51.921)
    )
    assert coords.start == (129.17, 35.075)
    assert coords.end == (4.158, 51.921)
    
    # Invalid coordinates should raise error
    with pytest.raises(ValueError):
        RouteCoordinates(start=[129.17, 35.075], end=(4.158, 51.921))
    
    with pytest.raises(ValueError):
        RouteCoordinates(start=(129.17,), end=(4.158, 51.921))


def test_identical_start_end():
    """Test route calculation with identical start and end points"""
    point = (129.17, 35.075)
    
    route = calculate_sea_route_simple(point, point)
    
    assert route.properties.length == 0
    assert route.properties.duration_hours == 0
    assert len(route.geometry.coordinates) == 1
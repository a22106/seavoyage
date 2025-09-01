"""
Test validation and security features
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock

from seavoyage.utils.validation import (
    validate_coordinates,
    validate_coordinate_pair,
    validate_geojson_structure,
    validate_geojson_geometry,
    validate_geojson_file,
    validate_restriction_zone,
    validate_network_resolution,
    validate_speed,
    validate_units,
    validate_restrictions_list,
    validate_port_params,
    validate_network_object,
    validate_file_path_security
)


class TestCoordinateValidation:
    """Test coordinate validation functions."""
    
    def test_validate_coordinates_valid(self):
        """Test valid coordinates."""
        result = validate_coordinates(129.17, 35.075)
        assert result == (129.17, 35.075)
        
        # Test edge cases
        assert validate_coordinates(-180, -90) == (-180.0, -90.0)
        assert validate_coordinates(180, 90) == (180.0, 90.0)
    
    def test_validate_coordinates_invalid_longitude(self):
        """Test invalid longitude values."""
        with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
            validate_coordinates(181, 35)
        
        with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
            validate_coordinates(-181, 35)
    
    def test_validate_coordinates_invalid_latitude(self):
        """Test invalid latitude values."""
        with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
            validate_coordinates(129, 91)
        
        with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
            validate_coordinates(129, -91)
    
    def test_validate_coordinates_non_numeric(self):
        """Test non-numeric coordinates."""
        with pytest.raises(TypeError, match="coordinates must be numeric"):
            validate_coordinates(None, 35)
        
        with pytest.raises(TypeError, match="coordinates must be numeric"):
            validate_coordinates(129, None)
            
        with pytest.raises(TypeError, match="coordinates must be numeric"):
            validate_coordinates([], {})

    def test_validate_coordinate_pair_valid(self):
        """Test valid coordinate pairs."""
        result = validate_coordinate_pair((129.17, 35.075))
        assert result == (129.17, 35.075)
        
        result = validate_coordinate_pair([129.17, 35.075])
        assert result == (129.17, 35.075)
    
    def test_validate_coordinate_pair_invalid_type(self):
        """Test invalid coordinate pair types."""
        with pytest.raises(TypeError, match="must be a tuple or list"):
            validate_coordinate_pair("129,35")
        
        with pytest.raises(TypeError, match="must be a tuple or list"):
            validate_coordinate_pair(129)
    
    def test_validate_coordinate_pair_wrong_length(self):
        """Test coordinate pairs with wrong length."""
        with pytest.raises(ValueError, match="must have exactly 2 elements"):
            validate_coordinate_pair((129,))
        
        with pytest.raises(ValueError, match="must have exactly 2 elements"):
            validate_coordinate_pair((129, 35, 100))


class TestGeoJSONValidation:
    """Test GeoJSON validation functions."""
    
    def test_validate_geojson_structure_feature_collection(self):
        """Test valid FeatureCollection structure."""
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        validate_geojson_structure(geojson_data)  # Should not raise
    
    def test_validate_geojson_structure_feature(self):
        """Test valid Feature structure."""
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [129.17, 35.075]
            },
            "properties": {}
        }
        validate_geojson_structure(geojson_data)  # Should not raise
    
    def test_validate_geojson_structure_invalid(self):
        """Test invalid GeoJSON structures."""
        # Missing type
        with pytest.raises(ValueError, match="must have a 'type' field"):
            validate_geojson_structure({})
        
        # Invalid type
        with pytest.raises(ValueError, match="Invalid GeoJSON type"):
            validate_geojson_structure({"type": "InvalidType"})
        
        # FeatureCollection without features
        with pytest.raises(ValueError, match="must have a 'features' field"):
            validate_geojson_structure({"type": "FeatureCollection"})
    
    def test_validate_geojson_file_valid(self):
        """Test valid GeoJSON file validation."""
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Point", 
                "coordinates": [129.17, 35.075]
            },
            "properties": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
            json.dump(geojson_data, f)
            temp_path = f.name
        
        try:
            result = validate_geojson_file(temp_path)
            assert result == geojson_data
        finally:
            Path(temp_path).unlink()
    
    def test_validate_geojson_file_not_found(self):
        """Test file not found error."""
        with pytest.raises(FileNotFoundError, match="GeoJSON file not found"):
            validate_geojson_file("nonexistent_file.geojson")
    
    def test_validate_geojson_file_invalid_json(self):
        """Test invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                validate_geojson_file(temp_path)
        finally:
            Path(temp_path).unlink()


class TestRestrictionValidation:
    """Test restriction zone validation."""
    
    def test_validate_restriction_zone_polygon(self):
        """Test valid polygon restriction zone."""
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            },
            "properties": {}
        }
        validate_restriction_zone(geojson_data)  # Should not raise
    
    def test_validate_restriction_zone_invalid_geometry(self):
        """Test invalid restriction zone geometry."""
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Point",  # Points are not valid for restriction zones
                "coordinates": [129.17, 35.075]
            },
            "properties": {}
        }
        
        with pytest.raises(ValueError, match="must be Polygon or MultiPolygon"):
            validate_restriction_zone(geojson_data)


class TestParameterValidation:
    """Test parameter validation functions."""
    
    def test_validate_network_resolution_valid(self):
        """Test valid network resolutions."""
        for resolution in ["5km", "10km", "20km", "50km", "100km"]:
            result = validate_network_resolution(resolution)
            assert result == resolution
    
    def test_validate_network_resolution_invalid(self):
        """Test invalid network resolution."""
        with pytest.raises(ValueError, match="Invalid network resolution"):
            validate_network_resolution("1km")
    
    def test_validate_speed_valid(self):
        """Test valid speed values."""
        assert validate_speed(10.5) == 10.5
        assert validate_speed("15") == 15.0
    
    def test_validate_speed_invalid(self):
        """Test invalid speed values."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_speed(-5)
        
        with pytest.raises(ValueError, match="must be positive"):
            validate_speed(0)
        
        with pytest.raises(TypeError, match="must be numeric"):
            validate_speed("invalid")
    
    def test_validate_units_valid(self):
        """Test valid units."""
        for unit in ["km", "m", "mi", "nm"]:
            result = validate_units(unit)
            assert result == unit
    
    def test_validate_units_invalid(self):
        """Test invalid units."""
        with pytest.raises(ValueError, match="Invalid units"):
            validate_units("yards")
    
    def test_validate_restrictions_list_valid(self):
        """Test valid restrictions list."""
        restrictions = ["suez", "panama", "custom_zone"]
        result = validate_restrictions_list(restrictions)
        assert result == restrictions
        
        # Test empty list
        result = validate_restrictions_list([])
        assert result == []
    
    def test_validate_restrictions_list_invalid(self):
        """Test invalid restrictions list."""
        with pytest.raises(TypeError, match="must be a list"):
            validate_restrictions_list("suez,panama")
        
        with pytest.raises(ValueError, match="must be a string"):
            validate_restrictions_list(["suez", 123])
        
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_restrictions_list(["suez", ""])
    
    def test_validate_port_params_valid(self):
        """Test valid port parameters."""
        params = {
            "country": "South Korea",
            "continent": "Asia",
            "harbor_size": "L"
        }
        result = validate_port_params(params)
        assert result["country"] == "South Korea"
        assert result["continent"] == "Asia"
        assert result["harbor_size"] == "L"
    
    def test_validate_port_params_invalid(self):
        """Test invalid port parameters."""
        with pytest.raises(TypeError, match="must be a dictionary"):
            validate_port_params("invalid")
        
        with pytest.raises(ValueError, match="must be a string"):
            validate_port_params({"country": 123})


class TestNetworkValidation:
    """Test network object validation."""
    
    def test_validate_network_object_valid(self):
        """Test valid network object."""
        mock_network = Mock()
        mock_network.nodes.return_value = [(1, 2), (3, 4)]
        mock_network.edges.return_value = [((1, 2), (3, 4))]
        
        result = validate_network_object(mock_network)
        assert result == mock_network
    
    def test_validate_network_object_none(self):
        """Test None network object."""
        result = validate_network_object(None)
        assert result is None
    
    def test_validate_network_object_invalid(self):
        """Test invalid network object."""
        invalid_network = "not a network"
        
        with pytest.raises(ValueError, match="must have 'nodes' method"):
            validate_network_object(invalid_network)
    
    def test_validate_network_object_method_fails(self):
        """Test network object with failing methods."""
        mock_network = Mock()
        mock_network.nodes.side_effect = Exception("Network error")
        mock_network.edges.return_value = []
        
        with pytest.raises(ValueError, match="nodes\\(\\) method failed"):
            validate_network_object(mock_network)


class TestFilePathSecurity:
    """Test file path security validation."""
    
    def test_validate_file_path_security_valid(self):
        """Test valid file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "test.geojson"
            result = validate_file_path_security(temp_path)
            assert isinstance(result, Path)
    
    def test_validate_file_path_security_path_traversal(self):
        """Test path traversal detection."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_file_path_security("../../../etc/passwd")
        
        with pytest.raises(ValueError, match="Path traversal detected"):
            validate_file_path_security("data/../../../secret.txt")
    
    def test_validate_file_path_security_system_directories(self):
        """Test system directory protection."""
        import platform
        
        # Test based on operating system
        if platform.system() == "Windows":
            # Test Windows system directories
            with pytest.raises(ValueError, match="Path traversal detected"):
                validate_file_path_security("C:\\Windows\\..\\..\\Windows\\System32\\config")
        else:
            # Test Unix-like system directories
            with pytest.raises(ValueError, match="Access to system directories not allowed"):
                validate_file_path_security("/etc/passwd")


class TestValidationIntegration:
    """Test validation integration with main APIs."""
    
    def test_api_validation_integration(self):
        """Test that validation is properly integrated into APIs."""
        # This would test that the main API functions properly call validation
        from seavoyage.api import calculate_sea_route_simple
        
        # Test invalid coordinates are caught
        with pytest.raises((ValueError, TypeError)):
            calculate_sea_route_simple("invalid", (4.158, 51.921))
        
        # Test invalid units are caught  
        with pytest.raises(ValueError):
            calculate_sea_route_simple((129.17, 35.075), (4.158, 51.921), units="invalid")
    
    def test_restriction_validation_integration(self):
        """Test restriction validation integration."""
        from seavoyage.api import calculate_sea_route_simple
        
        # Test invalid restrictions list
        with pytest.raises((ValueError, TypeError)):
            calculate_sea_route_simple(
                (129.17, 35.075), 
                (4.158, 51.921),
                restrictions="invalid"  # Should be a list
            )


if __name__ == "__main__":
    pytest.main([__file__]) 
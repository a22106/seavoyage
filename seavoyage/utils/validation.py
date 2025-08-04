"""Validation utilities for input data."""
from pathlib import Path
from typing import Tuple, Union, Any, Dict, List
import json
from shapely.geometry import shape, Point, Polygon, MultiPolygon, LineString, MultiLineString
import logging

logger = logging.getLogger(__name__)


def validate_coordinates(
    lon: float, 
    lat: float, 
    coord_name: str = "coordinate"
) -> Tuple[float, float]:
    """
    Validate geographic coordinates.
    
    Parameters
    ----------
    lon : float
        Longitude value (-180 to 180)
    lat : float
        Latitude value (-90 to 90)
    coord_name : str, optional
        Name of the coordinate for error messages
        
    Returns
    -------
    Tuple[float, float]
        Validated (lon, lat) tuple
        
    Raises
    ------
    ValueError
        If coordinates are invalid
    TypeError
        If coordinates are not numeric
    """
    # Type validation
    try:
        lon = float(lon)
        lat = float(lat)
    except (TypeError, ValueError) as e:
        raise TypeError(
            f"Invalid {coord_name}: coordinates must be numeric. "
            f"Got lon={type(lon).__name__}, lat={type(lat).__name__}"
        ) from e
    
    # Range validation
    if not -180 <= lon <= 180:
        raise ValueError(
            f"Invalid {coord_name}: longitude must be between -180 and 180. "
            f"Got {lon}"
        )
    
    if not -90 <= lat <= 90:
        raise ValueError(
            f"Invalid {coord_name}: latitude must be between -90 and 90. "
            f"Got {lat}"
        )
    
    return lon, lat


def validate_coordinate_pair(
    coord: Union[Tuple[float, float], List[float]], 
    coord_name: str = "coordinate"
) -> Tuple[float, float]:
    """
    Validate a coordinate pair (lon, lat).
    
    Parameters
    ----------
    coord : tuple or list
        Coordinate pair as (lon, lat)
    coord_name : str, optional
        Name of the coordinate for error messages
        
    Returns
    -------
    Tuple[float, float]
        Validated (lon, lat) tuple
        
    Raises
    ------
    ValueError
        If coordinate format or values are invalid
    TypeError
        If coordinate is not a tuple or list
    """
    if not isinstance(coord, (tuple, list)):
        raise TypeError(
            f"Invalid {coord_name}: must be a tuple or list. "
            f"Got {type(coord).__name__}"
        )
    
    if len(coord) != 2:
        raise ValueError(
            f"Invalid {coord_name}: must have exactly 2 elements (lon, lat). "
            f"Got {len(coord)} elements"
        )
    
    return validate_coordinates(coord[0], coord[1], coord_name)


def validate_geojson_structure(data: Dict[str, Any]) -> None:
    """
    Validate basic GeoJSON structure.
    
    Parameters
    ----------
    data : dict
        GeoJSON data to validate
        
    Raises
    ------
    ValueError
        If GeoJSON structure is invalid
    """
    if not isinstance(data, dict):
        raise ValueError("GeoJSON must be a dictionary")
    
    if "type" not in data:
        raise ValueError("GeoJSON must have a 'type' field")
    
    geojson_type = data["type"]
    
    if geojson_type == "FeatureCollection":
        if "features" not in data:
            raise ValueError("FeatureCollection must have a 'features' field")
        if not isinstance(data["features"], list):
            raise ValueError("FeatureCollection 'features' must be a list")
            
    elif geojson_type == "Feature":
        if "geometry" not in data:
            raise ValueError("Feature must have a 'geometry' field")
        if "properties" not in data:
            raise ValueError("Feature must have a 'properties' field")
            
    elif geojson_type in ["Point", "LineString", "Polygon", "MultiPoint", 
                          "MultiLineString", "MultiPolygon", "GeometryCollection"]:
        if "coordinates" not in data and geojson_type != "GeometryCollection":
            raise ValueError(f"{geojson_type} must have a 'coordinates' field")
        if geojson_type == "GeometryCollection" and "geometries" not in data:
            raise ValueError("GeometryCollection must have a 'geometries' field")
    else:
        raise ValueError(f"Invalid GeoJSON type: {geojson_type}")


def validate_geojson_geometry(data: Dict[str, Any]) -> bool:
    """
    Validate GeoJSON geometry using Shapely.
    
    Parameters
    ----------
    data : dict
        GeoJSON geometry or feature to validate
        
    Returns
    -------
    bool
        True if geometry is valid
        
    Raises
    ------
    ValueError
        If geometry is invalid
    """
    try:
        # Extract geometry if it's a Feature
        if data.get("type") == "Feature":
            geometry_data = data.get("geometry")
            if not geometry_data:
                raise ValueError("Feature has no geometry")
        else:
            geometry_data = data
            
        # Create Shapely geometry
        geom = shape(geometry_data)
        
        # Check if geometry is valid
        if not geom.is_valid:
            raise ValueError(f"Invalid geometry: {geom.wkt[:100]}...")
            
        # Additional checks for specific geometry types
        if isinstance(geom, (Polygon, MultiPolygon)):
            if geom.is_empty:
                raise ValueError("Polygon geometry is empty")
                
        return True
        
    except Exception as e:
        raise ValueError(f"Invalid GeoJSON geometry: {str(e)}") from e


def validate_geojson_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Validate and load a GeoJSON file.
    
    Parameters
    ----------
    file_path : str or Path
        Path to the GeoJSON file
        
    Returns
    -------
    dict
        Validated GeoJSON data
        
    Raises
    ------
    FileNotFoundError
        If file does not exist
    ValueError
        If file is not valid GeoJSON
    PermissionError
        If file cannot be read
    """
    # Convert to Path object
    path = Path(file_path)
    
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {path}")
    
    # Check if it's a file
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    # Check file extension
    if path.suffix.lower() not in ['.geojson', '.json']:
        logger.warning(f"File does not have .geojson extension: {path}")
    
    # Try to read and parse the file
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except PermissionError:
        raise PermissionError(f"Cannot read file: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {path}: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error reading file {path}: {str(e)}") from e
    
    # Validate GeoJSON structure
    validate_geojson_structure(data)
    
    # Validate geometries if it's a Feature or FeatureCollection
    if data["type"] == "FeatureCollection":
        for i, feature in enumerate(data["features"]):
            try:
                validate_geojson_geometry(feature)
            except ValueError as e:
                raise ValueError(f"Invalid geometry in feature {i}: {str(e)}") from e
    elif data["type"] == "Feature":
        validate_geojson_geometry(data)
    elif data["type"] in ["Point", "LineString", "Polygon", "MultiPoint", 
                          "MultiLineString", "MultiPolygon"]:
        validate_geojson_geometry(data)
    
    return data


def validate_restriction_zone(geojson_data: Dict[str, Any]) -> None:
    """
    Validate a restriction zone GeoJSON.
    
    Parameters
    ----------
    geojson_data : dict
        GeoJSON data for the restriction zone
        
    Raises
    ------
    ValueError
        If the restriction zone is invalid
    """
    # Basic GeoJSON validation
    validate_geojson_structure(geojson_data)
    
    # Check if it's a suitable type for restriction zones
    if geojson_data["type"] == "FeatureCollection":
        if len(geojson_data["features"]) == 0:
            raise ValueError("Restriction zone FeatureCollection is empty")
            
        # Validate each feature
        for i, feature in enumerate(geojson_data["features"]):
            geom_type = feature.get("geometry", {}).get("type")
            if geom_type not in ["Polygon", "MultiPolygon"]:
                raise ValueError(
                    f"Restriction zone feature {i} must be Polygon or MultiPolygon, "
                    f"got {geom_type}"
                )
            validate_geojson_geometry(feature)
            
    elif geojson_data["type"] == "Feature":
        geom_type = geojson_data.get("geometry", {}).get("type")
        if geom_type not in ["Polygon", "MultiPolygon"]:
            raise ValueError(
                f"Restriction zone must be Polygon or MultiPolygon, got {geom_type}"
            )
        validate_geojson_geometry(geojson_data)
        
    elif geojson_data["type"] in ["Polygon", "MultiPolygon"]:
        validate_geojson_geometry(geojson_data)
        
    else:
        raise ValueError(
            f"Restriction zone must be Polygon, MultiPolygon, Feature, "
            f"or FeatureCollection. Got {geojson_data['type']}"
        )


def validate_network_resolution(resolution: str) -> str:
    """
    Validate network resolution string.
    
    Parameters
    ----------
    resolution : str
        Network resolution (e.g., "5km", "10km", etc.)
        
    Returns
    -------
    str
        Validated resolution string
        
    Raises
    ------
    ValueError
        If resolution is invalid
    """
    valid_resolutions = ["5km", "10km", "20km", "50km", "100km"]
    
    if resolution not in valid_resolutions:
        raise ValueError(
            f"Invalid network resolution: {resolution}. "
            f"Must be one of: {', '.join(valid_resolutions)}"
        )
    
    return resolution


def validate_speed(speed: float, param_name: str = "speed") -> float:
    """
    Validate speed value.
    
    Parameters
    ----------
    speed : float
        Speed value to validate
    param_name : str, optional
        Parameter name for error messages
        
    Returns
    -------
    float
        Validated speed value
        
    Raises
    ------
    ValueError
        If speed is invalid
    TypeError
        If speed is not numeric
    """
    try:
        speed = float(speed)
    except (TypeError, ValueError) as e:
        raise TypeError(f"{param_name} must be numeric. Got {type(speed).__name__}") from e
    
    if speed <= 0:
        raise ValueError(f"{param_name} must be positive. Got {speed}")
    
    if speed > 100:  # Reasonable upper limit for ship speed in knots
        logger.warning(f"Unusually high {param_name}: {speed} knots")
    
    return speed


def validate_units(units: str) -> str:
    """
    Validate distance units.
    
    Parameters
    ----------
    units : str
        Units string ("km", "m", "mi", "nm")
        
    Returns
    -------
    str
        Validated units string
        
    Raises
    ------
    ValueError
        If units are invalid
    """
    valid_units = ["km", "m", "mi", "nm"]
    
    if units not in valid_units:
        raise ValueError(
            f"Invalid units: {units}. "
            f"Must be one of: {', '.join(valid_units)}"
        )
    
    return units
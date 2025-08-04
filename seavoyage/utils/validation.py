"""Validation utilities for input data."""

import json
import logging
from pathlib import Path
from typing import Any

from shapely.geometry import (
    MultiPolygon,
    Polygon,
    shape,
)

logger = logging.getLogger(__name__)


def validate_coordinates(
    lon: float, lat: float, coord_name: str = "coordinate"
) -> tuple[float, float]:
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
            f"Invalid {coord_name}: longitude must be between -180 and 180. Got {lon}"
        )

    if not -90 <= lat <= 90:
        raise ValueError(
            f"Invalid {coord_name}: latitude must be between -90 and 90. Got {lat}"
        )

    return lon, lat


def validate_coordinate_pair(
    coord: tuple[float, float] | list[float], coord_name: str = "coordinate"
) -> tuple[float, float]:
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
            f"Invalid {coord_name}: must be a tuple or list. Got {type(coord).__name__}"
        )

    if len(coord) != 2:
        raise ValueError(
            f"Invalid {coord_name}: must have exactly 2 elements (lon, lat). "
            f"Got {len(coord)} elements"
        )

    return validate_coordinates(coord[0], coord[1], coord_name)


def validate_geojson_structure(data: dict[str, Any]) -> None:
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

    elif geojson_type in [
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
        "GeometryCollection",
    ]:
        if "coordinates" not in data and geojson_type != "GeometryCollection":
            raise ValueError(f"{geojson_type} must have a 'coordinates' field")
        if geojson_type == "GeometryCollection" and "geometries" not in data:
            raise ValueError("GeometryCollection must have a 'geometries' field")
    else:
        raise ValueError(f"Invalid GeoJSON type: {geojson_type}")


def validate_geojson_geometry(data: dict[str, Any]) -> bool:
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


def validate_geojson_file(file_path: str | Path) -> dict[str, Any]:
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
    if path.suffix.lower() not in [".geojson", ".json"]:
        logger.warning(f"File does not have .geojson extension: {path}")

    # Try to read and parse the file
    try:
        with open(path, encoding="utf-8") as f:
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
    elif data["type"] in [
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
    ]:
        validate_geojson_geometry(data)

    return data


def validate_restriction_zone(geojson_data: dict[str, Any]) -> None:
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
        raise TypeError(
            f"{param_name} must be numeric. Got {type(speed).__name__}"
        ) from e

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
            f"Invalid units: {units}. Must be one of: {', '.join(valid_units)}"
        )

    return units


def validate_restrictions_list(restrictions: list[str]) -> list[str]:
    """
    Validate restriction zone names list.

    Parameters
    ----------
    restrictions : list of str
        List of restriction zone names

    Returns
    -------
    list of str
        Validated restrictions list

    Raises
    ------
    ValueError
        If restrictions list is invalid
    TypeError
        If restrictions is not a list
    """
    if not isinstance(restrictions, list):
        raise TypeError(
            f"Restrictions must be a list. Got {type(restrictions).__name__}"
        )

    if len(restrictions) == 0:
        logger.warning("Empty restrictions list provided")
        return restrictions

    # Validate each restriction name
    validated_restrictions = []
    for i, restriction in enumerate(restrictions):
        if not isinstance(restriction, str):
            raise ValueError(
                f"Restriction {i} must be a string. "
                f"Got {type(restriction).__name__}: {restriction}"
            )

        if not restriction.strip():
            raise ValueError(f"Restriction {i} cannot be empty or whitespace-only")

        validated_restrictions.append(restriction.strip())

    return validated_restrictions


def validate_port_params(port_params: dict[str, Any]) -> dict[str, Any]:
    """
    Validate port parameters dictionary.

    Parameters
    ----------
    port_params : dict
        Port parameters to validate

    Returns
    -------
    dict
        Validated port parameters

    Raises
    ------
    ValueError
        If port parameters are invalid
    TypeError
        If port_params is not a dictionary
    """
    if not isinstance(port_params, dict):
        raise TypeError(
            f"Port parameters must be a dictionary. Got {type(port_params).__name__}"
        )

    validated_params = {}

    # Validate common port parameters
    if "country" in port_params:
        country = port_params["country"]
        if not isinstance(country, str):
            raise ValueError(
                f"Port country must be a string. Got {type(country).__name__}"
            )
        validated_params["country"] = country.strip()

    if "continent" in port_params:
        continent = port_params["continent"]
        if not isinstance(continent, str):
            raise ValueError(
                f"Port continent must be a string. Got {type(continent).__name__}"
            )
        validated_params["continent"] = continent.strip()

    # Copy other parameters as-is but validate they're not empty strings
    for key, value in port_params.items():
        if key not in ["country", "continent"]:
            if isinstance(value, str) and not value.strip():
                logger.warning(f"Port parameter '{key}' is empty")
            validated_params[key] = value

    return validated_params


def validate_network_object(network_obj: Any, param_name: str = "network") -> Any:
    """
    Validate network object (MNetwork or Marnet).

    Parameters
    ----------
    network_obj : Any
        Network object to validate
    param_name : str, optional
        Parameter name for error messages

    Returns
    -------
    Any
        Validated network object

    Raises
    ------
    ValueError
        If network object is invalid
    """
    if network_obj is None:
        return network_obj

    # Check if it has required network methods/attributes
    required_methods = ["nodes", "edges"]
    for method in required_methods:
        if not hasattr(network_obj, method):
            raise ValueError(
                f"Invalid {param_name}: must have '{method}' method/attribute. "
                f"Got {type(network_obj).__name__}"
            )

    # Try to call nodes() to ensure it's functional
    try:
        nodes = network_obj.nodes()
        if hasattr(nodes, "__len__"):
            if len(nodes) == 0:
                logger.warning(f"{param_name} has no nodes")
    except Exception as e:
        raise ValueError(
            f"Invalid {param_name}: nodes() method failed. {str(e)}"
        ) from e

    return network_obj


def validate_file_path_security(file_path: str | Path) -> Path:
    """
    Validate file path for security concerns.

    Parameters
    ----------
    file_path : str or Path
        File path to validate

    Returns
    -------
    Path
        Validated and resolved Path object

    Raises
    ------
    ValueError
        If path has security issues
    """
    path = Path(file_path)

    # Check for path traversal attempts
    if ".." in path.parts:
        raise ValueError(f"Path traversal detected in: {path}")

    # Resolve to absolute path to check final destination
    try:
        resolved_path = path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Cannot resolve path {path}: {e}") from e

    # Check if path goes outside expected directories
    # This is a basic check - you might want to customize based on your needs
    if str(resolved_path).startswith("/etc/") or str(resolved_path).startswith("/sys/"):
        raise ValueError(f"Access to system directories not allowed: {resolved_path}")

    return resolved_path

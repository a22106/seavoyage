"""
Improved API for seavoyage with cleaner interfaces
"""
from typing import Dict, List, Tuple, Optional, Union, Any
from seavoyage.classes.m_network import MNetwork
from seavoyage.models import (
    RouteConfig, NetworkConfig, RouteCoordinates, 
    RouteResult, RouteProperties, RouteGeometry
)
from seavoyage.base import seavoyage as _original_seavoyage
from seavoyage.utils.marine_network import (
    get_m_network_5km, get_m_network_10km, get_m_network_20km,
    get_m_network_50km, get_m_network_100km
)
from seavoyage.callbacks import (
    ProgressCallback, ProgressTracker, ProgressStage,
    SimpleProgressCallback, FunctionProgressCallback
)
from seavoyage.retry import (
    RetryConfig, RetryHandler, ErrorRecoveryHandler,
    RetryStrategy, ErrorRecoveryResult
)
from seavoyage.log import logger
from seavoyage.utils.validation import (
    validate_coordinate_pair, validate_units, 
    validate_speed, validate_network_resolution
)


def calculate_sea_route(
    coordinates: RouteCoordinates,
    route_config: Optional[RouteConfig] = None,
    network_config: Optional[NetworkConfig] = None
) -> RouteResult:
    """Calculate optimal sea route between two points with improved API.
    
    This function provides a clean, type-safe interface for calculating maritime
    routes with full control over route and network configuration.
    
    Parameters
    ----------
    coordinates : RouteCoordinates
        Start and end coordinates for the route. Coordinates should be
        provided as (longitude, latitude) tuples.
    route_config : RouteConfig, optional
        Configuration for route calculation including units, speed, restrictions,
        and other route-specific parameters. If None, defaults are used.
    network_config : NetworkConfig, optional
        Configuration for maritime network including resolution and custom
        network options. If None, default 50km network is used.
        
    Returns
    -------
    RouteResult
        Calculated route containing:
        - geometry: LineString coordinates of the route
        - properties: Distance, duration, and other route metadata
        
    Raises
    ------
    RouteError
        When route cannot be calculated between the given points.
    StartInRestrictionError
        When start point is located within a restriction zone.
    DestinationInRestrictionError
        When end point is located within a restriction zone.
    IsolatedOriginError
        When start point is isolated by surrounding restrictions.
        
    Examples
    --------
    >>> coords = RouteCoordinates(
    ...     start=(129.17, 35.075),  # Busan
    ...     end=(4.158, 51.921)      # Rotterdam
    ... )
    >>> config = RouteConfig(units="km", speed_knot=12)
    >>> route = calculate_sea_route(coords, config)
    >>> print(f"Distance: {route.properties.length:.1f} km")
    
    Notes
    -----
    The function uses pre-computed maritime networks at various resolutions
    (5km to 100km) for efficient pathfinding. Custom restriction zones can
    be applied to avoid specific areas.
    
    See Also
    --------
    calculate_sea_route_simple : Simplified interface for basic use cases
    get_quick_route : Get basic route information quickly
    """
    # Use default configs if not provided
    if route_config is None:
        route_config = RouteConfig()
    if network_config is None:
        network_config = NetworkConfig()
    
    # Validate inputs
    validate_coordinate_pair(coordinates.start, "start coordinate")
    validate_coordinate_pair(coordinates.end, "end coordinate")
    
    if route_config.units:
        route_config.units = validate_units(route_config.units)
    if route_config.speed_knot:
        route_config.speed_knot = validate_speed(route_config.speed_knot, "speed_knot")
        
    # Prepare maritime network
    maritime_network = _prepare_maritime_network(network_config)
    
    # Prepare parameters for original function
    params = {
        "M": maritime_network,
        "units": route_config.units,
        "speed_knot": route_config.speed_knot,
        "append_orig_dest": route_config.append_origin_destination,
        "include_ports": route_config.include_ports,
        "return_passages": route_config.return_passages
    }
    
    if route_config.restrictions is not None:
        params["restrictions"] = route_config.restrictions
    if route_config.port_params is not None:
        params["port_params"] = route_config.port_params
    if network_config.port_network is not None:
        params["P"] = network_config.port_network
        
    # Calculate route
    result_dict = _original_seavoyage(
        coordinates.start,
        coordinates.end,
        **params
    )
    
    # Convert to RouteResult
    return RouteResult.from_dict(result_dict)


def calculate_sea_route_simple(
    start: Tuple[float, float],
    end: Tuple[float, float],
    restrictions: Optional[List[str]] = None,
    network_resolution: Optional[str] = None,
    units: str = "nm"
) -> RouteResult:
    """Simplified API for calculating sea routes.
    
    This function provides a streamlined interface for common route calculation
    use cases without needing to create configuration objects.
    
    Parameters
    ----------
    start : tuple[float, float]
        Starting coordinates as (longitude, latitude).
    end : tuple[float, float]
        Destination coordinates as (longitude, latitude).
    restrictions : list[str], optional
        List of restriction zone names to apply. Common values include
        "suez", "panama", "northwest" for built-in passages, or custom
        restriction names registered via register_custom_restriction().
    network_resolution : str, optional
        Network resolution to use. Valid values are "5km", "10km", "20km",
        "50km", "100km". Higher resolution provides more accurate routes
        but slower computation. Default is "50km".
    units : str, default="nm"
        Distance units for the result. Common values:
        - "nm": nautical miles
        - "km": kilometers
        - "m": meters
        - "mi": miles
        
    Returns
    -------
    RouteResult
        Calculated route with distance in specified units.
        
    Examples
    --------
    >>> route = calculate_sea_route_simple(
    ...     start=(129.17, 35.075),  # Busan
    ...     end=(4.158, 51.921),     # Rotterdam
    ...     restrictions=["suez"],
    ...     network_resolution="10km",
    ...     units="km"
    ... )
    >>> print(f"Distance: {route.properties.length:.1f} km")
    
    See Also
    --------
    calculate_sea_route : Full API with configuration objects
    get_quick_route : Get basic route information only
    """
    # Validate inputs
    start = validate_coordinate_pair(start, "start coordinate")
    end = validate_coordinate_pair(end, "end coordinate")
    units = validate_units(units)
    
    if network_resolution is not None:
        network_resolution = validate_network_resolution(network_resolution)
    
    coords = RouteCoordinates(start=start, end=end)
    route_config = RouteConfig(units=units, restrictions=restrictions)
    network_config = NetworkConfig(resolution=network_resolution)
    
    return calculate_sea_route(coords, route_config, network_config)


def get_quick_route(
    start: Tuple[float, float],
    end: Tuple[float, float]
) -> Dict[str, Union[float, str]]:
    """Get quick route information with minimal configuration.
    
    This is the simplest way to get basic routing information between two
    points without any configuration. Useful for quick distance/time estimates.
    
    Parameters
    ----------
    start : tuple[float, float]
        Starting coordinates as (longitude, latitude).
    end : tuple[float, float]
        Destination coordinates as (longitude, latitude).
        
    Returns
    -------
    dict
        Dictionary containing:
        - distance_nm : float
            Distance in nautical miles
        - distance_km : float
            Distance in kilometers  
        - duration_hours : float
            Estimated duration at 10 knots
        - waypoints_count : int
            Number of waypoints in the calculated route
        
    Examples
    --------
    >>> info = get_quick_route(
    ...     (129.17, 35.075),  # Busan
    ...     (4.158, 51.921)    # Rotterdam
    ... )
    >>> print(f"Distance: {info['distance_nm']:.1f} nm")
    >>> print(f"Duration: {info['duration_hours']:.1f} hours")
    
    Notes
    -----
    This function uses the default 50km network resolution and assumes
    a vessel speed of 10 knots for duration calculation.
    
    See Also
    --------
    calculate_sea_route_simple : Calculate full route with simple parameters
    calculate_sea_route : Full API with all configuration options
    """
    # Validate inputs
    start = validate_coordinate_pair(start, "start coordinate")
    end = validate_coordinate_pair(end, "end coordinate")
    
    route = calculate_sea_route_simple(start, end, units="nm")
    
    # Calculate km distance as well
    route_km = calculate_sea_route_simple(start, end, units="km")
    
    return {
        "distance_nm": route.properties.length,
        "distance_km": route_km.properties.length,
        "duration_hours": route.properties.duration_hours,
        "waypoints_count": len(route.geometry.coordinates)
    }


def _prepare_maritime_network(config: NetworkConfig) -> Optional[MNetwork]:
    """Prepare maritime network based on configuration.
    
    Parameters
    ----------
    config : NetworkConfig
        Network configuration specifying resolution or custom network.
        
    Returns
    -------
    MNetwork or None
        Maritime network instance or None to use default.
    """
    # If custom network provided, use it
    if config.maritime_network is not None:
        return config.maritime_network
        
    # If resolution specified, load appropriate network
    if config.resolution is not None:
        resolution_map = {
            "5km": get_m_network_5km,
            "10km": get_m_network_10km,
            "20km": get_m_network_20km,
            "50km": get_m_network_50km,
            "100km": get_m_network_100km
        }
        
        if config.resolution in resolution_map:
            logger.debug(f"Loading {config.resolution} resolution network")
            return resolution_map[config.resolution]()
        else:
            raise ValueError(f"Invalid resolution: {config.resolution}")
            
    # Default: let the original function handle it
    return None
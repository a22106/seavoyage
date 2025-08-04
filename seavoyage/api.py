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
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.marine_network import (
    get_m_network_5km, get_m_network_10km, get_m_network_20km,
    get_m_network_50km, get_m_network_100km
)
from seavoyage.log import logger


def calculate_sea_route(
    coordinates: RouteCoordinates,
    route_config: Optional[RouteConfig] = None,
    network_config: Optional[NetworkConfig] = None
) -> RouteResult:
    """
    Calculate optimal sea route between two points with improved API
    
    Args:
        coordinates: Start and end coordinates for the route
        route_config: Configuration for route calculation (units, speed, restrictions, etc.)
        network_config: Configuration for maritime network (resolution, custom network, etc.)
        
    Returns:
        RouteResult: Calculated route with geometry and properties
        
    Raises:
        RouteError: When route cannot be calculated
        StartInRestrictionError: When start point is in a restriction zone
        DestinationInRestrictionError: When end point is in a restriction zone
        IsolatedOriginError: When start point is isolated by restrictions
        
    Example:
        >>> coords = RouteCoordinates(
        ...     start=(129.17, 35.075),
        ...     end=(-4.158, 44.644)
        ... )
        >>> config = RouteConfig(units="km", speed_knot=12)
        >>> route = calculate_sea_route(coords, config)
        >>> print(f"Distance: {route.properties.length} km")
    """
    # Use default configs if not provided
    if route_config is None:
        route_config = RouteConfig()
    if network_config is None:
        network_config = NetworkConfig()
        
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
    """
    Simplified API for calculating sea routes
    
    Args:
        start: Starting coordinates (longitude, latitude)
        end: Destination coordinates (longitude, latitude) 
        restrictions: List of restriction zones to apply
        network_resolution: Network resolution ("5km", "10km", "20km", "50km", "100km")
        units: Distance units ("nm", "km", "m", "mi", etc.)
        
    Returns:
        RouteResult: Calculated route
        
    Example:
        >>> route = calculate_sea_route_simple(
        ...     start=(129.17, 35.075),
        ...     end=(-4.158, 44.644),
        ...     restrictions=["suez", "panama"],
        ...     network_resolution="10km",
        ...     units="km"
        ... )
        >>> print(f"Distance: {route.properties.length} km")
    """
    coords = RouteCoordinates(start=start, end=end)
    route_config = RouteConfig(units=units, restrictions=restrictions)
    network_config = NetworkConfig(resolution=network_resolution)
    
    return calculate_sea_route(coords, route_config, network_config)


def get_quick_route(
    start: Tuple[float, float],
    end: Tuple[float, float]
) -> Dict[str, Union[float, str]]:
    """
    Get quick route information with minimal configuration
    
    Args:
        start: Starting coordinates (longitude, latitude)
        end: Destination coordinates (longitude, latitude)
        
    Returns:
        Dictionary with basic route information:
        - distance_nm: Distance in nautical miles
        - distance_km: Distance in kilometers  
        - duration_hours: Estimated duration at 10 knots
        - waypoints_count: Number of waypoints in route
        
    Example:
        >>> info = get_quick_route((129.17, 35.075), (-4.158, 44.644))
        >>> print(f"Distance: {info['distance_nm']:.1f} nm")
    """
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
    """Prepare maritime network based on configuration"""
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
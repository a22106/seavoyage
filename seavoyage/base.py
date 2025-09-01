from typing import Dict, List, Tuple, Optional, Union, Any
from haversine import Unit
from searoute import searoute, setup_M
from searoute.classes.passages import Passage
from searoute.classes.marnet import Marnet
from searoute.classes.ports import Ports
from seavoyage.log import logger
from seavoyage.exceptions import RouteError, StartInRestrictionError, DestinationInRestrictionError, IsolatedOriginError

from seavoyage.modules.restriction import CustomRestriction, get_custom_restriction, list_custom_restrictions
from seavoyage.classes.m_network import MNetwork
from seavoyage.utils.coordinates import decdeg_to_degmin
from seavoyage.utils.route_utils import calculate_route_length
from seavoyage.utils.validation import (
    validate_coordinate_pair, validate_units, validate_speed,
    validate_restrictions_list, validate_network_object
)

units_map: Dict[str, Unit] = {
    "km": Unit.KILOMETERS,
    "m": Unit.METERS,
    "mi": Unit.MILES,
    "nm": Unit.NAUTICAL_MILES,
    "ft": Unit.FEET,
    "in": Unit.INCHES,
    "rad": Unit.RADIANS,
    "deg": Unit.DEGREES,
}

_DEFAULT_MNETWORK: Optional[MNetwork] = None


def _get_default_network() -> MNetwork:
    """Get or create the default maritime network."""
    global _DEFAULT_MNETWORK
    if _DEFAULT_MNETWORK is None:
        _DEFAULT_MNETWORK = MNetwork.from_marnet(setup_M())
    return _DEFAULT_MNETWORK


def _original_seavoyage(start: Tuple[float, float], end: Tuple[float, float], **kwargs) -> Dict[str, Any]:
    """
    Calculate ship route (internal use)

    Args:
        start: Starting coordinates (longitude, latitude)
        end: Destination coordinates (longitude, latitude)
        **kwargs: Additional arguments

    Returns:
        dict: Route information as GeoJSON Feature
    """
    if not kwargs.get("M"):
        kwargs["M"] = setup_M()
    route = searoute(start, end, **kwargs)
    
    # Calculate length property by units
    units: str = kwargs.get("units", "nm")
    unit: Unit = units_map[units]
    
    # Calculate total distance
    total_distance: float = calculate_route_length(route, unit)
    
    route['properties']['length'] = total_distance
    
    # Add speed_knot if provided
    speed_knot = kwargs.get("speed_knot")
    if speed_knot is not None:
        route['properties']['speed_knot'] = speed_knot
    
    return route

def _classify_restrictions(restrictions: List[str]) -> Tuple[List[CustomRestriction], List[Passage], List[str]]:
    """
    Classify restriction zone name list into custom/default/unknown.
    
    Args:
        restrictions: List of restriction names
        
    Returns:
        Tuple of (custom_restrictions, default_passages, unknown_restrictions)
    """
    custom = []
    default = []
    unknown = []
    for r in restrictions:
        custom_restriction = get_custom_restriction(r)
        if custom_restriction:
            logger.debug(f"Found custom restriction zone '{r}'")
            custom.append(custom_restriction)
        elif hasattr(Passage, r):
            logger.debug(f"Found default restriction zone '{r}'")
            default.append(getattr(Passage, r))
        else:
            logger.warning(f"Unknown restriction zone: '{r}'")
            unknown.append(r)
    return custom, default, unknown


def _apply_restrictions_to_network(
    mnetwork: MNetwork, 
    custom_restrictions: List[CustomRestriction], 
    default_passages: List[Passage]
) -> None:
    """
    Apply restriction zones to network object.
    
    Args:
        mnetwork: Maritime network object
        custom_restrictions: List of custom restrictions
        default_passages: List of default passages
    """
    if not isinstance(mnetwork, MNetwork | Marnet):
        raise ValueError(f"mnetwork must be an instance of MNetwork, not {type(mnetwork)}: {mnetwork}")
    
    # Add new restriction zones without overwriting existing ones
    for passage in default_passages:
        if passage not in mnetwork.restrictions:
            mnetwork.restrictions.append(passage)
    
    # Add custom restriction zones
    for restriction in custom_restrictions:
        mnetwork.add_restriction(restriction)


def seavoyage(
    start: Tuple[float, float], 
    end: Tuple[float, float], 
    *,
    restrictions: Optional[List[str]] = None,
    M: Optional[Union[MNetwork, Marnet]] = None,
    units: str = "nm",
    speed_knot: float = 10,
    append_orig_dest: bool = False,
    include_ports: bool = False,
    port_params: Optional[Dict[str, Any]] = None,
    P: Optional[Ports] = None,
    return_passages: bool = False,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Calculate ship route (with custom restriction zone support)

    Args:
        start: Starting coordinates (longitude, latitude)
        end: Destination coordinates (longitude, latitude)
        restrictions: List of restriction zones
        M: Maritime network object
        units: Distance unit (default: "nm")
        speed_knot: Ship speed (default: 10 knots)
        append_orig_dest: Whether to append origin/destination to route (default: False)
        include_ports: Whether to include ports (default: False)
        port_params: Port-related settings
        P: Port network object
        return_passages: Whether to return passages crossed (default: False)

    Returns:
        dict: Route information (GeoJSON Feature)
        
    Raises:
        RouteError: When error occurs during route calculation
        StartInRestrictionError: When starting point is within a restriction zone
        DestinationInRestrictionError: When destination is within a restriction zone
        UnreachableDestinationError: When destination cannot be reached due to restriction zones
        IsolatedOriginError: When starting point is isolated by restriction zones
    """
    # Validate inputs
    start = validate_coordinate_pair(start, "start coordinate")
    end = validate_coordinate_pair(end, "end coordinate")
    units = validate_units(units)
    speed_knot = validate_speed(speed_knot, "speed_knot")
    
    if restrictions is not None:
        restrictions = validate_restrictions_list(restrictions)
    
    if M is not None:
        validate_network_object(M, "maritime network (M)")
    if P is not None:
        validate_network_object(P, "port network (P)")
    
    mnetwork: MNetwork = M or _get_default_network()
    mnetwork.reset_restrictions()  # Reset restriction zones
    custom_restrictions: List[CustomRestriction] = []
    default_passages: List[Passage] = []
    unknown_restrictions: List[str] = []
    
    if restrictions is None:
        processed_restrictions = [Passage.northwest]
    else:
        if not isinstance(restrictions, list):
            raise ValueError("restrictions must be a list")
        logger.debug(f"Requested restriction zones: {restrictions}")
        processed_restrictions = restrictions + [Passage.northwest]
    
    # Classify restriction zones (always performed)
    custom_restrictions, default_passages, unknown_restrictions = _classify_restrictions(processed_restrictions)
    

    if start == end:
        # Return zero-length route when start and end are identical
        return {
            "geometry": {
                "coordinates": [list(start)],
                "type": "LineString"
            },
            "properties": {
                "duration_hours": 0.0,
                "length": 0.0,
                "units": units
            },
            "type": "Feature"
        }


    # Apply restriction zones to network
    _apply_restrictions_to_network(mnetwork, custom_restrictions, default_passages)

    logger.debug(f"Registered restriction zones: {list_custom_restrictions()}")
    logger.debug(f"Applied default restriction zones: {mnetwork.restrictions}")
    logger.debug(f"Applied custom restriction zones: {list(mnetwork.custom_restrictions.keys())}")

    # Construct kwargs dictionary
    kwargs: Dict[str, Any] = {
        "M": mnetwork,
        "units": units,
        "speed_knot": speed_knot,
        "append_orig_dest": append_orig_dest,
        "restrictions": processed_restrictions,
        "include_ports": include_ports,
        "return_passages": return_passages
    }
    
    # Add optional parameters
    if port_params is not None:
        kwargs["port_params"] = port_params
    if P is not None:
        kwargs["P"] = P
    
    try:
        # Check isolated points: First check if starting point is isolated
        logger.debug(f"Starting route calculation from {start} to {end}")
        
        # Check if starting point is within restriction zone
        is_origin_restricted, origin_restriction = mnetwork.is_point_in_restriction(start)
        if is_origin_restricted:
            logger.error(f"Starting point {decdeg_to_degmin(start)} is within restriction zone '{origin_restriction}'")
            raise StartInRestrictionError(start, origin_restriction)
            
        # Check if destination is within restriction zone
        is_dest_restricted, dest_restriction = mnetwork.is_point_in_restriction(end)
        if is_dest_restricted:
            logger.error(f"Destination {decdeg_to_degmin(end)} is within restriction zone '{dest_restriction}'")
            raise DestinationInRestrictionError(end, dest_restriction)
        
        # Find the nearest network node to starting point
        origin_node = mnetwork.kdtree.query(start)
        
        # Check if line segment between starting point and nearest node crosses restriction zones
        if start != origin_node:  # If starting point differs from network node
            from shapely import LineString
            
            line_to_origin = LineString([start, origin_node])
            logger.debug(f"Nearest network node to starting point {start}: {origin_node}")
            
            # Check custom restriction zones
            for name, restriction in mnetwork.custom_restrictions.items():
                if restriction.polygon.intersects(line_to_origin):
                    logger.error(f"Path from starting point {start} to nearest node {origin_node} intersects with restriction zone '{name}'")
                    raise IsolatedOriginError(start, [name])
        
        # Check if origin node is isolated
        is_isolated: bool = True
        
        for neighbor in mnetwork.neighbors(origin_node):
            edge_data = mnetwork.get_edge_data(origin_node, neighbor)
            if mnetwork._filter_custom_restricted_edge(origin_node, neighbor, edge_data):
                is_isolated = False
                break
        
        if is_isolated:
            restriction_names = list(mnetwork.custom_restrictions.keys())
            if mnetwork.restrictions:
                restriction_names.extend([str(r) for r in mnetwork.restrictions])
            logger.error(f"Starting point {start} is isolated by restriction zones: {restriction_names}")
            raise IsolatedOriginError(start, restriction_names)
            
        return _original_seavoyage(start, end, **kwargs)
        
    except (RouteError, IsolatedOriginError) as e:
        # Handle route-related exceptions
        logger.error(f"Route error: {str(e)}")
        raise
    except Exception as e:
        # Pass through other exceptions as-is
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise

# Function for backward compatibility
def custom_seavoyage(
    start: Tuple[float, float], 
    end: Tuple[float, float], 
    custom_restrictions: Optional[List[str]] = None, 
    default_restrictions: Optional[List[Union[str, Passage]]] = None, 
    **kwargs
) -> Dict[str, Any]:
    """
    Calculate ship route considering custom restriction zones.
    
    Args:
        start: Starting coordinates (longitude, latitude)
        end: Destination coordinates (longitude, latitude)
        custom_restrictions: List of custom restriction zone names
        default_restrictions: List of default restriction zones (Passage class constants)
        **kwargs: Additional arguments to pass to seavoyage
    Returns:
        dict: Route information (GeoJSON Feature)
        
    Raises:
        RouteError: When error occurs during route calculation
        IsolatedOriginError: When starting point is isolated by restriction zones
    """
    restrictions: List[str] = []
    
    # Add default restriction zones
    if default_restrictions:
        restrictions.extend(default_restrictions)
    
    # Add custom restriction zones
    if custom_restrictions:
        restrictions.extend(custom_restrictions)
    
    # Extract new seavoyage parameters from kwargs
    seavoyage_params: Dict[str, Any] = {
        'M': kwargs.pop('M', None),
        'units': kwargs.pop('units', 'nm'),
        'speed_knot': kwargs.pop('speed_knot', 10),
        'append_orig_dest': kwargs.pop('append_orig_dest', False),
        'include_ports': kwargs.pop('include_ports', False),
        'port_params': kwargs.pop('port_params', None),
        'P': kwargs.pop('P', None),
        'return_passages': kwargs.pop('return_passages', False)
    }
    
    # Add restrictions (only if not empty list)
    if restrictions:
        seavoyage_params['restrictions'] = restrictions
    
    # Remove optional parameters with None values
    seavoyage_params = {k: v for k, v in seavoyage_params.items() if v is not None}
    
    return seavoyage(start, end, **seavoyage_params)

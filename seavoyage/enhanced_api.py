"""
Enhanced API with progress tracking and error recovery
"""
from typing import Dict, List, Tuple, Optional, Union, Any
from seavoyage.classes.m_network import MNetwork
from seavoyage.models import (
    RouteConfig, NetworkConfig, RouteCoordinates, 
    RouteResult, RouteProperties, RouteGeometry
)
from seavoyage.base import seavoyage as _original_seavoyage, _apply_restrictions_to_network, _classify_restrictions
from seavoyage.base import _get_default_network
from seavoyage.callbacks import (
    ProgressTracker, ProgressStage, ProgressInfo,
    SimpleProgressCallback, FunctionProgressCallback
)
from seavoyage.retry import (
    RetryConfig, ErrorRecoveryHandler, RetryStrategy
)
from seavoyage.exceptions import (
    RouteError, StartInRestrictionError, DestinationInRestrictionError,
    IsolatedOriginError, NetworkError
)
from seavoyage.utils.coordinates import decdeg_to_degmin
from seavoyage.log import logger
from haversine import Unit
from searoute.classes.passages import Passage
from searoute.classes.ports import Ports


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


def seavoyage_with_progress(
    start: Tuple[float, float], 
    end: Tuple[float, float], 
    *,
    restrictions: Optional[List[str]] = None,
    M: Optional[Union[MNetwork, Any]] = None,
    units: str = "nm",
    speed_knot: float = 10,
    append_orig_dest: bool = False,
    include_ports: bool = False,
    port_params: Optional[Dict[str, Any]] = None,
    P: Optional[Ports] = None,
    return_passages: bool = False,
    progress_callback: Optional[Any] = None,
    enable_retry: bool = True,
    retry_config: Optional[RetryConfig] = None,
) -> Dict[str, Any]:
    """
    Enhanced version of seavoyage with progress tracking and error recovery
    
    Parameters
    ----------
    start : tuple[float, float]
        Starting coordinates (longitude, latitude)
    end : tuple[float, float]
        Destination coordinates (longitude, latitude)
    restrictions : list[str], optional
        List of restriction zones
    M : MNetwork or Marnet, optional
        Maritime network object
    units : str, default="nm"
        Distance unit
    speed_knot : float, default=10
        Ship speed in knots
    append_orig_dest : bool, default=False
        Whether to append origin/destination to route
    include_ports : bool, default=False
        Whether to include ports
    port_params : dict, optional
        Port-related settings
    P : Ports, optional
        Port network object
    return_passages : bool, default=False
        Whether to return passages crossed
    progress_callback : callable, optional
        Progress callback function that receives ProgressInfo objects
    enable_retry : bool, default=True
        Whether to enable automatic retry on failure
    retry_config : RetryConfig, optional
        Configuration for retry behavior
        
    Returns
    -------
    dict
        Route information (GeoJSON Feature)
    """
    # Setup progress tracker
    tracker = ProgressTracker(progress_callback)
    
    # Setup error recovery if enabled
    if enable_retry:
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                retry_on_exceptions=[NetworkError, RouteError]
            )
        recovery_handler = ErrorRecoveryHandler(retry_config)
    
    try:
        # Initialize
        tracker.update(
            ProgressStage.INITIALIZATION,
            0,
            "Starting route calculation"
        )
        
        # Handle identical start and end
        if start == end:
            tracker.complete("Zero-length route")
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
        
        # Load network
        tracker.update(
            ProgressStage.NETWORK_LOADING,
            0,
            "Loading maritime network"
        )
        
        mnetwork: MNetwork = M or _get_default_network()
        mnetwork.reset_restrictions()
        
        tracker.update(
            ProgressStage.NETWORK_LOADING,
            100,
            "Maritime network loaded"
        )
        
        # Process restrictions
        tracker.update(
            ProgressStage.RESTRICTION_PROCESSING,
            0,
            "Processing restriction zones"
        )
        
        if restrictions is None:
            processed_restrictions = [Passage.northwest]
        else:
            if not isinstance(restrictions, list):
                raise ValueError("restrictions must be a list")
            processed_restrictions = restrictions + [Passage.northwest]
        
        # Classify restrictions
        custom_restrictions, default_passages, unknown_restrictions = _classify_restrictions(processed_restrictions)
        
        tracker.update(
            ProgressStage.RESTRICTION_PROCESSING,
            50,
            f"Classified {len(custom_restrictions)} custom and {len(default_passages)} default restrictions"
        )
        
        # Apply restrictions
        _apply_restrictions_to_network(mnetwork, custom_restrictions, default_passages)
        
        tracker.update(
            ProgressStage.RESTRICTION_PROCESSING,
            100,
            "Restriction zones applied"
        )
        
        # Validate points
        tracker.update(
            ProgressStage.PATHFINDING,
            0,
            "Validating start and end points"
        )
        
        # Check if starting point is within restriction zone
        is_origin_restricted, origin_restriction = mnetwork.is_point_in_restriction(start)
        if is_origin_restricted:
            error_msg = f"Starting point {decdeg_to_degmin(start)} is within restriction zone '{origin_restriction}'"
            tracker.error(error_msg)
            raise StartInRestrictionError(start, origin_restriction)
            
        # Check if destination is within restriction zone
        is_dest_restricted, dest_restriction = mnetwork.is_point_in_restriction(end)
        if is_dest_restricted:
            error_msg = f"Destination {decdeg_to_degmin(end)} is within restriction zone '{dest_restriction}'"
            tracker.error(error_msg)
            raise DestinationInRestrictionError(end, dest_restriction)
        
        tracker.update(
            ProgressStage.PATHFINDING,
            20,
            "Points validated, finding nearest network nodes"
        )
        
        # Find nearest network node to starting point
        origin_node = mnetwork.kdtree.query(start)
        
        # Check if path to network is blocked
        if start != origin_node:
            from shapely import LineString
            
            line_to_origin = LineString([start, origin_node])
            
            for name, restriction in mnetwork.custom_restrictions.items():
                if restriction.polygon.intersects(line_to_origin):
                    error_msg = f"Path from starting point to network is blocked by restriction zone '{name}'"
                    tracker.error(error_msg)
                    raise IsolatedOriginError(start, [name])
        
        tracker.update(
            ProgressStage.PATHFINDING,
            40,
            "Checking network connectivity"
        )
        
        # Check if origin node is isolated
        is_isolated = True
        for neighbor in mnetwork.neighbors(origin_node):
            edge_data = mnetwork.get_edge_data(origin_node, neighbor)
            if mnetwork._filter_custom_restricted_edge(origin_node, neighbor, edge_data):
                is_isolated = False
                break
        
        if is_isolated:
            restriction_names = list(mnetwork.custom_restrictions.keys())
            if mnetwork.restrictions:
                restriction_names.extend([str(r) for r in mnetwork.restrictions])
            error_msg = f"Starting point is isolated by restriction zones"
            tracker.error(error_msg)
            raise IsolatedOriginError(start, restriction_names)
        
        tracker.update(
            ProgressStage.PATHFINDING,
            60,
            "Calculating optimal route"
        )
        
        # Prepare kwargs
        kwargs = {
            "M": mnetwork,
            "units": units,
            "speed_knot": speed_knot,
            "append_orig_dest": append_orig_dest,
            "restrictions": processed_restrictions,
            "include_ports": include_ports,
            "return_passages": return_passages
        }
        
        if port_params is not None:
            kwargs["port_params"] = port_params
        if P is not None:
            kwargs["P"] = P
        
        def calculate_route():
            """Inner function for route calculation with progress updates"""
            # Update progress periodically during calculation
            # Note: The actual searoute calculation is atomic, so we simulate progress
            tracker.update(
                ProgressStage.PATHFINDING,
                80,
                "Running pathfinding algorithm"
            )
            
            result = _original_seavoyage(start, end, **kwargs)
            
            tracker.update(
                ProgressStage.ROUTE_OPTIMIZATION,
                50,
                "Optimizing route"
            )
            
            return result
        
        # Execute with retry if enabled
        if enable_retry:
            def on_retry(attempt: int, error: Exception):
                tracker.update(
                    ProgressStage.PATHFINDING,
                    60,
                    f"Retry attempt {attempt} after error: {str(error)}"
                )
            
            recovery_result = recovery_handler.recover(
                calculate_route,
                recovery_callbacks={'on_retry': on_retry}
            )
            
            if not recovery_result.success:
                raise recovery_result.error
                
            route = recovery_result.result
        else:
            route = calculate_route()
        
        # Finalize
        tracker.update(
            ProgressStage.FINALIZATION,
            50,
            "Finalizing route data"
        )
        
        # Add additional metadata
        route['properties']['calculation_method'] = 'enhanced'
        if enable_retry and hasattr(recovery_result, 'recovery_method'):
            route['properties']['recovery_method'] = recovery_result.recovery_method
        
        tracker.complete(
            f"Route calculated: {route['properties']['length']:.1f} {units}"
        )
        
        return route
        
    except Exception as e:
        tracker.error(f"Route calculation failed: {str(e)}", e)
        raise


def calculate_sea_route_with_recovery(
    coordinates: RouteCoordinates,
    route_config: Optional[RouteConfig] = None,
    network_config: Optional[NetworkConfig] = None
) -> RouteResult:
    """
    Calculate sea route with progress tracking and error recovery
    
    This is an enhanced version of calculate_sea_route that includes:
    - Progress tracking with callbacks
    - Automatic retry on failure
    - Error recovery mechanisms
    - Partial route calculation fallback
    
    Parameters
    ----------
    coordinates : RouteCoordinates
        Start and end coordinates for the route
    route_config : RouteConfig, optional
        Route configuration including progress callback and retry settings
    network_config : NetworkConfig, optional
        Network configuration
        
    Returns
    -------
    RouteResult
        Calculated route with metadata about recovery if applicable
        
    Examples
    --------
    >>> from seavoyage.callbacks import SimpleProgressCallback
    >>> coords = RouteCoordinates(
    ...     start=(129.17, 35.075),
    ...     end=(4.158, 51.921)
    ... )
    >>> config = RouteConfig(
    ...     progress_callback=SimpleProgressCallback(),
    ...     enable_retry=True,
    ...     max_retry_attempts=3
    ... )
    >>> route = calculate_sea_route_with_recovery(coords, config)
    """
    # Use defaults if not provided
    if route_config is None:
        route_config = RouteConfig()
    if network_config is None:
        network_config = NetworkConfig()
    
    # Prepare maritime network
    from seavoyage.api import _prepare_maritime_network
    maritime_network = _prepare_maritime_network(network_config)
    
    # Setup retry config
    retry_config = None
    if route_config.enable_retry:
        retry_config = RetryConfig(
            max_attempts=route_config.max_retry_attempts,
            initial_delay=route_config.retry_delay,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
    
    # Call enhanced seavoyage
    result_dict = seavoyage_with_progress(
        coordinates.start,
        coordinates.end,
        restrictions=route_config.restrictions,
        M=maritime_network,
        units=route_config.units,
        speed_knot=route_config.speed_knot,
        append_orig_dest=route_config.append_origin_destination,
        include_ports=route_config.include_ports,
        port_params=route_config.port_params,
        P=network_config.port_network,
        return_passages=route_config.return_passages,
        progress_callback=route_config.progress_callback,
        enable_retry=route_config.enable_retry,
        retry_config=retry_config
    )
    
    # Convert to RouteResult
    return RouteResult.from_dict(result_dict)
"""
Examples of using the improved seavoyage API
"""
import seavoyage as sv


def example_1_quick_route():
    """Example 1: Get quick route information"""
    print("Example 1: Quick Route Information")
    print("-" * 40)
    
    # Simple route from Busan to Rotterdam
    start = (129.17, 35.075)  # Busan, South Korea
    end = (4.158, 51.921)     # Rotterdam, Netherlands
    
    info = sv.get_quick_route(start, end)
    
    print(f"Distance: {info['distance_nm']:.1f} nm ({info['distance_km']:.1f} km)")
    print(f"Duration: {info['duration_hours']:.1f} hours")
    print(f"Waypoints: {info['waypoints_count']}")
    print()


def example_2_simple_api():
    """Example 2: Using the simplified API"""
    print("Example 2: Simplified API with Custom Settings")
    print("-" * 40)
    
    start = (129.17, 35.075)  # Busan
    end = (-73.949, 40.650)   # New York
    
    # Calculate route with custom restrictions and network resolution
    route = sv.calculate_sea_route_simple(
        start=start,
        end=end,
        restrictions=["suez", "panama"],
        network_resolution="20km",
        units="km"
    )
    
    print(f"Route type: {route.type}")
    print(f"Distance: {route.properties.length:.1f} km")
    print(f"Duration: {route.properties.duration_hours:.1f} hours")
    print(f"Number of waypoints: {len(route.geometry.coordinates)}")
    print()


def example_3_advanced_api():
    """Example 3: Using the advanced API with configuration objects"""
    print("Example 3: Advanced API with Configuration Objects")
    print("-" * 40)
    
    # Define coordinates
    coords = sv.RouteCoordinates(
        start=(103.822, 1.264),  # Singapore
        end=(23.708, 37.945)     # Athens
    )
    
    # Configure route calculation
    route_config = sv.RouteConfig(
        units="nm",
        speed_knot=15,
        restrictions=["suez"],
        append_origin_destination=True,
        return_passages=True
    )
    
    # Configure network
    network_config = sv.NetworkConfig(
        resolution="10km"
    )
    
    # Calculate route
    route = sv.calculate_sea_route(coords, route_config, network_config)
    
    print(f"Distance: {route.properties.length:.1f} nautical miles")
    print(f"Duration: {route.properties.duration_hours:.1f} hours")
    
    if route.properties.passages_crossed:
        print(f"Passages crossed: {', '.join(route.properties.passages_crossed)}")
    print()


def example_4_custom_restrictions():
    """Example 4: Using custom restriction zones"""
    print("Example 4: Custom Restriction Zones")
    print("-" * 40)
    
    # Register a custom restriction zone (example only - file must exist)
    # sv.register_custom_restriction('my_zone', '/path/to/my_zone.geojson')
    
    coords = sv.RouteCoordinates(
        start=(129.17, 35.075),
        end=(4.158, 51.921)
    )
    
    route_config = sv.RouteConfig(
        units="km",
        restrictions=["suez", "panama"],  # Add custom zones here
        speed_knot=12
    )
    
    route = sv.calculate_sea_route(coords, route_config)
    
    print(f"Route calculated with restrictions")
    print(f"Distance: {route.properties.length:.1f} km")
    print(f"Duration: {route.properties.duration_hours:.1f} hours")
    print()


def example_5_convert_formats():
    """Example 5: Converting between dictionary and dataclass formats"""
    print("Example 5: Format Conversion")
    print("-" * 40)
    
    # Get route as dictionary (original format)
    start = (129.17, 35.075)
    end = (4.158, 51.921)
    
    dict_route = sv.seavoyage(start, end)
    print("Dictionary format keys:", list(dict_route.keys()))
    
    # Convert to RouteResult dataclass
    route_result = sv.RouteResult.from_dict(dict_route)
    print(f"RouteResult distance: {route_result.properties.length}")
    
    # Convert back to dictionary
    dict_again = route_result.to_dict()
    print("Converted back to dict:", dict_again == dict_route)
    print()


def example_6_network_resolutions():
    """Example 6: Comparing different network resolutions"""
    print("Example 6: Network Resolution Comparison")
    print("-" * 40)
    
    start = (129.17, 35.075)
    end = (4.158, 51.921)
    
    resolutions = ["10km", "20km", "50km", "100km"]
    
    for resolution in resolutions:
        route = sv.calculate_sea_route_simple(
            start=start,
            end=end,
            network_resolution=resolution,
            units="km"
        )
        
        print(f"{resolution:>5}: {route.properties.length:>10.1f} km, "
              f"{len(route.geometry.coordinates):>4} waypoints")
    print()


if __name__ == "__main__":
    example_1_quick_route()
    example_2_simple_api()
    example_3_advanced_api()
    example_4_custom_restrictions()
    example_5_convert_formats()
    example_6_network_resolutions()
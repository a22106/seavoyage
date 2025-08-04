"""
Demonstration of progress tracking and error recovery features in seavoyage
"""
import seavoyage as sv
import time


def demo_simple_progress():
    """Demo 1: Simple progress tracking"""
    print("=== Demo 1: Simple Progress Tracking ===\n")
    
    # Coordinates for Busan to Rotterdam
    start = (129.17, 35.075)  # Busan
    end = (4.158, 51.921)     # Rotterdam
    
    # Calculate route with progress display
    print("Calculating route from Busan to Rotterdam with progress tracking...\n")
    
    route = sv.seavoyage_with_progress(
        start, end,
        restrictions=["suez"],
        progress_callback=sv.SimpleProgressCallback(verbose=True)
    )
    
    print(f"\nRoute calculated!")
    print(f"Distance: {route['properties']['length']:.1f} {route['properties']['units']}")
    print(f"Duration: {route['properties']['duration_hours']:.1f} hours")
    print()


def demo_custom_progress():
    """Demo 2: Custom progress handler with emojis"""
    print("=== Demo 2: Custom Progress Handler ===\n")
    
    coords = sv.RouteCoordinates(
        start=(103.822, 1.264),  # Singapore
        end=(23.708, 37.945)     # Athens
    )
    
    # Custom progress handler with stage-specific emojis
    def emoji_progress(info: sv.ProgressInfo):
        emoji_map = {
            sv.ProgressStage.INITIALIZATION: "🚀",
            sv.ProgressStage.NETWORK_LOADING: "🗺️",
            sv.ProgressStage.RESTRICTION_PROCESSING: "🚧",
            sv.ProgressStage.PATHFINDING: "🧭",
            sv.ProgressStage.ROUTE_OPTIMIZATION: "⚡",
            sv.ProgressStage.FINALIZATION: "📦",
            sv.ProgressStage.COMPLETED: "✅",
            sv.ProgressStage.ERROR: "❌"
        }
        emoji = emoji_map.get(info.stage, "📍")
        print(f"{emoji} [{info.percent:5.1f}%] {info.message}")
    
    config = sv.RouteConfig(
        progress_callback=sv.FunctionProgressCallback(emoji_progress),
        restrictions=["suez"],
        units="km"
    )
    
    print("Calculating route from Singapore to Athens...\n")
    route = sv.calculate_sea_route_with_recovery(coords, config)
    
    print(f"\nRoute distance: {route.properties.length:.1f} km")
    print()


def demo_retry_mechanism():
    """Demo 3: Retry mechanism simulation"""
    print("=== Demo 3: Retry Mechanism ===\n")
    
    # Simulate a network that might fail
    attempt_count = 0
    
    def flaky_progress_handler(info: sv.ProgressInfo):
        """Progress handler that shows retry attempts"""
        if "Retry" in info.message:
            print(f"⚠️  {info.message}")
        else:
            print(f"▶️  {info.message}")
    
    coords = sv.RouteCoordinates(
        start=(129.17, 35.075),  # Busan
        end=(-73.949, 40.650)    # New York
    )
    
    config = sv.RouteConfig(
        progress_callback=sv.FunctionProgressCallback(flaky_progress_handler),
        enable_retry=True,
        max_retry_attempts=3,
        retry_delay=0.5,
        restrictions=["panama"],
        units="nm"
    )
    
    print("Calculating route from Busan to New York with retry enabled...\n")
    print("(Retry mechanism will activate on network errors)\n")
    
    try:
        route = sv.calculate_sea_route_with_recovery(coords, config)
        print(f"\n✅ Route calculated successfully!")
        print(f"Distance: {route.properties.length:.1f} nautical miles")
    except Exception as e:
        print(f"\n❌ Route calculation failed after retries: {e}")
    
    print()


def demo_progress_with_restrictions():
    """Demo 4: Progress tracking with multiple restrictions"""
    print("=== Demo 4: Progress with Multiple Restrictions ===\n")
    
    # Track restriction processing details
    class DetailedProgressTracker:
        def __init__(self):
            self.stages = []
            
        def __call__(self, info: sv.ProgressInfo):
            self.stages.append(info)
            
            # Show detailed info for restriction processing
            if info.stage == sv.ProgressStage.RESTRICTION_PROCESSING:
                print(f"🚧 {info.message}")
            elif info.stage == sv.ProgressStage.PATHFINDING:
                print(f"🧭 {info.message}")
            elif info.stage == sv.ProgressStage.COMPLETED:
                print(f"✅ {info.message}")
                
    tracker = DetailedProgressTracker()
    
    # Multiple restrictions
    coords = sv.RouteCoordinates(
        start=(103.822, 1.264),  # Singapore
        end=(-5.343, 36.144)     # Gibraltar
    )
    
    config = sv.RouteConfig(
        progress_callback=sv.FunctionProgressCallback(tracker),
        restrictions=["suez", "panama", "northwest"],
        units="km"
    )
    
    print("Calculating route with multiple restrictions...\n")
    route = sv.calculate_sea_route_with_recovery(coords, config)
    
    print(f"\nProcessed {len(tracker.stages)} progress stages")
    print(f"Route distance: {route.properties.length:.1f} km")
    print()


def demo_advanced_retry():
    """Demo 5: Advanced retry configuration"""
    print("=== Demo 5: Advanced Retry Configuration ===\n")
    
    # Progress handler that shows timing
    start_time = time.time()
    
    def timed_progress(info: sv.ProgressInfo):
        elapsed = time.time() - start_time
        print(f"[{elapsed:5.1f}s] {info.stage.value:20s} | {info.message}")
    
    # Advanced retry configuration
    retry_config = sv.RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=5.0,
        strategy=sv.RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor=2.0
    )
    
    coords = sv.RouteCoordinates(
        start=(129.17, 35.075),  # Busan  
        end=(8.468, 49.488)      # Hamburg
    )
    
    print("Calculating route with exponential backoff retry...\n")
    
    route = sv.seavoyage_with_progress(
        coords.start,
        coords.end,
        progress_callback=timed_progress,
        enable_retry=True,
        retry_config=retry_config
    )
    
    print(f"\nRoute calculated in {time.time() - start_time:.1f} seconds")
    print(f"Distance: {route['properties']['length']:.1f} {route['properties']['units']}")
    print()


def main():
    """Run all demos"""
    print("\n🌊 Seavoyage Progress & Retry Features Demo 🌊\n")
    print("This demo showcases the new progress tracking and error recovery features.\n")
    
    demos = [
        demo_simple_progress,
        demo_custom_progress,
        demo_retry_mechanism,
        demo_progress_with_restrictions,
        demo_advanced_retry
    ]
    
    for demo in demos:
        try:
            demo()
            input("Press Enter to continue to next demo...")
            print("\n" + "="*60 + "\n")
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
            break
        except Exception as e:
            print(f"\nDemo error: {e}")
            print("Continuing to next demo...")
            print("\n" + "="*60 + "\n")
    
    print("\n✅ All demos completed!")


if __name__ == "__main__":
    main()
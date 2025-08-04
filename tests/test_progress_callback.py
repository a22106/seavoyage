"""
Tests for progress callback functionality
"""
import pytest
from unittest.mock import Mock, MagicMock
from seavoyage import (
    seavoyage_with_progress,
    calculate_sea_route_with_recovery,
    RouteCoordinates,
    RouteConfig,
    SimpleProgressCallback,
    FunctionProgressCallback,
    ProgressInfo,
    ProgressStage
)


class TestProgressCallback:
    """Test progress callback functionality"""
    
    def test_simple_progress_callback(self, capsys):
        """Test simple progress callback that prints to stdout"""
        # Create callback
        callback = SimpleProgressCallback(verbose=True)
        
        # Test different progress stages
        callback(ProgressInfo(
            stage=ProgressStage.INITIALIZATION,
            percent=0.0,
            message="Starting"
        ))
        
        captured = capsys.readouterr()
        assert "Starting" in captured.out
        assert "initialization" in captured.out
        
    def test_function_progress_callback(self):
        """Test custom function progress callback"""
        # Track calls
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append({
                'stage': info.stage,
                'percent': info.percent,
                'message': info.message
            })
        
        # Create callback
        callback = FunctionProgressCallback(track_progress)
        
        # Test progress updates
        callback(ProgressInfo(
            stage=ProgressStage.NETWORK_LOADING,
            percent=50.0,
            message="Loading network"
        ))
        
        callback(ProgressInfo(
            stage=ProgressStage.PATHFINDING,
            percent=75.0,
            message="Finding path"
        ))
        
        # Verify updates
        assert len(progress_updates) == 2
        assert progress_updates[0]['stage'] == ProgressStage.NETWORK_LOADING
        assert progress_updates[0]['percent'] == 50.0
        assert progress_updates[1]['stage'] == ProgressStage.PATHFINDING
        
    def test_seavoyage_with_progress_tracking(self):
        """Test seavoyage with progress tracking"""
        # Track progress
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append(info)
        
        # Test points (same location for quick test)
        start = (129.17, 35.075)
        end = (129.17, 35.075)
        
        # Calculate route with progress
        result = seavoyage_with_progress(
            start,
            end,
            progress_callback=FunctionProgressCallback(track_progress)
        )
        
        # Verify result
        assert result['type'] == 'Feature'
        assert result['properties']['length'] == 0.0
        
        # Verify progress was tracked
        assert len(progress_updates) > 0
        
        # Check for expected stages
        stages = [update.stage for update in progress_updates]
        assert ProgressStage.INITIALIZATION in stages
        assert ProgressStage.COMPLETED in stages
        
    def test_calculate_sea_route_with_recovery_progress(self):
        """Test enhanced API with progress tracking"""
        # Track progress
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append({
                'stage': info.stage.value,
                'percent': info.percent,
                'message': info.message
            })
        
        # Configure route
        coords = RouteCoordinates(
            start=(129.17, 35.075),
            end=(129.17, 35.075)  # Same point for quick test
        )
        
        config = RouteConfig(
            progress_callback=FunctionProgressCallback(track_progress),
            enable_retry=True,
            max_retry_attempts=2
        )
        
        # Calculate route
        result = calculate_sea_route_with_recovery(coords, config)
        
        # Verify result
        assert result.properties.length == 0.0
        assert result.type == "Feature"
        
        # Verify progress tracking
        assert len(progress_updates) > 0
        
        # Find completed stage
        completed = [u for u in progress_updates if u['stage'] == 'completed']
        assert len(completed) == 1
        assert completed[0]['percent'] == 100.0
        
    def test_progress_stages_order(self):
        """Test that progress stages are reported in correct order"""
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append(info.stage)
        
        # Test with actual route calculation
        start = (103.822, 1.264)  # Singapore
        end = (103.822, 1.264)    # Same point
        
        result = seavoyage_with_progress(
            start,
            end,
            progress_callback=FunctionProgressCallback(track_progress),
            enable_retry=False
        )
        
        # Check stages appear in logical order
        expected_order = [
            ProgressStage.INITIALIZATION,
            ProgressStage.COMPLETED
        ]
        
        # For zero-length route, we skip most stages
        assert progress_updates[0] == ProgressStage.INITIALIZATION
        assert progress_updates[-1] == ProgressStage.COMPLETED
        
    def test_progress_error_handling(self):
        """Test progress tracking during errors"""
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append(info)
        
        # Invalid coordinates to trigger error
        start = (999.0, 999.0)  # Invalid
        end = (129.17, 35.075)
        
        # This should fail but track progress
        with pytest.raises(Exception):
            seavoyage_with_progress(
                start,
                end,
                progress_callback=FunctionProgressCallback(track_progress),
                enable_retry=False
            )
        
        # Should have some progress updates even on failure
        assert len(progress_updates) > 0
        
        # Check for error stage
        error_updates = [u for u in progress_updates if u.stage == ProgressStage.ERROR]
        if error_updates:
            assert "failed" in error_updates[0].message.lower()


class TestProgressPercentages:
    """Test progress percentage calculations"""
    
    def test_progress_percentages(self):
        """Test that progress percentages increase monotonically"""
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append({
                'percent': info.percent,
                'stage': info.stage
            })
        
        # Simple route calculation
        start = (129.17, 35.075)
        end = (129.17, 35.075)
        
        seavoyage_with_progress(
            start,
            end,
            progress_callback=FunctionProgressCallback(track_progress)
        )
        
        # Extract percentages (excluding error states)
        percentages = [
            u['percent'] for u in progress_updates 
            if u['stage'] != ProgressStage.ERROR
        ]
        
        # Verify percentages are non-decreasing
        for i in range(1, len(percentages)):
            assert percentages[i] >= percentages[i-1], \
                f"Progress decreased from {percentages[i-1]} to {percentages[i]}"
        
        # Verify final percentage is 100
        if percentages:
            assert percentages[-1] == 100.0


class TestProgressDetails:
    """Test progress details and metadata"""
    
    def test_progress_details(self):
        """Test that progress info includes relevant details"""
        progress_updates = []
        
        def track_progress(info: ProgressInfo):
            progress_updates.append(info)
        
        # Calculate route
        coords = RouteCoordinates(
            start=(129.17, 35.075),
            end=(129.17, 35.075)
        )
        
        config = RouteConfig(
            progress_callback=FunctionProgressCallback(track_progress),
            restrictions=["suez"]
        )
        
        calculate_sea_route_with_recovery(coords, config)
        
        # Check restriction processing stage has details
        restriction_updates = [
            u for u in progress_updates 
            if u.stage == ProgressStage.RESTRICTION_PROCESSING
        ]
        
        if restriction_updates:
            # At least one should mention restrictions
            messages = [u.message for u in restriction_updates]
            assert any("restriction" in msg.lower() for msg in messages)
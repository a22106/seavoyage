"""
Tests for retry and error recovery mechanisms
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import time
from seavoyage import (
    seavoyage_with_progress,
    calculate_sea_route_with_recovery,
    RouteCoordinates,
    RouteConfig,
    RetryConfig,
    RetryStrategy
)
from seavoyage.retry import (
    RetryHandler,
    ErrorRecoveryHandler,
    FallbackHandler,
    ErrorRecoveryResult
)
from seavoyage.exceptions import NetworkError, RouteError


class TestRetryHandler:
    """Test retry handler functionality"""
    
    def test_immediate_success(self):
        """Test function that succeeds immediately"""
        handler = RetryHandler()
        
        def success_func():
            return "success"
        
        result = handler.execute_with_retry(success_func)
        assert result == "success"
        assert handler._attempt_count == 1
        
    def test_retry_on_failure(self):
        """Test retry on failure"""
        handler = RetryHandler(RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            strategy=RetryStrategy.IMMEDIATE
        ))
        
        attempt_count = 0
        
        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise NetworkError("Network error")
            return "success after retries"
        
        result = handler.execute_with_retry(failing_func)
        assert result == "success after retries"
        assert attempt_count == 3
        
    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries"""
        handler = RetryHandler(RetryConfig(
            max_attempts=2,
            strategy=RetryStrategy.IMMEDIATE
        ))
        
        def always_fails():
            raise NetworkError("Always fails")
        
        with pytest.raises(NetworkError):
            handler.execute_with_retry(always_fails)
        
        assert handler._attempt_count == 2
        
    def test_retry_callback(self):
        """Test retry callback is called"""
        handler = RetryHandler(RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.IMMEDIATE
        ))
        
        retry_calls = []
        
        def on_retry(attempt, error):
            retry_calls.append((attempt, str(error)))
        
        attempt_count = 0
        
        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise NetworkError(f"Error {attempt_count}")
            return "success"
        
        result = handler.execute_with_retry(
            failing_func,
            on_retry=on_retry
        )
        
        assert result == "success"
        assert len(retry_calls) == 2
        assert retry_calls[0] == (1, "Error 1")
        assert retry_calls[1] == (2, "Error 2")
        
    def test_exponential_backoff(self):
        """Test exponential backoff delay calculation"""
        handler = RetryHandler(RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=10.0
        ))
        
        # Test delay calculations
        assert handler._calculate_delay(1) == 1.0
        assert handler._calculate_delay(2) == 2.0
        assert handler._calculate_delay(3) == 4.0
        assert handler._calculate_delay(4) == 8.0
        assert handler._calculate_delay(5) == 10.0  # Capped at max_delay
        
    def test_linear_backoff(self):
        """Test linear backoff delay calculation"""
        handler = RetryHandler(RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_delay=1.0,
            max_delay=5.0
        ))
        
        assert handler._calculate_delay(1) == 1.0
        assert handler._calculate_delay(2) == 2.0
        assert handler._calculate_delay(3) == 3.0
        assert handler._calculate_delay(6) == 5.0  # Capped at max_delay


class TestFallbackHandler:
    """Test fallback handler functionality"""
    
    def test_primary_success(self):
        """Test primary function succeeds"""
        handler = FallbackHandler()
        
        def primary():
            return "primary success"
        
        def fallback1():
            return "fallback1"
        
        result = handler.execute_with_fallback(
            primary,
            [fallback1]
        )
        
        assert result == "primary success"
        
    def test_fallback_on_primary_failure(self):
        """Test fallback when primary fails"""
        handler = FallbackHandler()
        
        def primary():
            raise NetworkError("Primary failed")
        
        def fallback1():
            return "fallback1 success"
        
        result = handler.execute_with_fallback(
            primary,
            [fallback1]
        )
        
        assert result == "fallback1 success"
        
    def test_multiple_fallbacks(self):
        """Test multiple fallback functions"""
        handler = FallbackHandler()
        
        def primary():
            raise NetworkError("Primary failed")
        
        def fallback1():
            raise RouteError("Fallback1 failed")
        
        def fallback2():
            return "fallback2 success"
        
        result = handler.execute_with_fallback(
            primary,
            [fallback1, fallback2]
        )
        
        assert result == "fallback2 success"
        
    def test_all_fallbacks_fail(self):
        """Test when all functions fail"""
        handler = FallbackHandler()
        
        def primary():
            raise NetworkError("Primary failed")
        
        def fallback1():
            raise RouteError("Fallback1 failed")
        
        with pytest.raises(RouteError):
            handler.execute_with_fallback(
                primary,
                [fallback1]
            )


class TestErrorRecoveryHandler:
    """Test comprehensive error recovery"""
    
    def test_recovery_with_retry(self):
        """Test recovery using retry strategy"""
        handler = ErrorRecoveryHandler(
            retry_config=RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.IMMEDIATE
            )
        )
        
        attempt_count = 0
        
        def func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise NetworkError("Network error")
            return "success"
        
        result = handler.recover(func)
        
        assert result.success is True
        assert result.result == "success"
        assert result.recovery_method == "retry"
        assert result.attempts == 2
        
    def test_recovery_failure(self):
        """Test recovery failure"""
        handler = ErrorRecoveryHandler(
            retry_config=RetryConfig(
                max_attempts=2,
                strategy=RetryStrategy.IMMEDIATE
            ),
            enable_fallback=False
        )
        
        def always_fails():
            raise NetworkError("Always fails")
        
        result = handler.recover(always_fails)
        
        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, NetworkError)
        assert result.recovery_method is None


class TestIntegrationWithAPI:
    """Test integration with seavoyage API"""
    
    def test_route_calculation_with_retry(self):
        """Test route calculation with retry enabled"""
        coords = RouteCoordinates(
            start=(129.17, 35.075),
            end=(129.17, 35.075)  # Same point for quick test
        )
        
        config = RouteConfig(
            enable_retry=True,
            max_retry_attempts=3,
            retry_delay=0.1
        )
        
        result = calculate_sea_route_with_recovery(coords, config)
        
        assert result.properties.length == 0.0
        assert result.type == "Feature"
        
    @patch('seavoyage.enhanced_api._original_seavoyage')
    def test_retry_on_network_error(self, mock_seavoyage):
        """Test retry behavior on network errors"""
        # Setup mock to fail twice then succeed
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Simulated network error")
            return {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[129.17, 35.075], [129.17, 35.075]]
                },
                "properties": {
                    "length": 0.0,
                    "duration_hours": 0.0,
                    "units": "nm",
                    "calculation_method": "enhanced"
                }
            }
        
        mock_seavoyage.side_effect = side_effect
        
        # Track retries
        retry_count = 0
        
        def on_retry(attempt, error):
            nonlocal retry_count
            retry_count += 1
        
        # Calculate with retry
        result = seavoyage_with_progress(
            (129.17, 35.075),
            (129.18, 35.076),
            enable_retry=True,
            retry_config=RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.IMMEDIATE
            )
        )
        
        # Verify retries happened
        assert call_count == 3
        assert result['properties']['length'] == 0.0
        
    def test_disable_retry(self):
        """Test that retry can be disabled"""
        coords = RouteCoordinates(
            start=(129.17, 35.075),
            end=(129.17, 35.075)
        )
        
        config = RouteConfig(
            enable_retry=False
        )
        
        # Should work without retry
        result = calculate_sea_route_with_recovery(coords, config)
        assert result.properties.length == 0.0
        
    def test_retry_with_progress_tracking(self):
        """Test retry with progress tracking"""
        progress_updates = []
        progress_info_list = []
        
        def track_progress(info):
            progress_updates.append(info.message)
            progress_info_list.append(info)
        
        coords = RouteCoordinates(
            start=(129.17, 35.075),
            end=(129.17, 35.075)
        )
        
        config = RouteConfig(
            progress_callback=track_progress,
            enable_retry=True,
            max_retry_attempts=2
        )
        
        result = calculate_sea_route_with_recovery(coords, config)
        
        # Should have progress updates
        assert len(progress_updates) > 0
        
        # Check that we reached completion (100% progress or COMPLETED stage)
        from seavoyage.callbacks import ProgressStage
        completed = any(
            info.percent == 100.0 or info.stage == ProgressStage.COMPLETED 
            for info in progress_info_list
        )
        assert completed, f"Progress should reach completion. Messages: {progress_updates}"
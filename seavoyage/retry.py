"""
Retry and error recovery mechanisms for route calculation
"""
from dataclasses import dataclass
from typing import Optional, List, Callable, Any, Dict
from enum import Enum
import time
import logging
from seavoyage.exceptions import RouteError, NetworkError


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for route calculation"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_factor: float = 2.0
    retry_on_exceptions: Optional[List[type]] = None
    fallback_resolutions: Optional[List[str]] = None  # e.g., ["50km", "100km"]
    
    def __post_init__(self):
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = [NetworkError, RouteError]
        if self.fallback_resolutions is None:
            self.fallback_resolutions = ["50km", "100km"]


class RetryHandler:
    """Handles retry logic and error recovery"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self._attempt_count = 0
        
    def execute_with_retry(
        self, 
        func: Callable[..., Any],
        *args,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> Any:
        """Execute a function with retry logic
        
        Parameters
        ----------
        func : callable
            Function to execute
        *args
            Positional arguments for the function
        on_retry : callable, optional
            Callback function called on each retry with (attempt_number, exception)
        **kwargs
            Keyword arguments for the function
            
        Returns
        -------
        Any
            Result from the function
            
        Raises
        ------
        Exception
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            self._attempt_count = attempt
            
            try:
                logger.debug(f"Attempt {attempt}/{self.config.max_attempts}")
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                should_retry = any(
                    isinstance(e, exc_type) 
                    for exc_type in self.config.retry_on_exceptions
                )
                
                if not should_retry or attempt == self.config.max_attempts:
                    logger.error(f"Failed after {attempt} attempts: {str(e)}")
                    raise
                    
                # Calculate delay
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Attempt {attempt} failed: {str(e)}. "
                    f"Retrying in {delay:.1f} seconds..."
                )
                
                # Call retry callback if provided
                if on_retry:
                    on_retry(attempt, e)
                    
                # Wait before retry
                time.sleep(delay)
                
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
            
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on retry strategy"""
        if self.config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
            
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_delay * attempt
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_delay * (self.config.backoff_factor ** (attempt - 1))
            
        else:
            delay = self.config.initial_delay
            
        return min(delay, self.config.max_delay)


class FallbackHandler:
    """Handles fallback strategies for route calculation"""
    
    def __init__(self, fallback_options: Optional[List[Dict[str, Any]]] = None):
        """
        Parameters
        ----------
        fallback_options : list of dict, optional
            List of fallback configurations to try in order.
            Each dict can contain alternative parameters like:
            - resolution: Network resolution to use
            - restrictions: Modified restriction list
            - method: Alternative calculation method
        """
        self.fallback_options = fallback_options or []
        
    def execute_with_fallback(
        self,
        primary_func: Callable[..., Any],
        fallback_funcs: List[Callable[..., Any]],
        *args,
        on_fallback: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> Any:
        """Execute with fallback functions
        
        Parameters
        ----------
        primary_func : callable
            Primary function to try first
        fallback_funcs : list of callable
            Fallback functions to try in order
        *args
            Positional arguments for the functions
        on_fallback : callable, optional
            Callback when falling back, called with (fallback_index, exception)
        **kwargs
            Keyword arguments for the functions
            
        Returns
        -------
        Any
            Result from the first successful function
            
        Raises
        ------
        Exception
            Last exception if all functions fail
        """
        all_funcs = [primary_func] + fallback_funcs
        last_exception = None
        
        for i, func in enumerate(all_funcs):
            try:
                if i == 0:
                    logger.debug("Trying primary function")
                else:
                    logger.debug(f"Trying fallback function {i}")
                    
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if i < len(all_funcs) - 1:  # Not the last function
                    logger.warning(
                        f"Function {i} failed: {str(e)}. "
                        f"Trying fallback..."
                    )
                    
                    if on_fallback and i > 0:
                        on_fallback(i, e)
                else:
                    logger.error(f"All functions failed. Last error: {str(e)}")
                    
        if last_exception:
            raise last_exception


class PartialRouteHandler:
    """Handles partial route calculation when full route fails"""
    
    def calculate_partial_route(
        self,
        start: tuple,
        end: tuple,
        waypoints: List[tuple],
        failed_segment: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Calculate partial route avoiding failed segments
        
        Parameters
        ----------
        start : tuple
            Starting coordinates
        end : tuple
            Ending coordinates
        waypoints : list of tuple
            Intermediate waypoints to try
        failed_segment : tuple, optional
            Segment that failed (start_point, end_point)
            
        Returns
        -------
        dict or None
            Partial route if successful, None otherwise
        """
        # Implementation would calculate alternative routes
        # through waypoints, avoiding the failed segment
        # This is a placeholder for the actual implementation
        logger.info("Attempting to calculate partial route")
        return None


@dataclass
class ErrorRecoveryResult:
    """Result of error recovery attempt"""
    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None
    recovery_method: Optional[str] = None
    attempts: int = 1


class ErrorRecoveryHandler:
    """Comprehensive error recovery handler"""
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        enable_partial_routes: bool = True,
        enable_fallback: bool = True
    ):
        self.retry_handler = RetryHandler(retry_config)
        self.fallback_handler = FallbackHandler()
        self.partial_route_handler = PartialRouteHandler()
        self.enable_partial_routes = enable_partial_routes
        self.enable_fallback = enable_fallback
        
    def recover(
        self,
        func: Callable[..., Any],
        *args,
        recovery_callbacks: Optional[Dict[str, Callable]] = None,
        **kwargs
    ) -> ErrorRecoveryResult:
        """Attempt to recover from errors using multiple strategies
        
        Parameters
        ----------
        func : callable
            Function to execute
        *args
            Positional arguments
        recovery_callbacks : dict, optional
            Callbacks for different recovery events:
            - 'on_retry': Called on each retry
            - 'on_fallback': Called on fallback
            - 'on_partial': Called when trying partial route
        **kwargs
            Keyword arguments
            
        Returns
        -------
        ErrorRecoveryResult
            Result of recovery attempt
        """
        callbacks = recovery_callbacks or {}
        
        try:
            # First try with retry
            result = self.retry_handler.execute_with_retry(
                func, *args, 
                on_retry=callbacks.get('on_retry'),
                **kwargs
            )
            
            return ErrorRecoveryResult(
                success=True,
                result=result,
                recovery_method="retry",
                attempts=self.retry_handler._attempt_count
            )
            
        except Exception as e:
            logger.error(f"Retry failed: {str(e)}")
            
            # Try fallback strategies if enabled
            if self.enable_fallback and hasattr(self, '_get_fallback_functions'):
                try:
                    fallback_funcs = self._get_fallback_functions(func, *args, **kwargs)
                    result = self.fallback_handler.execute_with_fallback(
                        func, fallback_funcs, *args,
                        on_fallback=callbacks.get('on_fallback'),
                        **kwargs
                    )
                    
                    return ErrorRecoveryResult(
                        success=True,
                        result=result,
                        recovery_method="fallback"
                    )
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback failed: {str(fallback_error)}")
                    e = fallback_error
                    
            # Try partial route if enabled and applicable
            if self.enable_partial_routes and self._can_use_partial_route(*args, **kwargs):
                try:
                    if callbacks.get('on_partial'):
                        callbacks['on_partial']()
                        
                    partial_result = self._calculate_partial_route(*args, **kwargs)
                    if partial_result:
                        return ErrorRecoveryResult(
                            success=True,
                            result=partial_result,
                            recovery_method="partial"
                        )
                        
                except Exception as partial_error:
                    logger.error(f"Partial route failed: {str(partial_error)}")
                    
            # All recovery attempts failed
            return ErrorRecoveryResult(
                success=False,
                error=e,
                recovery_method=None
            )
            
    def _can_use_partial_route(self, *args, **kwargs) -> bool:
        """Check if partial route calculation is applicable"""
        # Check if we have start and end coordinates
        return len(args) >= 2 and isinstance(args[0], tuple) and isinstance(args[1], tuple)
        
    def _calculate_partial_route(self, *args, **kwargs) -> Optional[Any]:
        """Calculate partial route"""
        # Extract start and end from args
        if len(args) >= 2:
            start, end = args[0], args[1]
            # This would use the partial route handler
            # Placeholder for actual implementation
            return None
        return None
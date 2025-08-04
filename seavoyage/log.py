import logging
import os
from typing import Optional

# Centralized logging configuration for seavoyage package


class LogConfig:
    """Centralized logging configuration manager."""
    
    _instance: Optional['LogConfig'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Initialize the logger with appropriate configuration."""
        # Get log level from environment variable (default: INFO)
        log_level = os.environ.get("SEAVOYAGE_LOG_LEVEL", "INFO").upper()
        
        # Create logger
        self._logger = logging.getLogger("seavoyage")
        self._logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Remove existing handlers to prevent duplication
        self._logger.handlers = []
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Set format
        formatter = logging.Formatter(
            "[%(asctime)s][%(levelname)s][%(module)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self._logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self._logger.propagate = False
    
    @property
    def logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        if self._logger is None:
            self._setup_logger()
        return self._logger
    
    def set_level(self, level: str) -> None:
        """
        Set the logging level.
        
        Args:
            level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level_value = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(level_value)
        for handler in self._logger.handlers:
            handler.setLevel(level_value)
    
    def get_level(self) -> str:
        """Get the current logging level as a string."""
        return logging.getLevelName(self._logger.level)


# Create singleton instance
_log_config = LogConfig()
logger = _log_config.logger

# Convenience functions
def set_log_level(level: str) -> None:
    """Set the logging level for seavoyage."""
    _log_config.set_level(level)


def get_log_level() -> str:
    """Get the current logging level for seavoyage."""
    return _log_config.get_level()
"""
Route navigation related exception classes
"""

from typing import Optional, List, Tuple
from seavoyage.utils.coordinates import decdeg_to_degmin


class RouteError(Exception):
    """Base exception class for route navigation errors"""
    pass


class UnreachableDestinationError(RouteError):
    """Exception raised when destination cannot be reached"""
    
    def __init__(
        self, 
        start: Tuple[float, float], 
        end: Tuple[float, float], 
        restriction_names: Optional[List[str]] = None, 
        message: Optional[str] = None
    ):
        """
        Args:
            start: Starting coordinates (longitude, latitude)
            end: Destination coordinates (longitude, latitude)
            restriction_names: List of applied restriction zone names
            message: Additional message
        """
        self.start = start
        self.end = end
        self.restriction_names = restriction_names or []
        
        if not message:
            if restriction_names:
                message = f"Cannot reach destination {end} due to restriction zones: {', '.join(restriction_names)}"
            else:
                message = f"Cannot reach destination {end}"
                
        super().__init__(message)


class DestinationInRestrictionError(RouteError):
    """Exception raised when destination is within a restriction zone"""
    
    def __init__(
        self, 
        end: Tuple[float, float], 
        restriction_name: str, 
        message: Optional[str] = None
    ):
        """
        Args:
            end: Destination coordinates (longitude, latitude)
            restriction_name: Restriction zone name
            message: Additional message
        """
        self.end = end
        self.restriction_name = restriction_name
        
        if not message:
            message = f"Destination {decdeg_to_degmin(end)} is within restriction zone '{restriction_name}'"
            
        super().__init__(message)


class StartInRestrictionError(RouteError):
    """Exception raised when starting point is within a restriction zone"""
    
    def __init__(
        self, 
        start: Tuple[float, float], 
        restriction_name: str, 
        message: Optional[str] = None
    ):
        """
        Args:
            start: Starting coordinates (longitude, latitude)
            restriction_name: Restriction zone name
            message: Additional message
        """
        self.start = start
        self.restriction_name = restriction_name
        
        if not message:
            message = f"Starting point {decdeg_to_degmin(start)} is within restriction zone '{restriction_name}'"
            
        super().__init__(message)


class IsolatedOriginError(RouteError):
    """Exception raised when starting point is isolated and cannot move due to restriction zones"""
    
    def __init__(
        self, 
        start: Tuple[float, float], 
        restriction_names: Optional[List[str]] = None, 
        message: Optional[str] = None
    ):
        """
        Args:
            start: Starting coordinates (longitude, latitude)
            restriction_names: List of applied restriction zone names
            message: Additional message
        """
        self.start = start
        self.restriction_names = restriction_names or []
        
        if not message:
            if restriction_names:
                message = f"Starting point {start} is isolated by restriction zones: {', '.join(restriction_names)}"
            else:
                message = f"Starting point {start} is isolated by restriction zones"
                
        super().__init__(message)
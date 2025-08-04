"""
Data models for seavoyage API
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Union, Any, Literal
from searoute.classes.passages import Passage
from searoute.classes.marnet import Marnet
from searoute.classes.ports import Ports


@dataclass
class RouteConfig:
    """Configuration for route calculation"""
    units: Literal["nm", "km", "m", "mi", "ft", "in", "rad", "deg"] = "nm"
    speed_knot: float = 10.0
    restrictions: Optional[List[str]] = None
    append_origin_destination: bool = False
    include_ports: bool = False
    port_params: Optional[Dict[str, Any]] = None
    return_passages: bool = False


@dataclass
class NetworkConfig:
    """Configuration for maritime network"""
    maritime_network: Optional[Union['MNetwork', Marnet]] = None
    port_network: Optional[Ports] = None
    resolution: Optional[Literal["5km", "10km", "20km", "50km", "100km"]] = None


@dataclass
class RouteCoordinates:
    """Coordinates for route start and end points"""
    start: Tuple[float, float]
    end: Tuple[float, float]
    
    def __post_init__(self):
        if not isinstance(self.start, tuple) or len(self.start) != 2:
            raise ValueError("start must be a tuple of (longitude, latitude)")
        if not isinstance(self.end, tuple) or len(self.end) != 2:
            raise ValueError("end must be a tuple of (longitude, latitude)")


@dataclass
class RouteProperties:
    """Properties of a calculated route"""
    length: float
    duration_hours: float
    units: str
    passages_crossed: Optional[List[str]] = None
    speed_knot: Optional[float] = None
    
    
@dataclass 
class RouteGeometry:
    """Geometry information for a route"""
    type: str = "LineString"
    coordinates: List[List[float]] = field(default_factory=list)


@dataclass
class RouteResult:
    """Result of route calculation"""
    type: str = "Feature"
    geometry: RouteGeometry = field(default_factory=RouteGeometry)
    properties: RouteProperties = field(default_factory=lambda: RouteProperties(0.0, 0.0, "nm"))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteResult':
        """Create RouteResult from dictionary"""
        geometry = RouteGeometry(
            type=data["geometry"]["type"],
            coordinates=data["geometry"]["coordinates"]
        )
        
        props_data = data["properties"]
        properties = RouteProperties(
            length=props_data["length"],
            duration_hours=props_data["duration_hours"],
            units=props_data["units"],
            passages_crossed=props_data.get("passages_crossed"),
            speed_knot=props_data.get("speed_knot")
        )
        
        return cls(
            type=data["type"],
            geometry=geometry,
            properties=properties
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert RouteResult to dictionary (GeoJSON format)"""
        result = {
            "type": self.type,
            "geometry": {
                "type": self.geometry.type,
                "coordinates": self.geometry.coordinates
            },
            "properties": {
                "length": self.properties.length,
                "duration_hours": self.properties.duration_hours,
                "units": self.properties.units
            }
        }
        
        if self.properties.passages_crossed is not None:
            result["properties"]["passages_crossed"] = self.properties.passages_crossed
        
        if self.properties.speed_knot is not None:
            result["properties"]["speed_knot"] = self.properties.speed_knot
            
        return result
import os
import json
from typing import Optional, Dict, List, Tuple
from shapely.geometry import Polygon, MultiPolygon, Point

from seavoyage.log import logger

# Global custom restriction registry
_CUSTOM_RESTRICTION_REGISTRY: Dict[str, 'CustomRestriction'] = {}

class CustomRestriction:
    """Class defining custom restriction zones"""
    
    def __init__(self, name: str, polygon):
        """
        CustomRestriction 객체 초기화
        
        Args:
            name (str): 제한 구역 이름
            polygon: Shapely Polygon 또는 MultiPolygon
        """
        self.name = name
        
        if isinstance(polygon, (Polygon, MultiPolygon)):
            self.polygon = polygon
        else:
            raise TypeError("polygon must be a Shapely Polygon or MultiPolygon type")
    
    def contains_point(self, point: Tuple[float, float]) -> bool:
        """
        Check if the given point is within the restriction zone.
        
        Args:
            point: (longitude, latitude) coordinates
            
        Returns:
            bool: True if point is within restriction zone, False otherwise
        """
        # Convert coordinates to Point object
        shapely_point = Point(point)
        # Check if polygon contains the point
        return self.polygon.contains(shapely_point)
        
    @classmethod
    def from_geojson(cls, name: str, geojson_data: dict) -> 'CustomRestriction':
        """
        GeoJSON 데이터로부터 CustomRestriction 생성
        
        Args:
            name (str): 제한 구역 이름
            geojson_data (dict): GeoJSON 데이터 (Feature 또는 FeatureCollection)
            
        Returns:
            CustomRestriction: 생성된 CustomRestriction 객체
        """
        if 'type' not in geojson_data:
            raise ValueError("Invalid GeoJSON format")
            
        if geojson_data['type'] == 'FeatureCollection':
            # 여러 Feature를 하나의 MultiPolygon으로 병합
            polygons = []
            for feature in geojson_data['features']:
                if feature['geometry']['type'] == 'Polygon':
                    coords = feature['geometry']['coordinates']
                    polygons.append(Polygon(coords[0], holes=coords[1:] if len(coords) > 1 else None))
                elif feature['geometry']['type'] == 'MultiPolygon':
                    for poly_coords in feature['geometry']['coordinates']:
                        polygons.append(Polygon(poly_coords[0], holes=poly_coords[1:] if len(poly_coords) > 1 else None))
            
            if not polygons:
                raise ValueError("No Polygon or MultiPolygon found in GeoJSON")
                
            if len(polygons) == 1:
                return cls(name, polygons[0])
            else:
                return cls(name, MultiPolygon(polygons))
                
        elif geojson_data['type'] == 'Feature':
            if geojson_data['geometry']['type'] == 'Polygon':
                coords = geojson_data['geometry']['coordinates']
                return cls(name, Polygon(coords[0], holes=coords[1:] if len(coords) > 1 else None))
            elif geojson_data['geometry']['type'] == 'MultiPolygon':
                polygons = []
                for poly_coords in geojson_data['geometry']['coordinates']:
                    polygons.append(Polygon(poly_coords[0], holes=poly_coords[1:] if len(poly_coords) > 1 else None))
                return cls(name, MultiPolygon(polygons))
            else:
                raise ValueError("Feature must be of type Polygon or MultiPolygon")
        else:
            raise ValueError("Unsupported GeoJSON type. FeatureCollection or Feature required")

    @classmethod
    def from_geojson_file(cls, name: str, file_path: str) -> 'CustomRestriction':
        """
        GeoJSON 파일에서 CustomRestriction 생성
        
        Args:
            name (str): 제한 구역 이름
            file_path (str): GeoJSON 파일 경로
            
        Returns:
            CustomRestriction: 생성된 CustomRestriction 객체
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        return cls.from_geojson(name, geojson_data)


def register_custom_restriction(name: str, geojson_file_path: str) -> CustomRestriction:
    """
    Register a custom restriction zone.
    
    Args:
        name (str): Restriction zone name
        geojson_file_path (str): GeoJSON file path
    
    Returns:
        CustomRestriction: The registered restriction object
    """
    restriction = CustomRestriction.from_geojson_file(name, geojson_file_path)
    _CUSTOM_RESTRICTION_REGISTRY[name] = restriction
    logger.debug(f"Restriction zone registered successfully: {name}, file: {geojson_file_path}")
    return restriction

def get_custom_restriction(name: str) -> Optional[CustomRestriction]:
    """
    Get a registered custom restriction zone by name.
    
    Args:
        name (str): Restriction zone name
        
    Returns:
        Optional[CustomRestriction]: Restriction zone object or None
    """
    return _CUSTOM_RESTRICTION_REGISTRY.get(name)

def list_custom_restrictions() -> List[str]:
    """
    Return all registered custom restriction zone names.
    
    Returns:
        List[str]: List of registered restriction zone names
    """
    return list(_CUSTOM_RESTRICTION_REGISTRY.keys())

def reset_custom_restrictions() -> None:
    """
    Reset all custom restriction zones.
    """
    _CUSTOM_RESTRICTION_REGISTRY.clear()


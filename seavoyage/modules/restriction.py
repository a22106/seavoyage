import os
import json
from shapely.geometry import Polygon, MultiPolygon

from seavoyage.log import logger

# 전역 제한 구역 저장소
_CUSTOM_RESTRICTION_REGISTRY = {}

class CustomRestriction:
    """커스텀 제한 구역을 정의하는 클래스"""
    
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
            raise TypeError("polygon은 Shapely Polygon 또는 MultiPolygon 타입이어야 합니다.")
        
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
            raise ValueError("유효하지 않은 GeoJSON 형식입니다.")
            
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
                raise ValueError("GeoJSON에 Polygon 또는 MultiPolygon이 없습니다.")
                
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
                raise ValueError("Feature는 Polygon 또는 MultiPolygon 타입이어야 합니다.")
        else:
            raise ValueError("지원되지 않는 GeoJSON 타입입니다. FeatureCollection 또는 Feature가 필요합니다.")

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
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        return cls.from_geojson(name, geojson_data)


def register_custom_restriction(name: str, geojson_file_path: str):
    """
    커스텀 제한 구역을 등록합니다.
    
    Args:
        name (str): 제한 구역 이름
        geojson_file_path (str): GeoJSON 파일 경로
    """
    restriction = CustomRestriction.from_geojson_file(name, geojson_file_path)
    _CUSTOM_RESTRICTION_REGISTRY[name] = restriction
    logger.info(f"제한 구역 등록 성공: {name}, 파일: {geojson_file_path}")
    return restriction

def get_custom_restriction(name: str):
    """
    이름으로 등록된 커스텀 제한 구역을 가져옵니다.
    
    Args:
        name (str): 제한 구역 이름
        
    Returns:
        Optional[CustomRestriction]: 제한 구역 객체 또는 None
    """
    return _CUSTOM_RESTRICTION_REGISTRY.get(name)

def list_custom_restrictions():
    """
    등록된 모든 커스텀 제한 구역 이름을 반환합니다.
    
    Returns:
        List[str]: 등록된 제한 구역 이름 목록
    """
    return list(_CUSTOM_RESTRICTION_REGISTRY.keys())
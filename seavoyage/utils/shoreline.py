from enum import Enum
from shapely.geometry import MultiPolygon
import geopandas as gpd

from seavoyage.settings import SHORELINE_DIR

class ShorelineLevel(Enum):
    CRUDE = 'c'
    LOW = "l"
    INTERMEDIATE = "i"
    HIGH = "h"
    
    def values(self):
        return [level.value for level in ShorelineLevel]

def _load_shoreline(level: ShorelineLevel) -> MultiPolygon:
    if not isinstance(level, ShorelineLevel):
        raise ValueError(f"Invalid shoreline level: {level}")
    
    shoreline_path = SHORELINE_DIR / f"{level.value}" / f"GSHHS_{level.value}_L1.shp"
    
    gdf: gpd.GeoDataFrame = gpd.read_file(shoreline_path)
    gdf['geometry'] = gdf['geometry'].make_valid()
    try:
        return gdf.union_all(method='coverage')
    except Exception as e:
        print(f"Error loading land polygon: {e}\nTrying unary method...")
        # coverage method가 실패하면 unary method 시도
        return gdf.union_all(method='unary')

shoreline = _load_shoreline(ShorelineLevel.LOW)
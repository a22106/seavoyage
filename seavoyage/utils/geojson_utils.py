import geojson
from pathlib import Path
from typing import Union

def load_geojson(file_path: Union[str, Path]) -> dict:
    """Load GeoJSON data from file.
    
    Parameters
    ----------
    file_path : str or Path
        Path to the GeoJSON file
        
    Returns
    -------
    dict
        GeoJSON data
    """
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        geojson_data = geojson.load(f)
    return geojson_data

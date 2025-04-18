from seavoyage.log import logger
import geopandas as gpd
import fiona

def print_gpkg_layers(gpkg_file: str):
    layers = fiona.listlayers(gpkg_file)
    logger.info("레이어 목록:", layers)
    
def convert_gpkg_to_geojson(gpkg_file: str, output_geojson: str = ""):
    layer_name = "type"  # 변환할 레이어 이름 (gpkg 파일 내의 실제 레이어 이름으로 변경)
    if not output_geojson:
        output_geojson = f"modules/geojson/{gpkg_file.split('/')[-1].split('.')[0]}.geojson"

    # GeoPackage 파일에서 지정한 레이어를 읽어옵니다.
    gdf = gpd.read_file(gpkg_file, layer=layer_name)

    # GeoDataFrame을 GeoJSON 파일로 저장합니다.
    gdf.to_file(output_geojson, driver="GeoJSON")

    logger.info(f"'{gpkg_file}'의 레이어 '{layer_name}'가 '{output_geojson}'로 변환되었습니다.")
    return output_geojson
# seavoyage/utils/shapely_utils.py
import numpy as np
from shapely import LineString
import geojson
import geopandas as gpd

from shapely import MultiPoint, MultiPolygon, Point
from shapely.prepared import prep, PreparedGeometry


def extract_linestrings_from_geojson(geojson_feature_collection: geojson.GeoJSON) -> np.ndarray[LineString]:
    # 각 feature에서 coordinates를 추출하여 LineString 객체 생성
    linestrings = np.array([])
    for feature in geojson_feature_collection['features']:
        coords = feature['geometry']['coordinates']
        linestrings = np.append(linestrings, LineString(coords))
    
    return linestrings

# geojson 파일에서 LineString 리스트 추출
def extract_linestrings_from_geojson_file(geojson_path: str) -> np.ndarray[LineString]:
    # geojson 파일 읽기
    with open(geojson_path) as f:
        data = geojson.load(f)
    
    linestrings = extract_linestrings_from_geojson(data)
    return linestrings

def _bounding_boxes_intersect(bbox1, bbox2) -> bool:
    """
    bbox1, bbox2: (minx, miny, maxx, maxy)
    두 개의 사각형(바운딩 박스)이 겹치는지 여부를 반환합니다.
    """
    return not (
        bbox1[2] < bbox2[0] or  # bbox1.maxx < bbox2.minx
        bbox1[0] > bbox2[2] or  # bbox1.minx > bbox2.maxx
        bbox1[3] < bbox2[1] or  # bbox1.maxy < bbox2.miny
        bbox1[1] > bbox2[3]     # bbox1.miny > bbox2.maxy
    )

def is_valid_edge(
    line: LineString, 
    land_polygon: MultiPolygon, 
    land_polygon_bbox: tuple[float, float, float, float] = None) -> bool:
    """
    edge인 line이 육지 폴리곤 land_polygon과 교차하는지 확인
    :param line: 두 좌표를 연결하는 LineString 객체
    :param land_polygon: 육지 폴리곤
    :return: 교차하지 않는 경우 True, 교차하는 경우 False
    """
    # 1) 바운딩 박스끼리 겹치는지 먼저 확인
    if land_polygon_bbox and not _bounding_boxes_intersect(line.bounds, land_polygon_bbox):
        return True
    
    # 2) prepared geometry 생성
    prepared_land_polygon = prep(land_polygon)
    
    # 3) prepared geometry로 교차 검사
    if not prepared_land_polygon.intersects(line):
        return True
    
    # 3) 실제 교차 시점에서, 시작점/끝점이 해안선 위에 닿는지(접하는지)만 통과시키고
    # 그외 육지를 관통하면 잘못된 edge로 처리
    intersection = prepared_land_polygon.context.intersection(line)
    
    start = Point(line.coords[0])
    end = Point(line.coords[-1])

    # intersection이 LineString이면 완전히 겹치는 구간이 있다는 뜻 -> 무효
    # intersection이 MultiLineString이어도 같은 맥락
    if intersection.geom_type in ['LineString', 'MultiLineString']:
        return False
    
    # intersection이 Point나 MultiPoint라면, 시작/끝 점만 겹치는지 검사
    if isinstance(intersection, MultiPoint):
        points = list(intersection.geoms)
    else:
        # 단일 Point일 수도 있으므로 리스트로 묶어줌
        points = [intersection]
    
    # 시작점/끝점 말고도 중간 지점에서 닿으면 교차로 간주
    for pt in points:
        if not (pt.touches(start) or pt.touches(end)):
            return False
    
    return True

def remove_edges_cross_land(marnet, land_polygon: MultiPolygon):
    """
    marnet에서 육지 폴리곤과 교차하는 간선을 제거
    :param marnet: MNetwork 객체
    :param land_polygon: 육지 폴리곤
    :return: 육지 폴리곤과 교차하지 않는 간선만 포함된 MNetwork 객체
    """
    # 1) 육지 폴리곤의 바운딩 박스 추출
    land_polygon_bbox = land_polygon.bounds # (minx, miny, maxx, maxy)
    
    # 2) marnet lineString 추출
    lines = marnet.to_line_string()
    
    edges_to_remove = []
    for line in lines:
        # 바운딩 박스 + prepared_land_polygon 기반 교차 검사
        if not is_valid_edge(line, land_polygon, land_polygon_bbox):
            edges_to_remove.append((line.coords[0], line.coords[1]))
    
    # 3) 한 번에 제거(개별 호출 오버헤드 방지)
    for u, v in edges_to_remove:
        marnet.remove_edge(u=u, v=v)
    
    return marnet
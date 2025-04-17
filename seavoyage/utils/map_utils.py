import geojson
import folium
from seavoyage.classes.m_network import MNetwork

def map_folium(
        data: dict | geojson.FeatureCollection | MNetwork, 
        center: tuple[float, float] = (36.0, 129.5), 
        zoom: int = 7,
        width: str = '100%',
        height: str = '100%',
    ) -> folium.Map:
    """
    folium 지도 객체 생성
    :param data: geojson 데이터, MNetwork 객체, 또는 geojson dict
    :param center: 지도 중심 좌표
    :param zoom: 지도 초기 확대 정도
    :param width: 지도 너비 (예: '800px' 또는 '100%')
    :param height: 지도 높이 (예: '600px' 또는 '100%')
    :return: folium 지도 객체
    """
    m = folium.Map(
        location=center, 
        zoom_start=zoom,
        width=width,
        height=height
    )
    
    if isinstance(data, MNetwork):
        geojson_data = data.to_geojson()
    else:
        geojson_data = data
        
    folium.GeoJson(geojson_data, name="GeoJSON Layer").add_to(m)
    return m

import folium

def map_folium_graph(graph, center=(35.0, 129.0), zoom_start=6):
    """
    MNetwork 그래프를 folium 지도로 시각화합니다.
    
    :param graph: MNetwork 그래프 객체
    :param center: 초기 지도의 중심 (위도, 경도)
    :param zoom_start: 초기 줌 레벨
    :return: folium 지도 객체
    """
    # folium은 (위도, 경도) 순으로 좌표를 받음
    m = folium.Map(location=center, zoom_start=zoom_start)

    # 엣지 그리기
    for u, v, data in graph.edges(data=True):
        # MNetwork에서 노드는 (경도, 위도) 튜플 형태
        lon_u, lat_u = u
        lon_v, lat_v = v
        
        # weight 등 에지 가중치
        weight = data.get('weight', 0)

        # Folium 선(Edge) 그리기: folium은 (위도, 경도) 순으로 locations 작성
        folium.PolyLine(
            locations=[(lat_u, lon_u), (lat_v, lon_v)],
            tooltip=f"거리: {weight:.3f}km",  # 한글로 표시
            color='blue',
            weight=2,
            opacity=0.7
        ).add_to(m)
    
    # 노드 표시 (선택적 - 노드가 많을 경우 성능에 영향을 줄 수 있음)
    # 모든 노드를 표시하는 것이 부담스러운 경우 일부만 표시하거나 이 부분을 주석 처리
    for node in graph.nodes():
        lon, lat = node
        folium.CircleMarker(
            location=(lat, lon),  # folium은 (위도, 경도) 순서
            radius=2,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.7,
            tooltip=f"노드: ({lon:.4f}, {lat:.4f})"
        ).add_to(m)

    return m
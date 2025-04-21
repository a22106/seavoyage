# 빠른 시작


## 1. 기본 경로 생성
```python
import seavoyage as sv

# 출발지와 도착지 좌표 (경도, 위도)
start = (129.17, 35.075)
end = (-4.158, 44.644)

# 기본 해상 네트워크에서 최적 경로 탐색
route = sv.seavoyage(start, end)
print("경로 길이:", route["properties"]["length"], "km")
print("예상 소요 시간:", route["properties"]["duration_hours"], "시간")
```

## 2. 커스텀 제한구역(해역) 적용
```python
# 제한구역 GeoJSON 파일 등록 (예: 'jwc.geojson')
sv.register_custom_restriction('jwc', '/path/to/jwc.geojson')

# 제한구역을 적용하여 경로 탐색
route = sv.seavoyage(start, end, restrictions=['jwc'])
print("제한구역 적용 후 경로 길이:", route["properties"]["length"], "km")
```

## 3. 다양한 해상 네트워크 해상도 사용
### 3.1 미리 설정된 해상 네트워크 사용
```python
# 5km, 10km, 20km, 50km, 100km 네트워크 지원
mnet_5km = sv.get_m_network_5km()
route = sv.seavoyage(start, end, M=mnet_5km)
```

### 3.2 사용자 정의 해상 네트워크 사용
```python
# 사용자 정의 해상 네트워크 생성
mnet = sv.MNetwork().from_geojson('/path/to/mnet.geojson')
route = sv.seavoyage(start, end, M=mnet)
```

### 3.3. 해상 네트워크에 node 추가
```python
# 해상 네트워크에 node 추가 및 edge 자동 연결결
mnet = sv.MNetwork().from_geojson('/path/to/mnet.geojson')
mnet.add_node_and_connect((129.17, 35.075), k=3)
```

## 4. folium 기반 지도 시각화
```python
from seavoyage.utils import map_folium

# folium 지도 객체로 변환
m = map_folium(route)
m.save("route_map.html")
```

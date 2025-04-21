# Sea Voyage

seavoyage는 해상 네트워크 기반의 선박 경로 탐색, 커스텀 제한구역(해역) 적용, 네트워크 시각화 등 다양한 해양 경로 분석 기능을 제공하는 Python 패키지입니다. 이 패키지는 [searoute](https://github.com/genthalili/searoute-py) 패키지를 기반으로 개선되었습니다.

## 원본 프로젝트
- 원본 패키지: [searoute](https://github.com/genthalili/searoute-py)
- 원작자: Gent Halili
- 라이선스: Apache License 2.0

## 주요 기능
- 해상 네트워크 기반 최적 경로 탐색
- 커스텀 제한구역(GeoJSON) 등록 및 적용
- 다양한 해상 네트워크 해상도(5km~100km) 지원
- folium 기반 경로/네트워크 지도 시각화
- 네트워크 및 경로의 GeoJSON 변환

## 설치
```bash
pip install seavoyage
```

## 개발 모드 설치
개발 중에 테스트를 쉽게 실행하려면 다음 명령으로 패키지를 개발 모드로 설치하세요:

```bash
pip install -e .
```

이렇게 하면 `pytest.ps1` 스크립트를 사용하지 않고도 바로 `pytest` 명령을 실행할 수 있습니다.

## 빠른 시작

### 1. 기본 경로 생성
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

### 2. 커스텀 제한구역(해역) 적용
```python
# 제한구역 GeoJSON 파일 등록 (예: 'jwc.geojson')
sv.register_custom_restriction('jwc', '/path/to/jwc.geojson')

# 제한구역을 적용하여 경로 탐색
route = sv.seavoyage(start, end, restrictions=['jwc'])
print("제한구역 적용 후 경로 길이:", route["properties"]["length"], "km")
```

### 3. 다양한 해상 네트워크 해상도 사용
#### 3.1 미리 설정된 해상 네트워크 사용
```python
# 5km, 10km, 20km, 50km, 100km 네트워크 지원
mnet_5km = sv.get_m_network_5km()
route = sv.seavoyage(start, end, M=mnet_5km)
```

#### 3.2 사용자 정의 해상 네트워크 사용
```python
# 사용자 정의 해상 네트워크 생성
mnet = sv.MNetwork().from_geojson('/path/to/mnet.geojson')
route = sv.seavoyage(start, end, M=mnet)
```

### 4. folium 기반 지도 시각화
```python
from seavoyage.utils import map_folium

# folium 지도 객체로 변환
m = map_folium(route)
m.save("route_map.html")
```

## 주요 API
- `seavoyage(start, end, restrictions=None, M=None, ...)`
: 최적 경로 탐색 (제한구역, 네트워크 해상도 등 옵션 지원)
- `MNetwork`
: 해상 네트워크 객체 (노드/엣지 추가, GeoJSON 변환 등 지원)
- `register_custom_restriction(name, geojson_file_path)`
: 커스텀 제한구역 등록
- `list_custom_restrictions()`
: 등록된 제한구역 이름 목록 반환
- `get_custom_restriction(name)`
: 제한구역 객체 반환
- `map_folium(data, ...)`
: folium 기반 지도 시각화

## 라이선스
이 프로젝트는 Apache License 2.0 라이선스 하에 배포됩니다.

```
Copyright 2024 - Gent Halili (원작자)
Copyright 2025 - Byeonggong Hwang

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## 기여
버그 리포트, 기능 제안, 풀 리퀘스트는 언제나 환영합니다.

## 연락처
- 이메일: bk22106@gmail.com
- GitHub: [a22106](https://github.com/a22106)

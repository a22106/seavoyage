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

이 프로젝트는 **uv**를 사용한 현대적인 Python 패키지 관리를 권장합니다:

```bash
# uv를 사용한 개발 환경 설정 (권장)
uv sync
uv pip install -e .

# 또는 기존 pip 방식
pip install -e .
```

### 개발 의존성 설치
```bash
# uv 사용 (권장)
uv sync --group dev --group test --group lint

# 또는 pip 사용
pip install -e ".[dev]"
```

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

## 개선 과제 및 문제점

### 1. 패키지 설정 및 구조 개선
- [x] **Python 버전 지원 불일치**: `pyproject.toml`에서 `requires-python = ">=3.11"`로 설정되어 있으나, classifiers에는 Python 3.9, 3.10도 포함되어 있음. 실제 지원 버전 확인 및 일치 필요
- [x] **개발 의존성 분리 부족**: `requirements.txt`와 `pyproject.toml`에 개발/테스트용 패키지(pytest, ruff, sphinx 등)가 일반 의존성으로 포함됨. `dev-dependencies` 또는 `extras_require` 사용 권장
- [x] **패키지 메타데이터 보완**: `pyproject.toml`에 maintainers, repository, documentation URL 등 추가 정보 필요

### 2. 코드 품질 및 아키텍처
- [x] **타입 힌트 일관성**: 일부 함수에만 타입 힌트가 적용됨. 전체 코드베이스에 일관된 타입 힌트 적용 필요
- [x] **에러 메시지 국제화**: 예외 메시지가 한글로 하드코딩됨. 영어 메시지로 통일 필요
- [x] **전역 상태 관리**: `_DEFAULT_MNETWORK` 같은 전역 변수 사용. 의존성 주입 패턴 고려
- [x] **로깅 레벨 관리**: 로깅 설정이 분산되어 있음. 중앙화된 로깅 설정 필요

### 3. API 설계 개선
- [ ] **함수 시그니처 복잡도**: `seavoyage()` 함수가 너무 많은 매개변수를 가짐. 설정 객체나 빌더 패턴 고려
- [ ] **일관성 없는 네이밍**: `M`, `P` 같은 단일 문자 매개변수명. 더 명확한 이름 사용 필요
- [ ] **반환 타입 명확화**: 함수들이 dict를 반환하는데, 구체적인 타입 정의나 dataclass 사용 권장

### 4. 테스트 및 문서화
- [ ] **테스트 커버리지**: 테스트 커버리지 측정 및 리포트 도구 부재
- [ ] **통합 테스트 부족**: 단위 테스트는 있으나 end-to-end 시나리오 테스트 필요
- [ ] **API 문서화**: Sphinx 설정은 있으나 실제 API 문서가 부족함. docstring 표준화 필요
- [ ] **예제 코드 검증**: README의 예제 코드가 실제로 작동하는지 자동 검증 필요

### 5. 성능 및 최적화
- [ ] **대용량 데이터 처리**: shapefile 등 대용량 지리 데이터를 패키지에 포함. 선택적 다운로드나 캐싱 전략 필요
- [ ] **네트워크 초기화 비용**: 매번 네트워크를 로드하는 비용이 큼. 지연 로딩이나 캐싱 메커니즘 필요
- [ ] **메모리 사용량**: 전체 해상 네트워크를 메모리에 로드. 필요한 부분만 로드하는 최적화 고려

### 6. 사용자 경험 개선
- [ ] **진행 상황 표시**: 긴 경로 계산 시 진행 상황을 표시하는 기능 부재
- [ ] **에러 복구**: 네트워크 오류나 부분적 실패 시 복구 메커니즘 부족
- [ ] **CLI 인터페이스**: 프로그래밍 API만 제공. 간단한 CLI 도구 추가 고려

### 7. 보안 및 유효성 검사
- [ ] **입력 검증 강화**: 좌표 범위 검증, GeoJSON 파일 검증 등 입력 유효성 검사 보강 필요
- [ ] **파일 경로 처리**: 절대/상대 경로 처리가 일관되지 않음. pathlib 사용 권장
- [ ] **의존성 보안**: 의존성 패키지의 보안 취약점 스캔 자동화 필요

### 8. 배포 및 CI/CD
- [ ] **GitHub Actions 설정**: 자동 테스트, 린팅, 패키지 빌드 파이프라인 구축
- [ ] **버전 관리 자동화**: 수동 버전 업데이트 대신 semantic versioning 도구 사용
- [ ] **변경 로그**: CHANGELOG.md 파일 작성 및 자동 생성 도구 도입
- [ ] **배포 자동화**: PyPI 배포 자동화 스크립트 또는 GitHub Actions 워크플로우

### 9. 코드 구조 개선
- [ ] **모듈 분리**: `base.py`가 너무 많은 책임을 가짐. 기능별로 모듈 분리 필요
- [ ] **순환 의존성**: 일부 모듈 간 순환 import 가능성. 의존성 구조 정리 필요
- [ ] **네임스페이스 정리**: `__all__` 정의가 복잡함. 공개 API 명확화 필요

### 10. 확장성 및 유지보수성
- [ ] **플러그인 시스템**: 커스텀 제한구역 외에도 다른 확장 포인트 제공
- [ ] **버전 호환성**: 이전 버전과의 호환성 정책 및 deprecation 전략 수립
- [ ] **커뮤니티 가이드라인**: CONTRIBUTING.md, CODE_OF_CONDUCT.md 등 커뮤니티 문서 작성

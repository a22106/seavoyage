from pathlib import Path
import os

# 패키지 루트 디렉토리 설정
PACKAGE_ROOT = Path(__file__).parent  # settings.py의 부모 디렉토리(seavoyage)를 루트로 설정

# 개발 환경과 설치 환경에서 모두 작동하도록 데이터 디렉토리 설정
if os.environ.get("DEVELOPMENT_MODE"):
    DATA_DIR = PACKAGE_ROOT / 'data'
else:
    # 설치된 패키지의 데이터 디렉토리
    DATA_DIR = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))

# 데이터 디렉토리가 존재하지 않으면 생성
DATA_DIR.mkdir(parents=True, exist_ok=True)

MARNET_DIR = DATA_DIR / 'geojson/marnet'
MARNET_DIR.mkdir(parents=True, exist_ok=True) 

RESTRICTIONS_DIR = DATA_DIR / 'geojson/restrictions'
RESTRICTIONS_DIR.mkdir(parents=True, exist_ok=True) 

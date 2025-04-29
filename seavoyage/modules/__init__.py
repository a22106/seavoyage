"""
seavoyage 추가 모듈
"""
try:
    # 패키지 내부에서 임포트할 때 사용되는 상대 경로
    from .restriction import *
except ImportError:
    # 외부에서 패키지를 임포트할 때 사용되는 절대 경로
    from seavoyage.modules.restriction import *

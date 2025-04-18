import logging
import os

# 로그 레벨을 환경변수로 조정 (기본값: INFO)
log_level = os.environ.get("SEAVOYAGE_LOG_LEVEL", "INFO").upper()

# 로그 포맷 설정
log_format = "[%(asctime)s][%(levelname)s][%(module)s] %(message)s"
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format
)

# seavoyage 전용 logger 객체
logger = logging.getLogger("seavoyage") 
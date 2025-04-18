from pathlib import Path
from seavoyage.settings import RESTRICTIONS_DIR

def _get_restriction_path(file_name: str) -> str:
    return str(RESTRICTIONS_DIR / file_name)


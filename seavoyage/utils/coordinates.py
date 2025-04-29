from typing import List

def decdeg_to_degmin(coord: List[float]) -> List[str]:
    """
    위·경도(10진수, [lat, lon])를 "[59°10.669N, 24°32.256E]" 형식의 list[str]로 변환한다.
    - 소수점 이하 3자리 분까지 출력.
    """
    if len(coord) != 2:
        raise ValueError("coord는 [위도(lat), 경도(lon)] 두 값이어야 합니다.")

    def _one(value: float, is_lat: bool) -> str:
        hemispheres = ('N', 'S') if is_lat else ('E', 'W')
        hemi = hemispheres[0] if value >= 0 else hemispheres[1]

        abs_val = abs(value)
        deg = int(abs_val)
        minutes = (abs_val - deg) * 60

        # 59°10.669N 처럼 출력
        return f"{deg}°{minutes:06.3f}{hemi}"

    lat, lon = coord
    return [_one(lat, True), _one(lon, False)]

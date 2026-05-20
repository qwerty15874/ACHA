# src/classifier.py
# 전압값 → 수분 단계 (0/1/2) 판정

from config.settings import THRESH_DRY, THRESH_WET


def classify(voltage: float) -> int:
    """
    전압값을 수분 단계로 변환

    Args:
        voltage: ADS1115 측정 전압 (V)

    Returns:
        0 — 건조  (V >= THRESH_DRY)
        1 — 수막  (THRESH_WET < V < THRESH_DRY)
        2 — 고임  (V <= THRESH_WET)
    """
    if voltage >= THRESH_DRY:
        return 0
    elif voltage <= THRESH_WET:
        return 2
    else:
        return 1


def classify_all(sensor_data: dict) -> dict:
    """
    read_all() 결과를 받아 각 블록의 수분 단계 반환

    Args:
        sensor_data: MoistureSensor.read_all() 반환값

    Returns:
        {채널번호: {"block": str, "voltage": float, "level": int}}
    """
    classified = {}
    for ch_idx, data in sensor_data.items():
        classified[ch_idx] = {
            **data,
            "level": classify(data["voltage"]),
        }
    return classified

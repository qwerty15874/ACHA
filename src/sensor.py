# src/sensor.py
# ADS1115 읽기 — 타일당 ADS1115 1개, A0 채널 사용
# ACTIVE_CHANNELS에 해당하는 타일만 초기화

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from config.settings import (
    ADS1115_ADDRESSES,
    ADS1115_GAIN,
    ACTIVE_CHANNELS,
    CHANNEL_MAP,
)

# gain → 풀스케일 전압
_GAIN_VOLTAGE = {1: 4.096, 2: 2.048, 4: 1.024, 8: 0.512, 16: 0.256}
_FULL_SCALE = 32767
_AVG_SAMPLES = 8   # 노이즈 평균화


class MoistureSensor:
    """ACTIVE_CHANNELS 타일의 ADS1115 A0 채널 읽기"""

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self._vref = _GAIN_VOLTAGE.get(ADS1115_GAIN, 4.096)

        # 타일별로 별도 ADS1115 인스턴스 생성
        self._channels = {}
        for tile in ACTIVE_CHANNELS:
            addr = ADS1115_ADDRESSES[tile]
            ads = ADS.ADS1115(i2c, address=addr)
            ads.gain = ADS1115_GAIN
            self._channels[tile] = AnalogIn(ads, 0)   # A0 고정

    def read_all(self) -> dict:
        """
        반환: {타일번호: {"block": str, "voltage": float, "raw": int}}
        """
        result = {}
        for tile, chan in self._channels.items():
            raw = sum(chan.value for _ in range(_AVG_SAMPLES)) // _AVG_SAMPLES
            result[tile] = {
                "block": CHANNEL_MAP.get(tile, f"타일{tile+1}"),
                "voltage": raw * self._vref / _FULL_SCALE,
                "raw": raw,
            }
        return result

    def read_channel(self, tile: int) -> float:
        if tile not in self._channels:
            raise ValueError(f"타일 {tile}은 ACTIVE_CHANNELS에 없음: {list(self._channels)}")
        raw = sum(self._channels[tile].value for _ in range(_AVG_SAMPLES)) // _AVG_SAMPLES
        return raw * self._vref / _FULL_SCALE

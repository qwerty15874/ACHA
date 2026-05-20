# src/sensor.py
# ADS1115 I2C ADC 읽기
# 블록당 1채널, 4블록 = 4채널 (A0~A3)

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from config.settings import (
    ADS1115_I2C_ADDRESS,
    ADS1115_GAIN,
    CHANNEL_MAP,
)

# ADS1115 채널 상수
_ADS_CHANNELS = [ADS.P0, ADS.P1, ADS.P2, ADS.P3]


class MoistureSensor:
    """ADS1115를 통해 4블록 수분 전압값 읽기"""

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self._ads = ADS.ADS1115(i2c, address=ADS1115_I2C_ADDRESS)
        self._ads.gain = ADS1115_GAIN

        # 채널별 AnalogIn 객체 생성 (단일 모드, GND 기준)
        self._channels = [
            AnalogIn(self._ads, ch) for ch in _ADS_CHANNELS
        ]

    def read_all(self) -> dict:
        """
        4개 채널 전압값 반환
        반환: {채널번호: {"block": 이름, "voltage": float}}
        """
        result = {}
        for ch_idx, channel in enumerate(self._channels):
            result[ch_idx] = {
                "block": CHANNEL_MAP.get(ch_idx, f"블록{ch_idx+1}"),
                "voltage": channel.voltage,
                "raw": channel.value,
            }
        return result

    def read_channel(self, ch_idx: int) -> float:
        """단일 채널 전압값 반환 (V)"""
        if ch_idx < 0 or ch_idx > 3:
            raise ValueError(f"채널은 0~3 범위여야 함, 입력값: {ch_idx}")
        return self._channels[ch_idx].voltage

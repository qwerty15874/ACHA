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
    ACTIVE_CHANNELS,
    CHANNEL_MAP,
)

# gain=1 → ±4.096V 풀스케일, 16bit 부호있음
_GAIN_VOLTAGE = {1: 4.096, 2: 2.048, 4: 1.024, 8: 0.512, 16: 0.256}
_FULL_SCALE = 32767
_AVG_SAMPLES = 8  # 노이즈 평균화 샘플 수

class MoistureSensor:
    """ADS1115를 통해 ACTIVE_CHANNELS 수분 전압값 읽기"""

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self._ads = ADS.ADS1115(i2c, address=ADS1115_I2C_ADDRESS)
        self._ads.gain = ADS1115_GAIN

        # ACTIVE_CHANNELS에 해당하는 채널만 초기화 (단일 모드, GND 기준)
        self._channels = {
            ch: AnalogIn(self._ads, ch)
            for ch in ACTIVE_CHANNELS
        }

    def read_all(self) -> dict:
        """
        ACTIVE_CHANNELS 전압값 반환
        반환: {채널번호: {"block": 이름, "voltage": float, "raw": int}}
        """
        vref = _GAIN_VOLTAGE.get(ADS1115_GAIN, 4.096)
        result = {}
        for ch, chan in self._channels.items():
            raw = sum(chan.value for _ in range(_AVG_SAMPLES)) // _AVG_SAMPLES
            voltage = raw * vref / _FULL_SCALE
            result[ch] = {
                "block": CHANNEL_MAP.get(ch, f"블록{ch+1}"),
                "voltage": voltage,
                "raw": raw,
            }
        return result

    def read_channel(self, ch_idx: int) -> float:
        """단일 채널 전압값 반환 (V)"""
        if ch_idx not in self._channels:
            raise ValueError(f"채널 {ch_idx}는 ACTIVE_CHANNELS에 없음: {list(self._channels)}")
        vref = _GAIN_VOLTAGE.get(ADS1115_GAIN, 4.096)
        chan = self._channels[ch_idx]
        raw = sum(chan.value for _ in range(_AVG_SAMPLES)) // _AVG_SAMPLES
        return raw * vref / _FULL_SCALE

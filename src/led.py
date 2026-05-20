# src/led.py
# WS2812B LED Strip 제어
# 블록별로 색상 동시 업데이트

from rpi_ws281x import PixelStrip, Color

from config.settings import (
    LED_DATA_PIN,
    LED_COUNT,
    LED_COUNT_PER_BLOCK,
    LED_FREQ_HZ,
    LED_DMA,
    LED_INVERT,
    LED_CHANNEL,
    LED_BRIGHTNESS,
    LED_COLOR,
)


class LEDController:
    """WS2812B 스트립 블록별 색상 제어"""

    def __init__(self):
        self._strip = PixelStrip(
            LED_COUNT,
            LED_DATA_PIN,
            LED_FREQ_HZ,
            LED_DMA,
            LED_INVERT,
            LED_BRIGHTNESS,
            LED_CHANNEL,
        )
        self._strip.begin()

    def set_block(self, block_idx: int, level: int):
        """
        특정 블록의 LED 색상을 수분 단계에 맞게 설정
        (strip.show()는 호출하지 않음 — update_all에서 일괄 호출)

        Args:
            block_idx: 블록 인덱스 (0~3, CHANNEL_MAP 채널번호와 동일)
            level: 수분 단계 (0/1/2)
        """
        r, g, b = LED_COLOR.get(level, (0, 0, 0))
        color = Color(r, g, b)
        start = block_idx * LED_COUNT_PER_BLOCK
        end = start + LED_COUNT_PER_BLOCK
        for i in range(start, end):
            self._strip.setPixelColor(i, color)

    def update_all(self, classified_data: dict):
        """
        classifier.classify_all() 결과를 받아 전체 LED 일괄 업데이트

        Args:
            classified_data: {ch_idx: {"level": int, ...}}
        """
        for ch_idx, data in classified_data.items():
            self.set_block(ch_idx, data["level"])
        self._strip.show()

    def clear(self):
        """전체 LED 소등"""
        for i in range(LED_COUNT):
            self._strip.setPixelColor(i, Color(0, 0, 0))
        self._strip.show()

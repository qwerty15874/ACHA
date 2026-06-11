# src/led.py
# 비주소형 RGB LED Strip 제어 (공통 양극, 5V+R+G+B 4선)
# GPIO PWM으로 R/G/B 각 채널 제어

import RPi.GPIO as GPIO

from config.settings import (
    LED_PIN_R,
    LED_PIN_G,
    LED_PIN_B,
    LED_PWM_FREQ,
    LED_BRIGHTNESS,
    LED_COLOR,
    ACTIVE_CHANNELS,
)


class LEDController:
    """비주소형 RGB 스트립 — 수분 단계에 따라 색상 출력"""

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        for pin in (LED_PIN_R, LED_PIN_G, LED_PIN_B):
            GPIO.setup(pin, GPIO.OUT)

        self._r = GPIO.PWM(LED_PIN_R, LED_PWM_FREQ)
        self._g = GPIO.PWM(LED_PIN_G, LED_PWM_FREQ)
        self._b = GPIO.PWM(LED_PIN_B, LED_PWM_FREQ)

        for pwm in (self._r, self._g, self._b):
            pwm.start(0)

    def set_color(self, r: int, g: int, b: int):
        """r, g, b: 0~255. LED_BRIGHTNESS로 전체 스케일 조정."""
        scale = LED_BRIGHTNESS / 255
        self._r.ChangeDutyCycle(r * scale / 255 * 100)
        self._g.ChangeDutyCycle(g * scale / 255 * 100)
        self._b.ChangeDutyCycle(b * scale / 255 * 100)

    def update_all(self, classified_data: dict):
        """classify_all() 결과를 받아 LED 색상 업데이트.
        단일 타일 PoC: ACTIVE_CHANNELS[0]의 단계를 사용."""
        ch = ACTIVE_CHANNELS[0]
        level = classified_data[ch]["level"]
        r, g, b = LED_COLOR.get(level, (0, 0, 0))
        self.set_color(r, g, b)

    def clear(self):
        """LED 소등"""
        self.set_color(0, 0, 0)

    def cleanup(self):
        self.clear()
        GPIO.cleanup()

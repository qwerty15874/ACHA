# src/main.py
# CPD 타일 낙상방지 시스템 — 진입점
# 실행: sudo python src/main.py  (WS2812B DMA 사용으로 sudo 필요)

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import signal

from sensor import MoistureSensor
from classifier import classify_all
from led import LEDController
from config.settings import POLL_INTERVAL_SEC, ACTIVE_CHANNELS, CHANNEL_MAP

# ----------------------------------------------------------
# 종료 처리 (Ctrl+C → LED 소등 후 종료)
# ----------------------------------------------------------
_led = None

def _shutdown(sig, frame):
    print("\n[종료] LED 소등 중...")
    if _led:
        _led.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

# ----------------------------------------------------------
# 메인 루프
# ----------------------------------------------------------
_LEVEL_LABEL = {0: "건조 ", 1: "수막 ⚠", 2: "고임 🚨"}

def main():
    global _led

    print("[시작] CPD 타일 수분감지 시스템")
    print(f"       활성 블록  : {[CHANNEL_MAP.get(ch, f'블록{ch+1}') for ch in ACTIVE_CHANNELS]}")
    print(f"       폴링 주기  : {POLL_INTERVAL_SEC}초")
    print(f"       종료      : Ctrl+C\n")

    sensor = MoistureSensor()
    _led = LEDController()

    while True:
        raw_data = sensor.read_all()
        classified = classify_all(raw_data)

        # 콘솔 출력 (디버그)
        parts = []
        for ch, d in classified.items():
            parts.append(
                f"{d['block']}: {d['voltage']:.3f}V → {_LEVEL_LABEL[d['level']]}"
            )
        print(" | ".join(parts))

        # LED 업데이트
        _led.update_all(classified)

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()

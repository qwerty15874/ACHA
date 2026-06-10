# planB/control.py
# Firebase 연동 통합 제어 루프
# 실행: sudo python planB/control.py
#
# src/main.py 와 차이:
#   - 센서 데이터를 Firebase RTDB에 push
#   - Firebase에서 원격 명령(밝기, LED 강제 단계) 수신 → 반영

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import signal

from src.sensor import MoistureSensor
from src.classifier import classify_all
from src.led import LEDController
from src.firebase_client import FirebaseClient
from config.settings import POLL_INTERVAL_SEC, CHANNEL_MAP

# ── 전역 상태 ─────────────────────────────────────────────────────
_led:      LEDController | None = None
_firebase: FirebaseClient | None = None

# 원격 명령 캐시 (command listener 콜백이 덮어씀)
_commands = {
    "brightness":    128,
    "led_override":  None,
    "alert_enabled": True,
}

_LEVEL_LABEL = {0: "건조 ", 1: "수막 ⚠", 2: "고임 🚨"}


# ── 종료 처리 ─────────────────────────────────────────────────────
def _shutdown(sig, frame):
    print("\n[종료] 정리 중...")
    if _led:
        _led.clear()
    if _firebase:
        _firebase.close()
    sys.exit(0)

signal.signal(signal.SIGINT,  _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ── 명령 수신 콜백 ────────────────────────────────────────────────
def _on_commands(commands: dict) -> None:
    global _commands
    _commands.update(commands)

    # 밝기 즉시 반영
    if _led and "brightness" in commands:
        _led.set_brightness(int(commands["brightness"]))

    print(f"[원격 명령] {commands}")


# ── 메인 루프 ─────────────────────────────────────────────────────
def main() -> None:
    global _led, _firebase

    print("[시작] CPD 타일 수분감지 시스템 (Firebase 연동)")
    print(f"       폴링 주기: {POLL_INTERVAL_SEC}초  |  종료: Ctrl+C\n")

    sensor    = MoistureSensor()
    _led      = LEDController()
    _firebase = FirebaseClient()
    _firebase.start_command_listener(_on_commands)

    while True:
        raw_data   = sensor.read_all()
        classified = classify_all(raw_data)

        # LED 업데이트 (원격 강제 단계 반영)
        override = _commands.get("led_override")
        if override is not None:
            _led.set_all(int(override))
        else:
            _led.update_all(classified)

        # Firebase push
        _firebase.push_status(classified)

        # 콘솔 출력
        parts = [
            f"{d['block']}: {d['voltage']:.3f}V → {_LEVEL_LABEL[d['level']]}"
            for d in classified.values()
        ]
        print(" | ".join(parts))

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()

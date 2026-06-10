# src/firebase_client.py
# Firebase Realtime Database 연동 — 센서 데이터 push / 명령 수신
#
# 전제:
#   config/serviceAccountKey.json  — Firebase 콘솔 > 프로젝트 설정 > 서비스 계정 > 새 비공개 키 생성
#   config/settings.py             — FIREBASE_DB_URL 설정 완료

import time
import threading
from typing import Callable

import firebase_admin
from firebase_admin import credentials, db

from config.settings import (
    FIREBASE_CRED_PATH,
    FIREBASE_DB_URL,
    FIREBASE_PATH_STATUS,
    FIREBASE_PATH_COMMANDS,
)


class FirebaseClient:
    """Firebase RTDB 연결, 센서 상태 push, 원격 명령 수신"""

    def __init__(self) -> None:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CRED_PATH)
            firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

        self._status_ref   = db.reference(FIREBASE_PATH_STATUS)
        self._commands_ref = db.reference(FIREBASE_PATH_COMMANDS)
        self._listener     = None

        # 초기 명령 기본값 설정 (없으면 생성)
        if self._commands_ref.get() is None:
            self._commands_ref.set(_default_commands())

    # ── 센서 데이터 push ────────────────────────────────────────
    def push_status(self, classified: dict) -> None:
        """
        classify_all() 결과를 RTDB에 기록.
        classified: {ch_idx: {block, voltage, raw, level}}
        """
        blocks = {}
        for ch, data in classified.items():
            blocks[str(ch)] = {
                "block":   data["block"],
                "voltage": round(data["voltage"], 4),
                "raw":     data["raw"],
                "level":   data["level"],
            }
        self._status_ref.set({
            "blocks":     blocks,
            "updated_at": int(time.time()),
        })

    # ── 원격 명령 수신 ──────────────────────────────────────────
    def start_command_listener(self, callback: Callable[[dict], None]) -> None:
        """
        RTDB commands 노드 변경을 실시간 수신.
        callback(commands: dict) 호출됨.
        별도 스레드에서 동작 — main 루프를 블로킹하지 않음.
        """
        def _on_change(event):
            if event.data:
                callback(event.data)

        self._listener = self._commands_ref.listen(_on_change)

    def stop_command_listener(self) -> None:
        if self._listener:
            self._listener.close()
            self._listener = None

    def close(self) -> None:
        self.stop_command_listener()


# ── RTDB commands 초기값 ─────────────────────────────────────────
def _default_commands() -> dict:
    return {
        "brightness":    128,   # LED 밝기 (0~255)
        "led_override":  None,  # None = 자동 / 0|1|2 = 강제 단계
        "alert_enabled": True,  # 원격 알림 활성화 여부
    }

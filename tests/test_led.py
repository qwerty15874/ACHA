# tests/test_led.py
# WS2812B LED 동작 확인 테스트
#
# 사용법:
#   sudo .venv/bin/python tests/test_led.py           # 전체 타일 순서대로
#   sudo .venv/bin/python tests/test_led.py --tile 0  # 특정 타일만
#   sudo .venv/bin/python tests/test_led.py --mode color   # 색상 순환
#   sudo .venv/bin/python tests/test_led.py --mode block   # 블록별 점등
#   sudo .venv/bin/python tests/test_led.py --mode state   # 수분 단계 시연
#
# WS2812B는 DMA 사용으로 sudo 필수

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    CHANNEL_MAP,
    LED_COUNT_PER_BLOCK,
    BLOCK_COUNT,
    LED_COLOR,
)
LED_COUNT = LED_COUNT_PER_BLOCK  # 각 스트립이 독립 — 스트립당 LED 수

try:
    from src.led import LEDController
except ImportError as e:
    sys.exit(
        f"[오류] LED 라이브러리 없음: {e}\n"
        "  pip install adafruit-circuitpython-neopixel\n"
        "  실행: sudo .venv/bin/python tests/test_led.py"
    )

DELAY = 0.5   # 초

# ── 모드: 색상 순환 ───────────────────────────────────────────────
def mode_color(led: LEDController, tiles: list[int]):
    """R→G→B→백→소등 순서로 타일 전체 점등"""
    colors = [
        ("빨강", (255, 0,   0)),
        ("초록", (0,   255, 0)),
        ("파랑", (0,   0,   255)),
        ("백색", (255, 255, 255)),
    ]
    print("[색상 순환] Ctrl+C로 종료")
    try:
        while True:
            for name, (r, g, b) in colors:
                print(f"  → {name}")
                for t in tiles:
                    led.set_block_raw(t, r, g, b)
                led.show()
                time.sleep(DELAY * 2)
            print("  → 소등")
            led.clear()
            time.sleep(DELAY)
    except KeyboardInterrupt:
        pass


# ── 모드: 블록별 순차 점등 ────────────────────────────────────────
TILE_COLORS = [
    (  0, 200,  80),   # 타일1 — 청록
    (200,   0, 200),   # 타일2 — 보라
    (200, 150,   0),   # 타일3 — 황
    (  0, 100, 255),   # 타일4 — 파랑
]

def mode_block(led: LEDController, tiles: list[int]):
    """타일을 하나씩 다른 색으로 점등 → 데이지체인 인덱스 확인용"""
    print("[블록별 점등] 타일을 하나씩 켭니다. Ctrl+C로 종료")
    try:
        while True:
            for t in tiles:
                name = CHANNEL_MAP.get(t, f"타일{t+1}")
                r, g, b = TILE_COLORS[t % len(TILE_COLORS)]
                start = t * LED_COUNT_PER_BLOCK
                print(f"  → {name}  색=RGB({r},{g},{b})  LED #{start}~{start + LED_COUNT_PER_BLOCK - 1}")
                led.clear()
                led.set_block_raw(t, r, g, b)
                led.show()
                time.sleep(DELAY * 3)
            # 마지막: 4타일 동시 점등 (각기 다른 색)
            print("  → 전체 동시 점등")
            for t in tiles:
                r, g, b = TILE_COLORS[t % len(TILE_COLORS)]
                led.set_block_raw(t, r, g, b)
            led.show()
            time.sleep(DELAY * 4)
    except KeyboardInterrupt:
        pass


# ── 모드: 수분 단계 시연 ──────────────────────────────────────────
def mode_state(led: LEDController, tiles: list[int]):
    """건조→수막→고임 색상을 순서대로 시연"""
    states = [
        (0, "건조  (백색)"),
        (1, "수막  (황색)"),
        (2, "고임  (적색)"),
    ]
    print("[수분 단계 시연] Ctrl+C로 종료")
    try:
        while True:
            for level, label in states:
                r, g, b = LED_COLOR[level]
                print(f"  → 단계{level}: {label}  RGB=({r},{g},{b})")
                for t in tiles:
                    led.set_block(t, level)
                led.show()
                time.sleep(DELAY * 3)
    except KeyboardInterrupt:
        pass


# ── 모드: 스캔 (LED 1개씩 점등) ──────────────────────────────────
def mode_scan(led: LEDController, tiles: list[int]):
    """타일별로 LED를 인덱스 0부터 하나씩 켜서 물리 배치 확인."""
    print(f"[스캔] 타일당 {LED_COUNT_PER_BLOCK}개를 1개씩 점등합니다. Ctrl+C로 중단")
    try:
        for t in tiles:
            name = CHANNEL_MAP.get(t, f"타일{t+1}")
            if t not in led.tiles:
                print(f"  [{name}] 초기화 안됨, 건너뜀")
                continue
            print(f"  [{name}]")
            for i in range(LED_COUNT_PER_BLOCK):
                led.set_block_raw(t, 0, 0, 0)
                led.set_pixel(t, i, (0, 180, 80))
                led.show()
                print(f"    LED #{i:3d}", end="\r")
                time.sleep(0.15)
            led.set_block_raw(t, 0, 0, 0)
            led.show()
            print(f"    완료 (0~{LED_COUNT_PER_BLOCK - 1})")
    except KeyboardInterrupt:
        pass


# ── 진입점 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WS2812B LED 테스트")
    parser.add_argument(
        "--tile", type=int, nargs="+",
        choices=list(range(BLOCK_COUNT)),
        default=list(range(BLOCK_COUNT)),   # LED 테스트는 4타일 전체가 기본
        help="테스트할 타일 (기본: 전체 0~3)",
    )
    parser.add_argument(
        "--mode", choices=["color", "block", "state", "scan"], default="block",
        help="테스트 모드 (기본: block) / scan: LED 1개씩 점등해 물리 인덱스 확인",
    )
    args = parser.parse_args()
    tiles = sorted(set(args.tile))

    print(f"[LED 테스트] 타일={[CHANNEL_MAP.get(t, t) for t in tiles]}  모드={args.mode}")
    print(f"  타일당 LED: {LED_COUNT_PER_BLOCK}개  총: {LED_COUNT}개\n")

    led = LEDController()
    led.clear()

    try:
        if args.mode == "color":
            mode_color(led, tiles)
        elif args.mode == "block":
            mode_block(led, tiles)
        elif args.mode == "state":
            mode_state(led, tiles)
        elif args.mode == "scan":
            mode_scan(led, tiles)
    finally:
        led.clear()
        print("\n[종료] LED 소등 완료")

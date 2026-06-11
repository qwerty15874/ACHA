# tests/test_electrode_detection.py
# 전극 간 수분 감지 차이 확인용 테스트
#
# 사용법:
#   python -m tests.test_electrode_detection          # 4채널 전체
#   python -m tests.test_electrode_detection --ch 0   # 특정 채널만
#
# 실행 흐름:
#   1. 건조 상태 기준값(baseline) 자동 측정 (5회 평균)
#   2. 0.5초마다 폴링 → 현재값 / 전압변화량 / 수분단계 출력
#   3. 상태가 바뀌면 (DRY→WET, WET→DRY) 강조 표시
#   Ctrl+C 로 종료

import argparse
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (직접 실행 및 -m 모드 모두 지원)
sys.path.insert(0, str(Path(__file__).parent.parent))

# ADS1115 / board 라이브러리가 없는 환경(비-RPi)에서는 시뮬레이션 모드로 동작
import math
import random

from src.classifier import classify
from config.settings import ACTIVE_CHANNELS, CHANNEL_MAP

try:
    from src.sensor import MoistureSensor
except ImportError as e:
    print(f"[시뮬레이션 모드] 하드웨어 라이브러리 없음: {e}")
    print("  실제 ADS1115 없이 모의 전압값으로 동작합니다.\n")

    class MoistureSensor:
        """RPi 하드웨어 없이 동작하는 시뮬레이션 센서"""
        _t = 0.0

        def read_all(self) -> dict:
            MoistureSensor._t += 0.05
            result = {}
            for ch in ACTIVE_CHANNELS:
                phase = ch * math.pi / 2
                base = 2.05 + 1.25 * math.sin(MoistureSensor._t + phase)
                voltage = round(base + random.uniform(-0.05, 0.05), 4)
                raw = int(voltage / 4.096 * 32767)
                result[ch] = {"voltage": voltage, "raw": raw}
            return result

# ── 상수 ─────────────────────────────────────────────────────────
BASELINE_SAMPLES = 5      # 기준값 측정 횟수
BASELINE_INTERVAL = 0.2   # 기준값 측정 간격 (초)
POLL_INTERVAL = 0.5       # 폴링 주기 (초)
DELTA_WARN = 0.1          # 이 이상 전압 변화 시 "!" 표시 (V)

LEVEL_LABEL = {0: "건조  ", 1: "수막 !", 2: "고임!!"}
LEVEL_SEP   = {0: " ", 1: "*", 2: "▶"}


# ── 기준값 측정 ──────────────────────────────────────────────────
def measure_baseline(sensor: MoistureSensor, channels: list[int]) -> dict[int, float]:
    print(f"\n[기준값 측정] 전극을 건조 상태로 유지하세요. ({BASELINE_SAMPLES}회 평균)")
    totals = {ch: 0.0 for ch in channels}

    for i in range(1, BASELINE_SAMPLES + 1):
        data = sensor.read_all()
        for ch in channels:
            totals[ch] += data[ch]["voltage"]
        print(f"  샘플 {i}/{BASELINE_SAMPLES}", end="\r")
        time.sleep(BASELINE_INTERVAL)

    baselines = {ch: totals[ch] / BASELINE_SAMPLES for ch in channels}
    print("\n[기준값]")
    for ch in channels:
        name = CHANNEL_MAP.get(ch, f"채널{ch}")
        print(f"  {name} (A{ch}): {baselines[ch]:.4f} V")
    return baselines


# ── 헤더 출력 ────────────────────────────────────────────────────
def print_header(channels: list[int]) -> None:
    print()
    print("─" * 72)
    header = f"{'시각':>8}  "
    for ch in channels:
        name = CHANNEL_MAP.get(ch, f"A{ch}")
        header += f"  {name}(A{ch}): V_now / Δ / raw / 단계"
    print(header)
    print("─" * 72)


# ── 한 줄 출력 ───────────────────────────────────────────────────
def format_row(ts: str, data: dict, baselines: dict[int, float], channels: list[int],
               prev_levels: dict[int, int]) -> tuple[str, dict[int, int]]:
    row = f"{ts:>8}  "
    new_levels: dict[int, int] = {}

    for ch in channels:
        v_now = data[ch]["voltage"]
        raw   = data[ch]["raw"]
        delta = v_now - baselines[ch]
        level = classify(v_now)
        new_levels[ch] = level

        changed = (prev_levels.get(ch) is not None) and (level != prev_levels[ch])
        sep = LEVEL_SEP[level]

        flag = " CHANGE" if changed else ""
        row += (
            f"  {sep}{LEVEL_LABEL[level]}{sep} "
            f"{v_now:+.4f}V  Δ{delta:+.4f}  raw={raw:6d}{flag:<8}"
        )

    return row, new_levels


# ── 메인 루프 ────────────────────────────────────────────────────
def run(channels: list[int]) -> None:
    sensor = MoistureSensor()
    baselines = measure_baseline(sensor, channels)
    print_header(channels)

    prev_levels: dict[int, int] = {}
    iteration = 0

    try:
        while True:
            data = sensor.read_all()
            ts = time.strftime("%H:%M:%S")
            row, prev_levels = format_row(ts, data, baselines, channels, prev_levels)
            print(row)

            # 20줄마다 헤더 재출력 (터미널 스크롤 편의)
            iteration += 1
            if iteration % 20 == 0:
                print_header(channels)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[종료] 테스트를 마쳤습니다.")
        _print_summary(baselines, prev_levels, channels)


def _print_summary(baselines: dict, final_levels: dict, channels: list[int]) -> None:
    print("\n[최종 상태]")
    print(f"  {'채널':<8} {'기준(V)':>10} {'현재 단계':>12}")
    print(f"  {'─'*8} {'─'*10} {'─'*12}")
    for ch in channels:
        name = CHANNEL_MAP.get(ch, f"A{ch}")
        level = final_levels.get(ch, -1)
        label = LEVEL_LABEL.get(level, "알 수 없음")
        print(f"  {name:<8} {baselines[ch]:>10.4f} {label:>12}")
    print()


# ── 진입점 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="전극 수분 감지 테스트")
    parser.add_argument(
        "--ch", type=int, nargs="+",
        choices=[0, 1, 2, 3],
        default=ACTIVE_CHANNELS,
        help=f"테스트할 ADS1115 채널 (기본: settings.ACTIVE_CHANNELS = {ACTIVE_CHANNELS})",
    )
    args = parser.parse_args()
    run(sorted(set(args.ch)))

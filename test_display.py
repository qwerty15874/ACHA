# test_display.py
# PC에서 디스플레이 미리보기 — 5초마다 시나리오 전환
# 실행: python test_display.py   (ESC 또는 창 닫기로 종료)

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

from display import DisplayController

# ── 테스트 시나리오 ──────────────────────────────────────────
SCENARIOS = [
    # 1. 전체 건조
    {
        0: {"block": "블록1", "voltage": 3.25, "level": 0},
        1: {"block": "블록2", "voltage": 3.18, "level": 0},
        2: {"block": "블록3", "voltage": 3.30, "level": 0},
        3: {"block": "블록4", "voltage": 3.21, "level": 0},
    },
    # 2. 블록2 수막
    {
        0: {"block": "블록1", "voltage": 3.22, "level": 0},
        1: {"block": "블록2", "voltage": 2.45, "level": 1},
        2: {"block": "블록3", "voltage": 3.14, "level": 0},
        3: {"block": "블록4", "voltage": 3.09, "level": 0},
    },
    # 3. 블록3 고임 + 블록2 수막
    {
        0: {"block": "블록1", "voltage": 3.20, "level": 0},
        1: {"block": "블록2", "voltage": 2.10, "level": 1},
        2: {"block": "블록3", "voltage": 0.98, "level": 2},
        3: {"block": "블록4", "voltage": 3.15, "level": 0},
    },
    # 4. 다중 고임 (블록1, 3, 4)
    {
        0: {"block": "블록1", "voltage": 0.75, "level": 2},
        1: {"block": "블록2", "voltage": 3.10, "level": 0},
        2: {"block": "블록3", "voltage": 1.02, "level": 2},
        3: {"block": "블록4", "voltage": 0.88, "level": 2},
    },
]

SCENARIO_LABELS = [
    "1/4  전체 건조",
    "2/4  블록2 수막",
    "3/4  블록3 고임 + 블록2 수막",
    "4/4  다중 고임 (블록1,3,4)",
]
SCENARIO_DURATION = 5  # 초


def main():
    display = DisplayController()
    idx   = 0
    start = time.time()

    print("테스트 시작 - ESC 또는 창 닫기로 종료")
    print(f"현재 시나리오: {SCENARIO_LABELS[idx]}")

    running = True
    while running:
        if time.time() - start >= SCENARIO_DURATION:
            idx   = (idx + 1) % len(SCENARIOS)
            start = time.time()
            print(f"시나리오 전환 -> {SCENARIO_LABELS[idx]}")

        running = display.update(SCENARIOS[idx])

    display.close()
    print("종료")


if __name__ == "__main__":
    main()

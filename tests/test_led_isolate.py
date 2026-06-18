# tests/test_led_isolate.py
# RPi 5 PIO 단일 자원 문제 진단용
#
# 각 GPIO 핀을 "완전히 분리된 프로세스"에서 하나씩 점등한다.
# 프로세스가 분리되면 PIO 자원 충돌이 없으므로,
# 핀 각각이 단독으로 물리적으로 켜지는지 확인할 수 있다.
#
# 사용법:
#   sudo .venv/bin/python tests/test_led_isolate.py            # 모든 핀 순차(각각 별도 프로세스)
#   sudo .venv/bin/python tests/test_led_isolate.py --pin 22   # 한 핀만 (자식 프로세스 모드)
#
# 결과 해석:
#   - 모든 핀이 단독 실행 시 켜짐  → 배선 정상, 문제는 "한 프로세스 다중 핀" 충돌
#                                    → 데이지체인(단일 GPIO) 방식으로 전환 권장
#   - 단독 실행에도 안 켜지는 핀    → 그 핀은 배선/핀 자체 문제

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LED_PINS, LED_COUNT_PER_BLOCK, LED_BRIGHTNESS

HOLD_SEC = 2.0   # 한 핀 점등 유지 시간


def light_one(bcm: int):
    """자식 프로세스: 이 핀 하나만 초록색으로 점등 후 HOLD_SEC 유지."""
    import board
    import neopixel

    pin = getattr(board, f"D{bcm}")
    strip = neopixel.NeoPixel(
        pin, LED_COUNT_PER_BLOCK,
        brightness=LED_BRIGHTNESS, auto_write=False,
        pixel_order=neopixel.GRB,
    )
    strip.fill((0, 200, 80))
    strip.show()
    time.sleep(HOLD_SEC)
    strip.fill((0, 0, 0))
    strip.show()


def run_all():
    """부모 프로세스: 핀마다 자식 프로세스를 새로 띄워 단독 점등."""
    print(f"[격리 테스트] 각 핀을 별도 프로세스로 단독 점등 (유지 {HOLD_SEC}s)")
    print(f"  대상 핀: {sorted(set(LED_PINS.values()))}\n")
    for tile, bcm in LED_PINS.items():
        print(f"  → 타일{tile}  GPIO{bcm}  점등 중... (눈으로 확인)")
        r = subprocess.run(
            [sys.executable, __file__, "--pin", str(bcm)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"     실패: {r.stderr.strip()}")
        else:
            print(f"     완료")
    print("\n[종료] 어떤 핀이 실제로 켜졌는지 알려주세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LED 핀 격리 진단")
    parser.add_argument("--pin", type=int, default=None,
                        help="내부용: 이 BCM 핀 하나만 점등 (자식 프로세스)")
    args = parser.parse_args()

    if args.pin is not None:
        light_one(args.pin)
    else:
        run_all()

# src/led.py
# WS2812B LED 제어 — RPi 5 (RP1 PIO) 대응
#
# 두 가지 배선 모드를 지원 (config.settings.LED_WIRING):
#   "separate" : 타일마다 독립 GPIO 데이터선. 타일별 NeoPixel 인스턴스.
#   "chain"    : 전 타일 데이지체인(1선). 단일 NeoPixel(전체 LED), 인덱스 범위로 타일 분할.
#
# RPi 5의 PIO 자원은 한 번에 1개만 점유되므로, separate 모드에서는
# show() 시 타일을 "하나씩 순차" 출력한다. chain 모드는 자원을 1개만
# 쓰므로 가장 안정적이다.

import board
import neopixel

from config.settings import (
    LED_WIRING,
    LED_PINS,
    LED_CHAIN_PIN,
    LED_COUNT_PER_BLOCK,
    BLOCK_COUNT,
    LED_BRIGHTNESS,
    LED_COLOR,
)

_PIXEL_ORDER = neopixel.GRB
_OFF = (0, 0, 0)


def _board_pin(bcm: int):
    """BCM 번호 → board.Dxx 핀 객체."""
    name = f"D{bcm}"
    if not hasattr(board, name):
        raise ValueError(f"board에 {name} 핀이 없음 (BCM{bcm})")
    return getattr(board, name)


class LEDController:
    """수분 단계 색상으로 타일별 LED를 제어.

    내부적으로 타일별 RGB 버퍼를 들고 있다가 show() 때 하드웨어에 반영한다.
    배선 모드에 따라 출력 경로만 달라지고, 외부 API(set_block / update_all 등)는 동일.
    """

    def __init__(self):
        self.mode = LED_WIRING
        # 타일 → (strip 객체, 버퍼 시작 인덱스)
        self._tiles: dict[int, tuple[neopixel.NeoPixel, int]] = {}
        # show()에서 갱신할 모든 strip 객체
        self._strip_objs: list[neopixel.NeoPixel] = []

        if self.mode == "chain":
            self._init_chain()
        else:
            self._init_separate()

        if not self._tiles:
            raise RuntimeError(
                "LED 스트립이 하나도 초기화되지 않았습니다. "
                "settings.LED_WIRING / LED_PINS / LED_CHAIN_PIN 확인."
            )
        self.clear()

    # ── 초기화 ───────────────────────────────────────────────
    def _init_separate(self):
        """타일마다 독립 GPIO + 독립 NeoPixel 인스턴스."""
        for tile, bcm in LED_PINS.items():
            try:
                pin = _board_pin(bcm)
                strip = neopixel.NeoPixel(
                    pin,
                    LED_COUNT_PER_BLOCK,
                    brightness=LED_BRIGHTNESS,
                    auto_write=False,
                    pixel_order=_PIXEL_ORDER,
                )
            except Exception as e:  # 한 타일 실패가 전체를 막지 않도록
                print(f"[LED] 타일{tile} GPIO{bcm} 초기화 실패: {type(e).__name__}: {e}")
                continue
            self._tiles[tile] = (strip, 0)   # 독립 스트립이라 시작 인덱스 0
            self._strip_objs.append(strip)
            print(f"[LED] 타일{tile} ← GPIO{bcm} (LED {LED_COUNT_PER_BLOCK}개) OK")

    def _init_chain(self):
        """데이지체인 1선: 단일 NeoPixel을 인덱스 범위로 타일 분할."""
        total = LED_COUNT_PER_BLOCK * BLOCK_COUNT
        pin = _board_pin(LED_CHAIN_PIN)
        strip = neopixel.NeoPixel(
            pin,
            total,
            brightness=LED_BRIGHTNESS,
            auto_write=False,
            pixel_order=_PIXEL_ORDER,
        )
        self._strip_objs.append(strip)
        for tile in range(BLOCK_COUNT):
            start = tile * LED_COUNT_PER_BLOCK
            self._tiles[tile] = (strip, start)
        print(
            f"[LED] 데이지체인 GPIO{LED_CHAIN_PIN} ← 총 {total}개 "
            f"(타일당 {LED_COUNT_PER_BLOCK}개)"
        )

    # ── 버퍼 쓰기 (show 전까지 하드웨어 미반영) ────────────────
    def _fill_tile(self, tile: int, color: tuple[int, int, int]):
        entry = self._tiles.get(tile)
        if entry is None:
            return False
        strip, start = entry
        for i in range(start, start + LED_COUNT_PER_BLOCK):
            strip[i] = color
        return True

    def set_block(self, tile: int, level: int):
        """타일을 수분 단계 색상으로 설정 (show() 전까지 버퍼만)."""
        self._fill_tile(tile, LED_COLOR.get(level, _OFF))

    def set_block_raw(self, tile: int, r: int, g: int, b: int):
        """타일을 직접 RGB로 설정 (테스트용)."""
        self._fill_tile(tile, (r, g, b))

    # ── 하드웨어 반영 ─────────────────────────────────────────
    def show(self):
        """버퍼를 하드웨어로 출력.

        separate 모드는 strip 객체가 여러 개이므로 순차 출력한다.
        (RP1 PIO 자원을 한 번에 하나씩만 점유 → 순차가 안전)
        """
        for strip in self._strip_objs:
            try:
                strip.show()
            except Exception as e:
                print(f"[LED] show 실패: {type(e).__name__}: {e}")

    def update_all(self, classified_data: dict):
        """classify_all() 결과로 활성 타일 LED 일괄 갱신."""
        for tile, data in classified_data.items():
            self.set_block(tile, data["level"])
        self.show()

    def clear(self):
        for strip in self._strip_objs:
            strip.fill(_OFF)
        self.show()

    def cleanup(self):
        self.clear()

    # ── 진단/테스트 보조 ──────────────────────────────────────
    @property
    def tiles(self) -> list[int]:
        """초기화에 성공한 타일 목록."""
        return sorted(self._tiles)

    def set_pixel(self, tile: int, idx: int, color: tuple[int, int, int]):
        """타일 내 특정 LED 1개만 설정 (스캔 테스트용). idx: 0 ~ LED_COUNT_PER_BLOCK-1."""
        entry = self._tiles.get(tile)
        if entry is None or not (0 <= idx < LED_COUNT_PER_BLOCK):
            return
        strip, start = entry
        strip[start + idx] = color

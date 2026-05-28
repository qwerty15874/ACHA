# src/display.py
# RPi 7" Touch Display (DSI 800x480) 상태판

import os
import sys
import time

import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
    DISPLAY_FPS,
    DISPLAY_FULLSCREEN,
)

# ── 색상 팔레트 ──────────────────────────────────────────────
_BG_MAIN    = (15,  15,  20)
_BG_HEADER  = (25,  25,  38)
_BG_DIVIDER = (50,  50,  72)

_LEVEL_BG = {
    0: (18,  40,  18),
    1: (42,  36,   0),
    2: (55,   5,   5),
}
_LEVEL_FG = {
    0: (160, 255, 160),
    1: (255, 220,  50),
    2: (255,  80,  80),
}
_LEVEL_LABEL = {
    0: "건  조",
    1: "수  막  !",
    2: "고  임  !!",
}

_HEADER_H = 60
_BANNER_H = 80


def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
    candidates = [
        "malgun gothic",     # Windows
        "gulim",             # Windows 폴백
        "noto sans cjk kr",  # Linux / RPi
        "nanum gothic",      # Linux 폴백
        "notosanscjk",
        "dejavu sans",
    ]
    for name in candidates:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


class DisplayController:
    def __init__(self):
        pygame.init()
        flags = pygame.FULLSCREEN if DISPLAY_FULLSCREEN else 0
        self._screen = pygame.display.set_mode(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT), flags
        )
        pygame.display.set_caption("CPD 타일 수분감지 시스템")
        self._clock = pygame.time.Clock()

        self._font_title  = _load_font(26, bold=True)
        self._font_status = _load_font(46, bold=True)
        self._font_sub    = _load_font(22)
        self._font_volt   = _load_font(20)
        self._font_banner = _load_font(28, bold=True)

        self._blink_on   = True
        self._blink_tick = 0

    def update(self, classified_data: dict) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False

        self._blink_tick += 1
        if self._blink_tick >= DISPLAY_FPS // 2:
            self._blink_on   = not self._blink_on
            self._blink_tick = 0

        self._screen.fill(_BG_MAIN)
        self._draw_header()
        self._draw_grid(classified_data)
        self._draw_banner(classified_data)
        pygame.display.flip()
        self._clock.tick(DISPLAY_FPS)
        return True

    def close(self):
        pygame.quit()

    # ── 내부 그리기 함수 ──────────────────────────────────────

    def _draw_header(self):
        pygame.draw.rect(self._screen, _BG_HEADER,
                         (0, 0, DISPLAY_WIDTH, _HEADER_H))

        title = self._font_title.render(
            "CPD 타일 수분감지 시스템", True, (200, 210, 255)
        )
        self._screen.blit(title, (20, (_HEADER_H - title.get_height()) // 2))

        clock_str = time.strftime("%H:%M:%S")
        clock_surf = self._font_sub.render(clock_str, True, (130, 130, 155))
        self._screen.blit(
            clock_surf,
            (DISPLAY_WIDTH - clock_surf.get_width() - 20,
             (_HEADER_H - clock_surf.get_height()) // 2),
        )

        pygame.draw.line(self._screen, _BG_DIVIDER,
                         (0, _HEADER_H), (DISPLAY_WIDTH, _HEADER_H), 1)

    def _draw_grid(self, data: dict):
        grid_y = _HEADER_H
        grid_h = DISPLAY_HEIGHT - _HEADER_H - _BANNER_H
        cell_w = DISPLAY_WIDTH  // 2
        cell_h = grid_h         // 2

        # 채널 0~3 → 2×2 배치
        positions = {
            0: (0,      grid_y),
            1: (cell_w, grid_y),
            2: (0,      grid_y + cell_h),
            3: (cell_w, grid_y + cell_h),
        }

        for ch, (x, y) in positions.items():
            d = data.get(ch, {"block": f"블록{ch+1}", "voltage": 0.0, "level": 0})
            self._draw_block(pygame.Rect(x, y, cell_w, cell_h),
                             d["block"], d["level"], d["voltage"])

        # 격자 구분선
        mid_x = DISPLAY_WIDTH  // 2
        mid_y = grid_y + grid_h // 2
        pygame.draw.line(self._screen, _BG_DIVIDER,
                         (mid_x, grid_y), (mid_x, grid_y + grid_h), 2)
        pygame.draw.line(self._screen, _BG_DIVIDER,
                         (0, mid_y), (DISPLAY_WIDTH, mid_y), 2)

    def _draw_block(self, rect: pygame.Rect,
                    block_name: str, level: int, voltage: float):
        bg = _LEVEL_BG[level]
        fg = _LEVEL_FG[level]

        pygame.draw.rect(self._screen, bg, rect)

        # 고임 단계 — 테두리 깜빡임
        if level == 2 and self._blink_on:
            pygame.draw.rect(self._screen, fg, rect, 3)

        pad = 16
        cy  = rect.y + rect.height // 2

        # 블록 이름
        name_surf = self._font_sub.render(block_name, True, (150, 150, 175))
        self._screen.blit(name_surf, (rect.x + pad, rect.y + pad))

        # 수분 단계 라벨 (중앙)
        label_surf = self._font_status.render(_LEVEL_LABEL[level], True, fg)
        self._screen.blit(
            label_surf,
            (rect.x + (rect.width  - label_surf.get_width())  // 2,
             cy - label_surf.get_height() // 2 - 6),
        )

        # 전압값 (우하단)
        volt_surf = self._font_volt.render(f"{voltage:.3f} V", True, (140, 140, 165))
        self._screen.blit(
            volt_surf,
            (rect.x + rect.width - volt_surf.get_width() - pad,
             rect.y + rect.height - volt_surf.get_height() - pad),
        )

    def _draw_banner(self, data: dict):
        y         = DISPLAY_HEIGHT - _BANNER_H
        max_level = max((d["level"] for d in data.values()), default=0)

        if max_level == 2:
            bg  = (80, 0, 0) if self._blink_on else (48, 0, 0)
            fg  = (255, 110, 110)
            msg = "위험  —  " + ", ".join(
                d["block"] for d in data.values() if d["level"] == 2
            ) + " : 물이 고여 있습니다"
        elif max_level == 1:
            bg  = (50, 40, 0)
            fg  = (255, 220, 50)
            msg = "주의  —  " + ", ".join(
                d["block"] for d in data.values() if d["level"] == 1
            ) + " : 수분이 감지되었습니다"
        else:
            bg  = (18, 32, 18)
            fg  = (100, 200, 100)
            msg = "정상  —  모든 구역 건조 상태"

        pygame.draw.rect(self._screen, bg, (0, y, DISPLAY_WIDTH, _BANNER_H))
        pygame.draw.line(self._screen, _BG_DIVIDER,
                         (0, y), (DISPLAY_WIDTH, y), 1)

        msg_surf = self._font_banner.render(msg, True, fg)
        self._screen.blit(
            msg_surf,
            ((DISPLAY_WIDTH - msg_surf.get_width())  // 2,
             y + (_BANNER_H - msg_surf.get_height()) // 2),
        )

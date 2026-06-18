#!/usr/bin/env python3
# planB/terminal_view.py
# ──────────────────────────────────────────────────────────────────────────
# Plan B: 물리 WS2812B LED가 불안정할 때, 타일의 수막 상태를 "터미널"에
# 고품질 그래픽으로 보여주는 대체 시각화.
#
#   · 외부 의존성 0 — 순수 표준 라이브러리 + ANSI 24비트 트루컬러.
#     라즈베리파이에서 SSH로 그대로 실행 (pip 설치 불필요).
#   · src/sensor.py + src/classifier.py 를 그대로 재사용해 실측을 표시.
#   · 하드웨어(I2C/센서)가 없으면 자동으로 데모 시뮬레이터로 폴백.
#   · threshold(0.4 / 0.2)는 config/settings.py 에서 읽어옴.
#
# 실행:
#   python3 planB/terminal_view.py          # 하드웨어 자동감지, 없으면 데모
#   python3 planB/terminal_view.py --demo   # 강제 데모(시뮬레이션)
#   python3 planB/terminal_view.py --tile 0 # 표시할 타일 채널 지정
#
# 종료: Ctrl+C  (커서/화면 자동 복구)
# ──────────────────────────────────────────────────────────────────────────

import os
import sys
import math
import time
import signal
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 설정값 (config/settings.py 우선, 실패 시 기본값) ───────────────────────
try:
    from config.settings import THRESH_DRY, THRESH_WET, POLL_INTERVAL_SEC, CHANNEL_MAP
except Exception:
    THRESH_DRY, THRESH_WET, POLL_INTERVAL_SEC = 0.40, 0.20, 1.0
    CHANNEL_MAP = {0: "타일1", 1: "타일2", 2: "타일3", 3: "타일4"}

V_MAX = 0.60   # 게이지 풀스케일(표시용)

LEVELS = {
    0: ("건조", "DRY",     (207, 230, 255)),   # 백색
    1: ("수막", "FILM",    (255, 184,  77)),   # 황색
    2: ("고임", "POOLING", (255,  84, 104)),   # 적색
}

# ── 렌더 파라미터 ─────────────────────────────────────────────────────────
GRID   = 40          # 타일 픽셀 한 변 (짝수). 가로 40칸 / 세로 20행으로 출력
FPS    = 25
DT     = 1.0 / FPS

# ── ANSI ──────────────────────────────────────────────────────────────────
ESC = "\x1b"
RESET     = f"{ESC}[0m"
CLR_EOL   = f"{ESC}[K"
HOME      = f"{ESC}[H"
HIDE_CUR  = f"{ESC}[?25l"
SHOW_CUR  = f"{ESC}[?25h"
ALT_ON    = f"{ESC}[?1049h"
ALT_OFF   = f"{ESC}[?1049l"

def fg(c): return f"{ESC}[38;2;{c[0]};{c[1]};{c[2]}m"
def bg(c): return f"{ESC}[48;2;{c[0]};{c[1]};{c[2]}m"

# ── 색 유틸 ────────────────────────────────────────────────────────────────
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, t): return a + (b - a) * t

def blend(c1, c2, t):
    t = clamp(t)
    return (round(lerp(c1[0], c2[0], t)),
            round(lerp(c1[1], c2[1], t)),
            round(lerp(c1[2], c2[2], t)))

def lighten(c, t):  # c → 흰색 방향으로
    return blend(c, (255, 255, 255), t)

WHITE = (255, 255, 255)
BG    = (8, 11, 22)     # 타일 바깥(배경)


# ──────────────────────────────────────────────────────────────────────────
# 전압 → 단계 / 습윤도
# ──────────────────────────────────────────────────────────────────────────
def classify(v):
    if v >= THRESH_DRY: return 0
    if v <= THRESH_WET: return 2
    return 1

def wetness_from_voltage(v):
    """0(건조) ~ 1(완전 고임) 연속값. 단계 경계에서 부드럽게."""
    if v >= THRESH_DRY:
        return clamp((V_MAX - v) / (V_MAX - THRESH_DRY)) * 0.12
    if v <= THRESH_WET:
        return 0.62 + clamp((THRESH_WET - v) / THRESH_WET) * 0.38
    return 0.12 + (THRESH_DRY - v) / (THRESH_DRY - THRESH_WET) * 0.50


# ──────────────────────────────────────────────────────────────────────────
# 데이터 소스 — 하드웨어 / 데모
# ──────────────────────────────────────────────────────────────────────────
class HardwareSource:
    """src/sensor.py 의 MoistureSensor 재사용."""
    def __init__(self, tile):
        from src.sensor import MoistureSensor
        self.tile = tile
        self.sensor = MoistureSensor()
        self.name = CHANNEL_MAP.get(tile, f"타일{tile+1}")

    def read(self):
        return self.sensor.read_channel(self.tile)


class DemoSource:
    """센서 없이 0.55V(건조)↔0.05V(고임) 천천히 왕복 시뮬레이션."""
    def __init__(self, tile):
        self.tile = tile
        self.name = CHANNEL_MAP.get(tile, f"타일{tile+1}") + " (데모)"
        self._phase = 0.0

    def read(self):
        self._phase += 0.10
        s = (math.sin(self._phase) + 1) / 2          # 0~1
        import random
        return clamp(lerp(0.55, 0.05, s) + (random.random() - 0.5) * 0.01, 0, V_MAX)


# ──────────────────────────────────────────────────────────────────────────
# 타일 워터 렌더러
# ──────────────────────────────────────────────────────────────────────────
class WaterTile:
    def __init__(self, grid=GRID):
        self.N = grid
        self.c = (grid - 1) / 2.0
        self.half = grid / 2.0
        self.wet = 0.0          # 현재 표시 습윤도(목표로 수렴)
        self.target = 0.0
        self.level = 0
        self.ripples = []       # {"r":, "life":}
        self._spawn = 0.0
        # 정규화 좌표/높이 미리 계산 (그리드 고정)
        self._nx = [[(x - self.c) / self.half for x in range(grid)] for _ in range(grid)]

    def set_state(self, level, wetness):
        self.level = level
        self.target = wetness

    def _step(self, dt):
        # 습윤도 부드럽게 수렴
        self.wet += (self.target - self.wet) * clamp(dt * 2.2)
        # 잔물결 생성/소멸
        self._spawn -= dt
        if self.wet > 0.25 and self._spawn <= 0:
            self._spawn = lerp(2.6, 0.7, self.wet)
            self.ripples.append({"r": 0.08, "life": 1.0})
        for rp in self.ripples:
            rp["r"]    += dt * lerp(0.35, 0.7, self.wet)
            rp["life"] -= dt * 0.55
        self.ripples = [r for r in self.ripples if r["life"] > 0 and r["r"] < 1.15]

    def _pixel(self, px, py, t):
        """(px,py) 픽셀의 최종 RGB 또는 None(타일 바깥)."""
        nx = (px - self.c) / self.half
        ny = (py - self.c) / self.half
        # 둥근 사각형(슈퍼타원) 마스크
        shape = nx**4 + ny**4
        if shape > 0.95:
            return None

        # 베이스 베벨: 중앙(배수, 낮음·어두움) → 가장자리(높음·밝음)
        height = clamp(shape / 0.95)
        col = blend((27, 32, 48), (49, 58, 82), height)

        rc = math.sqrt(nx*nx + ny*ny)      # 중심 거리(고임 반경 비교용)
        wet = self.wet

        # 얇은 수막: 타일 전체를 옅게 덮음
        if wet > 0.02:
            col = blend(col, (58, 143, 216), 0.05 + clamp(wet) * 0.16)

        # 중앙 고임: wet^? 비선형 성장
        pool = clamp((wet - 0.12) / 0.88)
        pool_r = 0.15 + pool * 0.85
        if pool > 0.01 and rc < pool_r:
            depth = (pool_r - rc) / pool_r          # 중심일수록 깊음
            water = blend((58, 150, 220), (20, 70, 140), depth)
            if self.level == 2:                      # 고임 단계: 경고색 살짝
                water = blend(water, (150, 40, 70), 0.18)
            col = blend(col, water, 0.40 + depth * 0.45)

        # 잔물결: 링 위치에서 밝게
        for rp in self.ripples:
            if abs(rc - rp["r"]) < 0.05:
                col = lighten(col, 0.45 * rp["life"])

        # 반사광 시머(젖은 표면 광택)
        if wet > 0.08:
            for i in range(2):
                ph = t * 0.6 + i * 2.3
                sx = math.cos(ph) * 0.42
                sy = math.sin(ph * 1.3) * 0.42
                d2 = (nx - sx) ** 2 + (ny - sy) ** 2
                glow = math.exp(-d2 / 0.03)
                if glow > 0.02:
                    col = lighten(col, glow * (0.10 + wet * 0.14))

        # 가장자리 LED 글로우 (물리 LED 스트립을 화면으로 대체)
        if shape > 0.62:
            edge = clamp((shape - 0.62) / (0.95 - 0.62))
            accent = LEVELS[self.level][2]
            if self.level == 2:
                pulse = 0.55 + 0.45 * math.sin(t * 6.0)      # 빠른 적색 경고
            elif self.level == 1:
                pulse = 0.70 + 0.30 * math.sin(t * 3.0)      # 느린 황색 숨쉬기
            else:
                pulse = 0.85                                  # 잔잔한 흰빛
            col = blend(col, accent, edge * pulse)

        return col

    def render(self, t, dt):
        """반블록 '▀'(상=fg, 하=bg)로 정사각 픽셀 출력. 문자행 리스트 반환."""
        self._step(dt)
        N = self.N
        # 픽셀 색 캐시
        px = [[self._pixel(x, y, t) for x in range(N)] for y in range(N)]
        lines = []
        for row in range(N // 2):
            top_y, bot_y = row * 2, row * 2 + 1
            parts, cur_fg, cur_bg = [], None, None
            for x in range(N):
                top = px[top_y][x] or BG
                bot = px[bot_y][x] or BG
                if top != cur_fg:
                    parts.append(fg(top)); cur_fg = top
                if bot != cur_bg:
                    parts.append(bg(bot)); cur_bg = bot
                parts.append("▀")
            parts.append(RESET)
            lines.append("".join(parts))
        return lines


# ──────────────────────────────────────────────────────────────────────────
# 정보 패널
# ──────────────────────────────────────────────────────────────────────────
WIDTH = GRID  # 타일 가로폭에 맞춤

def bar_line(voltage):
    """0V(좌·고임) → V_MAX(우·건조) 게이지. 현재 위치에 마커."""
    w = WIDTH
    pos = int(clamp(voltage / V_MAX) * (w - 1))
    cells = []
    for i in range(w):
        if i == pos:
            cells.append(fg((255, 255, 255)) + "│")
        else:
            # 좌(적)→중(황)→우(백) 그라데이션
            ti = i / (w - 1)
            c = blend((255, 84, 104), (255, 184, 77), ti * 2) if ti < 0.5 \
                else blend((255, 184, 77), (207, 230, 255), (ti - 0.5) * 2)
            cells.append(fg(c) + "─")
    return "".join(cells) + RESET

def pad(s_visible_len, s):
    """ANSI 제외 가시폭 기준 우측 공백 + 줄 끝 클리어."""
    return s + " " * max(0, WIDTH - s_visible_len) + CLR_EOL


# ──────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────
_running = True

def _stop(*_):
    global _running
    _running = False

def make_source(tile, force_demo):
    if force_demo:
        return DemoSource(tile), "DEMO"
    try:
        src = HardwareSource(tile)
        return src, "LIVE"
    except Exception as e:
        sys.stderr.write(f"[알림] 센서 초기화 실패 → 데모 모드 ({type(e).__name__}: {e})\n")
        time.sleep(1.2)
        return DemoSource(tile), "DEMO"


def main():
    ap = argparse.ArgumentParser(description="ACHA Plan B — 터미널 수막 시각화")
    ap.add_argument("--demo", action="store_true", help="센서 없이 시뮬레이션")
    ap.add_argument("--tile", type=int, default=0, help="표시할 타일 채널 (기본 0)")
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    source, mode = make_source(args.tile, args.demo)
    tile = WaterTile()

    voltage = THRESH_DRY + 0.1
    history = []
    next_poll = 0.0
    t0 = time.monotonic()

    out = sys.stdout
    out.write(ALT_ON + HIDE_CUR)
    out.flush()
    try:
        while _running:
            now = time.monotonic()
            t = now - t0

            # 센서 폴링(애니메이션과 분리: 매 프레임 그리되 읽기는 주기적으로)
            if now >= next_poll:
                next_poll = now + POLL_INTERVAL_SEC
                try:
                    voltage = source.read()
                except Exception:
                    pass
                history.append(voltage)
                if len(history) > 40:
                    history.pop(0)

            level = classify(voltage)
            tile.set_state(level, wetness_from_voltage(voltage))
            ko, en, color = LEVELS[level]

            tile_lines = tile.render(t, DT)

            # 추세
            trend = ""
            if len(history) > 3:
                d = history[-1] - history[0]
                trend = "▲ 마르는 중" if d >= 0.005 else "▼ 젖는 중" if d <= -0.005 else "● 안정"

            # ── 프레임 조립 (각 원소 = 터미널 한 줄) ──
            rows = []
            mode_c = (122, 224, 164) if mode == "LIVE" else (255, 210, 125)
            head = (f"{fg((233,238,247))}ACHA · 타일 수막 모니터{RESET}"
                    f"  {fg(mode_c)}[{mode}]{RESET}")
            rows.append(pad(len("ACHA · 타일 수막 모니터  [" + mode + "]"), head))
            rows.append(pad(len(f"현재 타일 · {source.name}"),
                           f"{fg((138,152,179))}현재 타일 · {fg((233,238,247))}{source.name}{RESET}"))
            rows.append(CLR_EOL)

            rows.extend(ln + CLR_EOL for ln in tile_lines)

            rows.append(CLR_EOL)
            # 단계 배너
            banner = (f"{fg(color)}●{RESET} {fg(color)}{ko}{RESET} "
                      f"{fg((138,152,179))}{en}{RESET}   "
                      f"{fg((233,238,247))}{voltage:5.3f} V{RESET}   "
                      f"{fg((90,100,125))}{trend}{RESET}")
            vis = len(f"● {ko} {en}   {voltage:5.3f} V   {trend}")
            rows.append(pad(vis, banner))
            rows.append(CLR_EOL)
            # 게이지
            rows.append(bar_line(voltage) + CLR_EOL)
            scale = f"{fg((90,100,125))}0V·고임{' ' * (WIDTH - 14)}건조·{V_MAX:.1f}V↑{RESET}"
            rows.append(pad(WIDTH, scale))
            rows.append(CLR_EOL)
            # 임계 범례
            for lv in (0, 1, 2):
                lko, len_, lc = LEVELS[lv]
                rng = {0: f"V ≥ {THRESH_DRY:.2f}",
                       1: f"{THRESH_WET:.2f} ~ {THRESH_DRY:.2f}",
                       2: f"V ≤ {THRESH_WET:.2f}"}[lv]
                mark = "▸" if lv == level else " "
                txt = f"{mark} ■ {lko}  {rng}"
                seg = (f"{fg((233,238,247) if lv == level else (90,100,125))}{mark} "
                       f"{fg(lc)}■{RESET} "
                       f"{fg((233,238,247) if lv == level else (138,152,179))}{lko}  "
                       f"{fg((90,100,125))}{rng}{RESET}")
                rows.append(pad(len(txt), seg))
            rows.append(CLR_EOL)
            rows.append(pad(len("Ctrl+C 종료"), f"{fg((90,100,125))}Ctrl+C 종료{RESET}"))

            out.write(HOME + "\r\n".join(rows) + f"{ESC}[J")
            out.flush()
            time.sleep(DT)
    finally:
        out.write(SHOW_CUR + ALT_OFF + RESET)
        out.flush()
        print("[종료] 터미널 시각화 종료")


if __name__ == "__main__":
    main()

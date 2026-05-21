# CPD 타일 낙상방지 시스템 — Claude Code 메모리

> 이 파일은 Claude Code가 프로젝트 컨텍스트를 유지하기 위한 메모리 파일.
> 하드웨어 조립 완료 후 핀번호 입력만으로 바로 동작 가능하게 설계.

---

## 프로젝트 개요

**목적**: 욕실 바닥 잔류 수분을 감지해 LED로 미끄럼 위험을 시각적으로 경고
**대상**: 독거 노인 (낙상 위험 환경 개선)
**설치 위치**: 욕실 바닥 타일 (2×2 블록, 총 16타일)
**프레임워크**: Maslow 안전 욕구 / Ambient Assisted Living (AAL)
**팀 노션**: https://www.notion.so/2026-CPD-3bef7d9e8fbe83d5b63901dad30f0b57
**팀 피그마**: https://www.figma.com/design/Xh5B2kIe02iWJppcpqIYEm/

---

## 하드웨어 구성

### 핵심 부품

| 부품 | 모델 | 수량 | 역할 |
|------|------|------|------|
| 싱글보드컴퓨터 | Raspberry Pi (모델 미정) | 1 | 중앙 제어 |
| ADC | ADS1115 | 1 | 아날로그→디지털 변환 (I2C, 4채널) |
| LED 스트립 | WS2812B 5050 RGB 에폭시 코팅 | 4 | 수분 단계 시각화 |
| 기준 저항 | 10kΩ | 4+ | 분압회로 |
| 커넥터 | MCT-S08 (8핀) | 블록간 연결 | 블록간 전기 연결 |
| 전극 | 구리테이프 10mm | - | 저항식 수분 감지 |

### 물리 구조 (레이어)

```
L6 — 타일 (완만한 사각뿔)     ← 보행면, 물 중앙으로 배수 유도
L5 — 통합 모듈 ×4/블록        ← 구리 전극 + LED Strip + 포고핀 + 자석
   (포고핀으로 L5↔하우징 연결, MCT-S08)
L4 — 대메시 필터               ← 큰 이물질 차단
L3 — 4분할 지지대              ← 배선 채널 내장, 배수 안내
L2 — 배수 트랩 + 소메시        ← 미세 이물질 + 배수
L1 — 메인 하우징               ← RPi + ADS1115 수납, M3 나사 고정
```

### 블록 배치 (2×2)

```
[블록1] ─── [블록2]
  |              |
[블록3] ─── [블록4]

초록선(실선)  : VCC / GND / LED Data — 데이지체인
주황선(점선)  : SIG 아날로그 — 블록별 RPi 직결
```

---

## 핀 배정 (조립 후 여기에 입력)

### Raspberry Pi → ADS1115 (I2C)

```python
# I2C 핀 (RPi 표준 — 변경 불필요)
SDA_PIN = 2    # BCM GPIO2 (물리 핀 3)
SCL_PIN = 3    # BCM GPIO3 (물리 핀 5)

# ADS1115 I2C 주소
# ADDR핀 → GND : 0x48 (기본값, 현재 설계)
# ADDR핀 → VDD : 0x49
# ADDR핀 → SDA : 0x4A
# ADDR핀 → SCL : 0x4B
ADS1115_ADDRESS = 0x48
```

### ADS1115 채널 → 블록 매핑

```python
# ADS1115 채널 (단일 모드, GND 기준)
CHANNEL_MAP = {
    0: "블록1",   # ADS1115 A0
    1: "블록2",   # ADS1115 A1
    2: "블록3",   # ADS1115 A2
    3: "블록4",   # ADS1115 A3
}
```

### Raspberry Pi GPIO → WS2812B LED

```python
# TODO: 조립 후 실제 연결 핀으로 수정
LED_DATA_PIN = 18    # BCM GPIO18 (PWM0, 권장) — 물리 핀 12
```

---

## 회로 설계

### 분압회로 (블록 1개 기준)

```
3.3V (RPi) → R_ref(10kΩ) → V_out(노드) → R_water(전극) → GND
                                  ↓
                            ADS1115 Ax 입력
```

수식: `V_out = 3.3 × R_water / (R_ref + R_water)`

| 상태 | R_water | V_out | ADS1115 raw (16bit) |
|------|---------|-------|---------------------|
| 건조 | ∞ | ≈ 3.3V | ≈ 26400 |
| 수막 | ≈ 100kΩ | ≈ 3.0V | ≈ 24000 |
| 고임 | ≈ 5kΩ | ≈ 1.1V | ≈ 8800 |

> raw값 = V_out / 4.096 × 32767 (ADS1115 ±4.096V gain 기준)

### MCT-S08 커넥터 핀 배정

| 핀 번호 | 신호 | 전류 | 설명 |
|---------|------|------|------|
| 1, 2 | VCC (5V) | 2A × 2 = 4A | LED 전원 (데이지체인) |
| 3, 4 | GND | 2A × 2 = 4A | 공통 GND (데이지체인) |
| 5 | LED Data | 신호 | WS2812B 데이터선 |
| 6 | 3.3V | 신호 | ADS1115 전원 |
| 7 | SIG | 아날로그 | V_out → ADS1115 Ax |
| 8 | GND | - | SIG 기준 GND |

---

## 소프트웨어 로직

### 3단계 수분 판정

```
단계 0 (건조)  : V_out > THRESH_DRY   → LED 백색
단계 1 (수막)  : THRESH_WET < V_out ≤ THRESH_DRY  → LED 황색 (색 A)
단계 2 (고임)  : V_out ≤ THRESH_WET  → LED 적색 (색 B)
```

```python
# TODO: 실제 센서 캘리브레이션 후 값 확정
THRESH_DRY = 3.0   # V — 이 이상이면 건조
THRESH_WET = 1.5   # V — 이 이하면 고임
```

### LED 색상 (WS2812B, RGB)

```python
# TODO: 최종 색상 디자인 확정 전 임시값
LED_COLOR = {
    0: (255, 255, 255),   # 단계0 — 백색 (야간 조명 겸용)
    1: (255, 165, 0),     # 단계1 — 황색 (주의)   ← 색 A 미확정
    2: (255, 0, 0),       # 단계2 — 적색 (위험)   ← 색 B 미확정
}
LED_BRIGHTNESS = 128      # 0~255
```

### 폴링 주기

```python
POLL_INTERVAL_SEC = 1.0   # 초 단위, 1초마다 센서 읽기
```

---

## 파일 구조

```
cpd-tile-system/
├── CLAUDE.md              ← 이 파일 (메모리)
├── config/
│   └── settings.py        ← 핀번호, threshold, 색상 — 여기만 수정
├── src/
│   ├── main.py            ← 진입점
│   ├── sensor.py          ← ADS1115 읽기
│   ├── led.py             ← WS2812B 제어
│   └── classifier.py      ← 3단계 판정 로직
├── docs/
│   └── wiring.md          ← 배선 가이드
└── requirements.txt
```

---

## 미결 사항 (TODO)

- [ ] LED 색 A, 색 B 최종 확정 (디자인팀)
- [ ] threshold 값 캘리브레이션 (실제 센서 측정 후)
- [ ] RPi 모델 확정 → GPIO 핀 물리번호 검증
- [ ] LED_DATA_PIN 실제 연결 핀으로 수정
- [ ] 포고핀 규격 확정 (직경, 스트로크)
- [ ] 하우징 3D 치수 확정

---

## 의존성

```
RPi.GPIO
adafruit-circuitpython-ads1x15
rpi_ws281x
board
busio
```

설치:
```bash
pip install adafruit-circuitpython-ads1x15 rpi-ws281x
```

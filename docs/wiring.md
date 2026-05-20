# 배선 가이드

## RPi → ADS1115 (I2C)

| RPi 핀 (물리) | RPi 핀 (BCM) | ADS1115 핀 |
|--------------|--------------|-----------|
| 핀 3 | SDA (GPIO2) | SDA |
| 핀 5 | SCL (GPIO3) | SCL |
| 핀 1 | 3.3V | VDD |
| 핀 6 | GND | GND |
| — | GND | ADDR (기본값 0x48) |

> ADDR 핀을 GND에 연결하면 I2C 주소 0x48 (settings.py 기본값)

## ADS1115 → 분압회로 → 전극

각 채널(A0~A3)별 동일한 회로:

```
3.3V ─── R_ref(10kΩ) ─── [노드] ─── R_water(전극) ─── GND
                              │
                          ADS1115 Ax
```

| 노드 | 연결 |
|------|------|
| [노드] → ADS1115 A0 | 블록1 전극 |
| [노드] → ADS1115 A1 | 블록2 전극 |
| [노드] → ADS1115 A2 | 블록3 전극 |
| [노드] → ADS1115 A3 | 블록4 전극 |

## RPi → WS2812B LED Strip

| RPi 핀 (물리) | RPi 핀 (BCM) | LED Strip 핀 |
|--------------|--------------|-------------|
| 핀 12 | GPIO18 (PWM0) | Data (DI) |
| 핀 4 | 5V | 5V (전원) |
| 핀 6 | GND | GND |

> **주의**: WS2812B는 5V 전원, 데이터 레벨은 3.3V도 인식하지만
> 신호 레벨 변환기(3.3V→5V) 사용 권장 (긴 스트립이나 노이즈 환경)

## MCT-S08 블록간 커넥터

| 핀 | 신호 | 방향 |
|----|------|------|
| 1, 2 | VCC 5V | 데이지체인 (전류 4A) |
| 3, 4 | GND | 데이지체인 |
| 5 | LED Data | 데이지체인 |
| 6 | 3.3V | ADS1115 전원 |
| 7 | SIG | 블록 → RPi ADS1115 직결 |
| 8 | GND | SIG 기준 |

## I2C 활성화 (RPi 최초 설정)

```bash
sudo raspi-config
# Interface Options → I2C → Enable

# 확인
i2cdetect -y 1
# 0x48 위치에 숫자 보이면 정상
```

## 설치

```bash
# 시스템 패키지
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus i2c-tools

# Python 패키지
pip install -r requirements.txt
```

## 실행

```bash
cd cpd-tile-system
sudo python src/main.py
# WS2812B DMA 사용으로 sudo 필요
```

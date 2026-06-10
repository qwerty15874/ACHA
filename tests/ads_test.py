import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# I2C 초기화
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P0)

R_KNOWN = 10000  # 기준 저항 (Ω), 예: 10kΩ
VCC = 3.3

while True:
    v = chan.voltage
    if v > 0 and v < VCC:
        r_unknown = R_KNOWN * v / (VCC - v)
        print(f"전압: {v:.4f}V | 저항: {r_unknown:.1f}Ω")
    else:
        print("측정 범위 초과")
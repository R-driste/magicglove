from machine import Pin, I2C
import time
from qmc5883l import QMC5883L
from mpu6050 import MPU6050
import ssd1306

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)   # i2c bus setup
laser = Pin(6, Pin.OUT)                              # laser control pin
mode_button = Pin(10, Pin.IN, Pin.PULL_UP)           # mode toggle button
extra_button = Pin(11, Pin.IN, Pin.PULL_UP)          # extra pushbutton
flex_pins = [Pin(26, Pin.IN), Pin(27, Pin.IN), Pin(28, Pin.IN), Pin(22, Pin.IN)]  # flex sensor pins

pushbuttons = [                                      # list of 4 pushbuttons
    Pin(0, Pin.IN, Pin.PULL_UP),
    Pin(1, Pin.IN, Pin.PULL_UP),
    Pin(2, Pin.IN, Pin.PULL_UP),
    Pin(3, Pin.IN, Pin.PULL_UP)
]

oled = ssd1306.SSD1306_I2C(128, 64, i2c) # oled display initialization

class PCA9548A: # i2c multiplexer class
    def __init__(self, i2c, addr=0x70):
        self.i2c = i2c
        self.addr = addr
    def select_channel(self, channel):
        if 0 <= channel <= 7:
            self.i2c.writeto(self.addr, bytes([1 << channel]))
mux = PCA9548A(i2c) # create mux object

def read_magnetometer(channel): # read magnetometer data from given channel
    mux.select_channel(channel)
    sensor = QMC5883L(i2c)
    x, y, z = sensor.read_magnetometer()
    return (x, y, z)

PCA8574_ADDR = 0x20
def read_pca8574(): # read io expander PCA8574
    try:
        return i2c.readfrom(PCA8574_ADDR, 1)[0]
    except:
        return 0xFF

mux.select_channel(4) # select channel for gyro sensor
mpu = MPU6050(i2c) # initialize gyro sensor

modes = ["Magnetometer", "Flex Sensor", "Gyroscope"] # available modes
mode_index = 0
last_button = 1

while True:
    button_state = mode_button.value()# read mode button state
    if last_button == 1 and button_state == 0: # on button press (falling edge)
        mode_index = (mode_index + 1) % len(modes) # cycle mode
        oled.fill(0)
        oled.text(f"Mode: {modes[mode_index]}", 0, 0)
        oled.show()
        time.sleep(0.3) # debounce delay
    last_button = button_state

    oled.fill(0)

    if mode_index == 0: # magnetometer mode
        for i in range(4):
            mag = read_magnetometer(i)
            oled.text(f"M{i}: {mag[0]}, {mag[1]}", 0, i * 10)

    elif mode_index == 1: # flex sensor mode
        flex_values = [pin.value() for pin in flex_pins]
        pca_val = read_pca8574()
        for i, val in enumerate(flex_values):
            oled.text(f"Flex{i}: {val}", 0, i * 10)
        oled.text(f"PCA8574: {bin(pca_val)}", 0, 50)
        if flex_values[0] == 0:
            laser.on()
        else:
            laser.off()

    elif mode_index == 2: # gyroscope mode
        accel = mpu.get_accel_data()
        gyro = mpu.get_gyro_data()
        oled.text("Acc X: {:.1f}".format(accel['x']), 0, 0)
        oled.text("Acc Y: {:.1f}".format(accel['y']), 0, 10)
        oled.text("Gyro Z: {:.1f}".format(gyro['z']), 0, 20)

    pad_values = [pin.value() for pin in pushbuttons] # read pushbuttons states
    extra_val = extra_button.value()# read extra button state

    for i, val in enumerate(pad_values):
        oled.text(f"PadBtn{i}: {'P' if val == 0 else 'R'}", 0, 40 + i*10)
    oled.text(f"ExtraBtn: {'P' if extra_val == 0 else 'R'}", 70, 40)

    oled.show()
    time.sleep(0.1)

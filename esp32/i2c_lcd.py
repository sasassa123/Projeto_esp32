from machine import I2C
from lcd_api import LcdApi
import time

MASK_RS = 0x01
MASK_RW = 0x02
MASK_E = 0x04
MASK_BACKLIGHT = 0x08

class I2cLcd(LcdApi):
    def __init__(self, i2c, lcd_addr, num_lines, num_columns):
        self.i2c = i2c
        self.lcd_addr = lcd_addr
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.backlight = MASK_BACKLIGHT
        self._write_init()

    def _write_byte(self, data):
        self.i2c.writeto(self.lcd_addr, bytes([data | self.backlight]))

    def _strobe(self, data):
        self._write_byte(data | MASK_E)
        time.sleep_us(500)
        self._write_byte(data & ~MASK_E)
        time.sleep_us(500)

    def _write_init(self):
        self._write_cmd(0x33)
        self._write_cmd(0x32)
        self._write_cmd(0x28)
        self._write_cmd(0x0C)
        self._write_cmd(0x06)
        self.clear()

    def _write_cmd(self, cmd):
        self._write_byte(cmd & 0xF0)
        self._strobe(cmd & 0xF0)
        self._write_byte((cmd << 4) & 0xF0)
        self._strobe((cmd << 4) & 0xF0)

    def _write_data(self, data):
        high = (data & 0xF0) | MASK_RS
        low = ((data << 4) & 0xF0) | MASK_RS
        self._write_byte(high)
        self._strobe(high)
        self._write_byte(low)
        self._strobe(low)


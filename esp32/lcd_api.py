class LcdApi:
    LCD_CLR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x06
    LCD_DISPLAY_ON = 0x0C
    LCD_FUNCTION_SET = 0x28

    def __init__(self, num_lines, num_columns):
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.clear()

    def clear(self):
        self._write_cmd(self.LCD_CLR)

    def move_to(self, col, row):
        addr = col + (0x40 * row)
        self._write_cmd(0x80 | addr)

    def putchar(self, char):
        self._write_data(ord(char))

    def putstr(self, string):
        for char in string:
            self.putchar(char)

   
    def _write_cmd(self, cmd):
        raise NotImplementedError

    def _write_data(self, data):
        raise NotImplementedError


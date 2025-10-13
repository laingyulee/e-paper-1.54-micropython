import time
from machine import Pin, SPI
from math import ceil # sqrt is not needed for IL0373, but keep it for now
from fonts import asc2_0806

class TimeoutError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        
class Color():
    BLACK = 0x00 # 对应缓冲区中的 1
    WHITE = 0xff # 对应缓冲区中的 0
    
class Rotate():
    ROTATE_0 = 0
    ROTATE_90 = 1
    ROTATE_180 = 2
    ROTATE_270 = 3

class Screen():
    def __init__(self, width=152, height=152): # 默认值直接设为152x152
        self.width = width
        self.height = height
        self.width_bytes = ceil(width / 8) # 152 / 8 = 19
        self.height_bytes = height
        
    def __repr__(self):
        print(f"screen width: {self.width}")
        print(f"screen height: {self.height}")
        print(f"screen width bytes: {self.width_bytes}")
        print(f"screen height bytes: {self.height_bytes}")

class Paint():
    def __init__(self, screen=Screen(), rotate=Rotate.ROTATE_0, bg_color=Color.WHITE): # 默认旋转0度
        self.screen = screen
        self.img = bytearray(self.screen.width_bytes * self.screen.height_bytes)
        self.rotate = rotate
        self.bg_color = bg_color
        
        # Paint对象的逻辑尺寸，用于绘图函数的坐标转换
        if self.rotate == Rotate.ROTATE_0 or self.rotate == Rotate.ROTATE_180:
            self.width = self.screen.width
            self.height = self.screen.height
        else: # ROTATE_90 or ROTATE_270
            self.width = self.screen.height # 旋转后宽度变为原高度
            self.height = self.screen.width # 旋转后高度变为原宽度
        
    def __repr__(self):
        self.screen.__repr__()
        print(f"rotate: {self.rotate}")
        print(f"background color: 0x{self.bg_color:02x}")
            
    def clear(self, color):
        self.bg_color = color
        # 注意：IL0373驱动中，缓冲区中的0x00是白色，0xFF是黑色
        # 所以如果我们要清屏为白色，缓冲区应该填充0x00
        fill_byte = 0x00 if color == Color.WHITE else 0xFF
        for i in range(len(self.img)):
            self.img[i] = fill_byte
    
    def _convert_coor(self, x_pos, y_pos):
        # 确保坐标在 Paint 对象的逻辑尺寸内
        if x_pos < 0 or y_pos < 0 or x_pos >= self.width or y_pos >= self.height:
            return -1, -1 # Invalid coordinates

        # 根据当前Paint对象的逻辑尺寸进行转换
        # Arduino GxEPD库的旋转逻辑可能与我们之前的通用驱动略有不同
        # 根据GxGDEW0154T8.cpp中的drawPixel()逻辑进行调整
        # x, y 是传入的逻辑坐标
        # px, py 是转换后的物理坐标，用于寻址 img 缓冲区
        px, py = x_pos, y_pos
        
        if self.rotate == Rotate.ROTATE_0:
            pass # No change
        elif self.rotate == Rotate.ROTATE_90: # GxEPD case 1
            px, py = self.screen.width - y_pos - 1, x_pos
        elif self.rotate == Rotate.ROTATE_180: # GxEPD case 2
            px, py = self.screen.width - x_pos - 1, self.screen.height - y_pos - 1
        elif self.rotate == Rotate.ROTATE_270: # GxEPD case 3
            px, py = y_pos, self.screen.height - x_pos - 1
            
        # 检查转换后的物理坐标是否超出屏幕的物理尺寸
        if px < 0 or py < 0 or px >= self.screen.width or py >= self.screen.height:
            return -1, -1 # Out of bounds
            
        return px, py
    
    def draw_point(self, x_pos, y_pos, color=Color.BLACK):
        px, py = self._convert_coor(x_pos, y_pos)
        if px == -1 or py == -1: # 检查是否越界
            return
        
        addr = px // 8 + py * self.screen.width_bytes
        # Arduino驱动中是 (1 << (7 - x % 8))，我们保持一致
        bit_mask = (1 << (7 - px % 8))
        
        # IL0373 驱动中，缓冲区中的 0x00 是白色，0xFF 是黑色
        # GxEPD库的drawPixel: if (!color) _buffer[i] |= bit; else _buffer[i] &= ~bit;
        # 也就是 color=0 (黑色) -> 设置位为1； color=1 (白色) -> 设置位为0
        # 与我们Color.BLACK=0x00, Color.WHITE=0xff 配合
        if color == Color.BLACK: # 黑色，缓冲区中对应位设置为1
            self.img[addr] |= bit_mask
        else: # 白色，缓冲区中对应位设置为0
            self.img[addr] &= ~bit_mask
            
    def draw_line(self, x_start, y_start, x_end, y_end, color=Color.BLACK):
        # 使用Bresenham's line algorithm
        dx = abs(x_end - x_start)
        dy = abs(y_end - y_start)
        sx = 1 if x_start < x_end else -1
        sy = 1 if y_start < y_end else -1
        err = dx - dy

        while True:
            self.draw_point(x_start, y_start, color)
            if x_start == x_end and y_start == y_end:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x_start += sx
            if e2 < dx:
                err += dx
                y_start += sy
            
    def draw_rectangle(self, x_start, y_start, x_end, y_end, color=Color.BLACK, filled=False):
        if filled:
            # 填充矩形
            for y in range(min(y_start, y_end), max(y_start, y_end) + 1):
                for x in range(min(x_start, x_end), max(x_start, x_end) + 1):
                    self.draw_point(x, y, color)
        else:
            # 只画边框
            self.draw_line(x_start, y_start, x_start, y_end, color)
            self.draw_line(x_start, y_start, x_end, y_start, color)
            self.draw_line(x_start, y_end, x_end, y_end, color)
            self.draw_line(x_end, y_start, x_end, y_end, color)

    def draw_circle(self, x_center, y_center, radius, color=Color.BLACK, filled=False):
        x = 0
        y = radius
        d = 3 - 2 * radius
        
        while x <= y:
            if filled:
                self.draw_line(x_center - x, y_center + y, x_center + x, y_center + y, color)
                self.draw_line(x_center - x, y_center - y, x_center + x, y_center - y, color)
                self.draw_line(x_center - y, y_center + x, x_center + y, y_center + x, color)
                self.draw_line(x_center - y, y_center - x, x_center + y, y_center - x, color)
            else:
                self.draw_point(x_center + x, y_center + y, color)
                self.draw_point(x_center - x, y_center + y, color)
                self.draw_point(x_center + x, y_center - y, color)
                self.draw_point(x_center - x, y_center - y, color)
                self.draw_point(x_center + y, y_center + x, color)
                self.draw_point(x_center - y, y_center + x, color)
                self.draw_point(x_center + y, y_center - x, color)
                self.draw_point(x_center - y, y_center - x, color)

            if d < 0:
                d = d + 4 * x + 6
            else:
                d = d + 4 * (x - y) + 10
                y -= 1
            x += 1
            
    def show_char(self, char, x_start, y_start, font=asc2_0806, font_size=(6, 8), multiplier=1, color=Color.BLACK):
        char_idx = ord(char) - 32
        if char_idx < 0 or char_idx >= len(font):
            return

        for x_offset in range(font_size[0] * multiplier):
            if x_offset // multiplier >= font_size[0]:
                continue
            tmp = font[char_idx][x_offset // multiplier]
            for y_offset in range(font_size[1] * multiplier):
                if y_offset // multiplier >= font_size[1]:
                    continue
                # Font data is column-major, LSB is top pixel.
                # GxEPD's drawPixel uses (1 << (7 - x % 8)) for horizontal bit addressing
                # and (tmp >> (y_offset // multiplier)) & 0x01 for vertical bit order in font data
                if (tmp >> (y_offset // multiplier)) & 0x01:
                    self.draw_point(x_start + x_offset, y_start + y_offset, color)
                
    def show_string(self, string, x_start, y_start, font=asc2_0806, font_size=(6, 8), multiplier=1, color=Color.BLACK):
        for idx, char in enumerate(string):
            self.show_char(char, x_start + idx * font_size[0] * multiplier, y_start, font, font_size, multiplier, color)
            
    def show_bitmap(self, bitmap, x_start, y_start, multiplier=1, color=Color.BLACK):
        for r_idx, row in enumerate(bitmap):
            for c_idx, pixel_val in enumerate(row):
                if pixel_val == 1:
                    if multiplier == 1:
                        self.draw_point(x_start + c_idx, y_start + r_idx, color)
                    else:
                        for mr in range(multiplier):
                            for mc in range(multiplier):
                                self.draw_point(x_start + c_idx * multiplier + mc, y_start + r_idx * multiplier + mr, color)
    
    def show_img(self, img_path, x_start, y_start):
        raise NotImplementedError

# --- IL0373 LUTs (from GxGDEW0154T8.cpp) ---
# Full screen update LUTs
lut_20_vcomDC = bytearray([
  0x00, 0x08, 0x00, 0x00, 0x00, 0x02,
  0x60, 0x28, 0x28, 0x00, 0x00, 0x01,
  0x00, 0x14, 0x00, 0x00, 0x00, 0x01,
  0x00, 0x12, 0x12, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00,
]) # 44 bytes

lut_21_ww = bytearray([
  0x40, 0x08, 0x00, 0x00, 0x00, 0x02,
  0x90, 0x28, 0x28, 0x00, 0x00, 0x01,
  0x40, 0x14, 0x00, 0x00, 0x00, 0x01,
  0xA0, 0x12, 0x12, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]) # 42 bytes

lut_22_bw = bytearray([
  0x40, 0x08, 0x00, 0x00, 0x00, 0x02,
  0x90, 0x28, 0x28, 0x00, 0x00, 0x01,
  0x40, 0x14, 0x00, 0x00, 0x00, 0x01,
  0xA0, 0x12, 0x12, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]) # 42 bytes

lut_23_wb = bytearray([
  0x80, 0x08, 0x00, 0x00, 0x00, 0x02,
  0x90, 0x28, 0x28, 0x00, 0x00, 0x01,
  0x80, 0x14, 0x00, 0x00, 0x00, 0x01,
  0x50, 0x12, 0x12, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]) # 42 bytes

lut_24_bb = bytearray([
  0x80, 0x08, 0x00, 0x00, 0x00, 0x02,
  0x90, 0x28, 0x28, 0x00, 0x00, 0x01,
  0x80, 0x14, 0x00, 0x00, 0x00, 0x01,
  0x50, 0x12, 0x12, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]) # 42 bytes

# Partial screen update LUTs (if needed, not used in this basic demo)
# For simplicity, we will only implement full update first.
# If you need partial update, these LUTs would be used with command 0x20-0x24 in _Init_PartialUpdate
# Tx19 = 0x20
# lut_20_vcomDC_partial = bytearray([...])
# ...

class IL0373(): # Rename from SSD1680 to IL0373 for clarity
    def __init__(self, spi, dc, busy, cs, res, width=152, height=152, rotate=Rotate.ROTATE_0, bg_color=Color.WHITE):
        super().__init__()
        self.spi = spi
        self.dc = dc
        self.busy = busy
        self.cs = cs
        self.res = res
        
        self.screen = Screen(width=width, height=height)
        self.paint = Paint(self.screen, rotate=rotate, bg_color=bg_color) 
        
        self.cs(1) # CS pin needs to be high by default if not actively selected
        
    def chip_sel(self):
        self.cs(0)
        
    def chip_desel(self):
        self.cs(1)
        
    def read_busy(self, info="wait busy timeout!", timeout=10):
        st = time.time()
        # 直接移除 GPIO 编号的打印
        print(f"Waiting for BUSY pin to go HIGH (idle)...")
        while self.busy.value() == 0: # BUSY is LOW when busy for IL0373
            if (time.time() - st) > timeout:
                raise TimeoutError(info)
            time.sleep_ms(10)
        print(f"BUSY went HIGH. EPD is idle. Waited {time.time() - st:.2f}s")
        
    def hw_rst(self):
        print("hardware resetting...")
        self.res(0) # Pull RESET low
        time.sleep_ms(10) # 10ms pulse for IL0373 (from Arduino driver)
        self.res(1) # Release RESET
        time.sleep_ms(10) # Wait after reset release
        # No _waitWhileBusy immediately after hw_rst in Arduino driver's _wakeUp, but we can do it here.
        # However, _wakeUp will call _waitWhileBusy after power on command.
        print("hardware reset signal sent.")
        
    def write_cmd(self, cmd: int):
        self.chip_sel()
        self.dc(0) # Command mode
        self.spi.write(cmd.to_bytes(1, 'big'))
        self.dc(1) # Data mode (default after command)
        self.chip_desel()
        
    def write_data(self, data: int):
        self.chip_sel()
        self.dc(1) # Data mode
        self.spi.write(data.to_bytes(1, 'big'))
        self.chip_desel()

    def _Init_FullUpdate(self):
        self.write_cmd(0x82) # VCOM_DC setting
        self.write_data(0x08)
        self.write_cmd(0X50) # VCOM AND DATA INTERVAL SETTING
        self.write_data(0x97) # Value from Arduino driver

        self.write_cmd(0x20) # VCOM LUT
        self._write_bytes(lut_20_vcomDC)

        self.write_cmd(0x21) # WW LUT
        self._write_bytes(lut_21_ww)

        self.write_cmd(0x22) # BW LUT
        self._write_bytes(lut_22_bw)

        self.write_cmd(0x23) # WB LUT
        self._write_bytes(lut_23_wb)

        self.write_cmd(0x24) # BB LUT
        self._write_bytes(lut_24_bb)

    def _write_bytes(self, data_bytes: bytearray):
        # Optimized for writing multiple data bytes
        self.chip_sel()
        self.dc(1) # Data mode
        self.spi.write(data_bytes)
        self.chip_desel()
        
    def _wakeUp(self):
        print("Waking up EPD (IL0373 initialization sequence)...")
        self.hw_rst() # Arduino driver calls reset here

        self.write_cmd(0x01)     # POWER SETTING
        self.write_data(0x03)
        self.write_data(0x00)
        self.write_data(0x2b)
        self.write_data(0x2b)
        self.write_data(0x03)

        self.write_cmd(0x06)         # BOOST SOFT START
        self.write_data(0x17)   # A
        self.write_data(0x17)   # B
        self.write_data(0x17)   # C

        self.write_cmd(0x04) # POWER ON
        self.read_busy("_wakeUp Power On timeout!") # Wait for power to stabilize

        self.write_cmd(0x00) # PANEL SETTING
        self.write_data(0xbf)    # LUT from register, 128x296 (Arduino comment, but for 152x152)
        self.write_data(0x0d)    # VCOM to 0V fast

        self.write_cmd(0x30) # PLL SETTING
        self.write_data(0x3a)   # 3a 100HZ   29 150Hz 39 200HZ 31 171HZ

        self.write_cmd(0x61) # RESOLUTION SETTING
        self.write_data(self.screen.width) # 152 (0x98)
        self.write_data(self.screen.height >> 8) # 152 >> 8 = 0
        self.write_data(self.screen.height & 0xFF) # 152 & 0xFF = 152 (0x98)

        self._Init_FullUpdate()
        print("EPD woke up.")

    def _sleep(self):
        print("Putting EPD to sleep...")
        self.write_cmd(0x02)      # POWER OFF
        self.read_busy("_sleep Power Off timeout!")
        
        self.write_cmd(0x07) # DEEP SLEEP
        self.write_data(0xa5)
        print("EPD is in deep sleep.")
        
    def init(self):
        self._wakeUp() # Simplified init to just call _wakeUp for full init sequence
        
    def update_mem(self):
        print("updating the memory...")
        # Arduino driver writes 0xFF to 0x10 command (old data) then ~_buffer[i] to 0x13 (new data)
        # This is different from SSD1680 which uses 0x24 for new data.
        
        # Write "old" image (all white) to RAM 1
        self.write_cmd(0x10) # DATA START TRANSMISSION 1
        self.chip_sel()
        self.dc(1)
        for _ in range(self.paint.screen.height_bytes * self.paint.screen.width_bytes):
            self.spi.write(b'\xFF') # Write white (0xFF) as old data
        self.chip_desel()
            
        # Write "new" image (our buffer, inverted) to RAM 2
        self.write_cmd(0x13) # DATA START TRANSMISSION 2
        self.chip_sel()
        self.dc(1)
        for k in range(self.paint.screen.height_bytes * self.paint.screen.width_bytes):
            # Invert data as per Arduino driver: _writeData(~_buffer[i])
            byte = ~self.paint.img[k] & 0xFF # Ensure it stays within 8 bits
            self.spi.write(byte.to_bytes(1, 'big'))
        self.chip_desel()
        print("updating memory successful")
        
    def update_screen(self):
        print("updating the screen (display refresh)...")
        self.write_cmd(0x12) # DISPLAY REFRESH
        self.read_busy("update screen timeout!")
        print("update screen successful")
        self._sleep() # Arduino driver puts to sleep after update
        
    def update(self):
        self.update_mem()
        self.update_screen()
        
    # --- Passthrough methods (remain the same) ---
    def clear(self, *args, **kwargs):
        self.paint.clear(*args, **kwargs)
        
    def draw_point(self, *args, **kwargs):
        self.paint.draw_point(*args, **kwargs)
        
    def draw_line(self, *args, **kwargs):
        self.paint.draw_line(*args, **kwargs)
    
    def draw_rectangle(self, *args, **kwargs):
        self.paint.draw_rectangle(*args, **kwargs)
        
    def draw_circle(self, *args, **kwargs):
        self.paint.draw_circle(*args, **kwargs)
        
    def show_char(self, *args, **kwargs):
        self.paint.show_char(*args, **kwargs)
        
    def show_string(self, *args, **kwargs):
        self.paint.show_string(*args, **kwargs)
    
    def show_bitmap(self, *args, **kwargs):
        self.paint.show_bitmap(*args, **kwargs)
        
    def show_img(self, *args, **kwargs):
        self.paint.show_img(*args, **kwargs)
    

if __name__ == "__main__": # test block
    # --- ESP32-S3 Pin Definitions (ADJUST AS NEEDED) ---
    spi_id = 1      # Use SPI controller 1 (HSPI)
    sck_pin = 18    # SPI SCK (Clock) - Example GPIO
    mosi_pin = 23   # SPI MOSI (Data Out) - Example GPIO
    miso_pin = 19   # SPI MISO (Data In) - Example GPIO (EPD typically doesn't use MISO)

    busy_pin = 13   # BUSY pin (Input) - Example GPIO
    reset_pin = 15  # RESET pin (Output) - Example GPIO
    dc_pin = 14     # Data/Command pin (Output) - Example GPIO
    cs_pin = 5      # Chip Select pin (Output) - Example GPIO

    spi_epd = SPI(
        spi_id,
        baudrate=4_000_000,
        polarity=0,
        phase=0,
        sck=Pin(sck_pin),
        mosi=Pin(mosi_pin),
        miso=Pin(miso_pin)
    )

    busy = Pin(busy_pin, Pin.IN)
    res = Pin(reset_pin, Pin.OUT)
    dc = Pin(dc_pin, Pin.OUT)
    cs = Pin(cs_pin, Pin.OUT)

    # Instantiate the IL0373 driver
    epd = IL0373( # Changed from SSD1680 to IL0373
            spi_epd,
            dc,
            busy,
            cs,
            res,
            width=152,
            height=152,
            rotate=Rotate.ROTATE_0, # Default to 0 rotation
            bg_color=Color.WHITE
            )

    epd.init()
    epd.clear(Color.WHITE)
    
    epd.draw_rectangle(0, 0, 151, 151, Color.BLACK)
    epd.draw_line(0, 75, 151, 75, Color.BLACK)
    epd.draw_line(75, 0, 75, 151, Color.BLACK)
    epd.draw_rectangle(10, 10, 40, 40, Color.BLACK, filled=True)
    epd.draw_circle(75, 75, 30, Color.BLACK)
    epd.draw_circle(75, 75, 15, Color.BLACK, filled=True)

    epd.show_string("IL0373", 5, 5, multiplier=1, color=Color.BLACK)
    epd.show_string("1.54 inch", 5, 20, multiplier=2, color=Color.BLACK)
    epd.show_string("MicroPython!", 5, 60, multiplier=2, color=Color.BLACK)
    epd.show_string("152x152", 5, 100, multiplier=3, color=Color.BLACK)

    heart_bitmap = [
        [0,1,0,1,0],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [0,1,1,1,0],
        [0,0,1,0,0]
    ]
    epd.show_bitmap(heart_bitmap, 120, 120, multiplier=1, color=Color.BLACK)
    
    epd.update()
    print("Demo finished. Displaying content.")
    time.sleep(5)
    
    epd.clear(Color.WHITE)
    epd.show_string("Cleared!", 20, 60, multiplier=3, color=Color.BLACK)
    epd.update()
    time.sleep(2)
    
    # After update, the _sleep() is called automatically as per Arduino driver
    # If you want to explicitly deep sleep again:
    # epd._sleep()

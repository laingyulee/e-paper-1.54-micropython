import time
from machine import Pin, SPI
from math import ceil
import struct # For ufont's struct.pack

# ==============================================================================
# Start of ufont.py content (Integrated into il0373.py)
# ==============================================================================

# Helper functions from ufont.py, made into module-level functions
def _bmf_bytes_to_int(byte):
    i = 0
    for _ in byte:
        i = (i << 8) + _
    return i

def _bmf_byte_to_bit(byte_arr, font_size):
    """
    将 BMF 字体文件中读取的字节数组转换为 2D 位图数组 (font_size x font_size)。
    假设 BMF 字体数据是按行存储的，每行填充到最近的8位字节。
    例如，12x12 字体，每行12像素，需要2个字节来存储 (2*8=16位)。
    """
    if not byte_arr:
        return [[0 for _ in range(font_size)] for _ in range(font_size)] # Return empty bitmap

    bitmap_2d = []
    bytes_per_row = ceil(font_size / 8) # 每行需要的字节数 (例如 12px -> 2 bytes)
    
    for r_idx in range(font_size): # 遍历每一行
        row_bits = []
        # 从 byte_arr 中取出当前行对应的字节
        # 假设 byte_arr 是连续的，总长度为 bytes_per_row * font_size
        start_byte_idx = r_idx * bytes_per_row
        
        for b_idx in range(bytes_per_row): # 遍历当前行的每个字节
            if start_byte_idx + b_idx < len(byte_arr):
                current_byte = byte_arr[start_byte_idx + b_idx]
            else:
                current_byte = 0 # Prevent IndexError if byte_arr is too short

            for i in range(7, -1, -1): # 从最高位开始，提取每个像素
                if len(row_bits) < font_size: # 确保只提取 font_size 个像素
                    row_bits.append((current_byte >> i) & 1)
                else:
                    break # Current row is full
        bitmap_2d.append(row_bits)
    
    # Pad rows if they are shorter than font_size (shouldn't happen if logic is correct)
    for row in bitmap_2d:
        while len(row) < font_size:
            row.append(0)

    # Pad with empty rows if bitmap_2d has fewer than font_size rows
    while len(bitmap_2d) < font_size:
        bitmap_2d.append([0 for _ in range(font_size)])

    return bitmap_2d

class BMFont:
    def __init__(self, font_file_path):
        self.font_file_path = font_file_path
        self.font = None # Will be opened on first access
        self.bmf_info = None
        self.version = 0
        self.map_mode = 0
        self.start_bitmap = 0
        self.font_size = 0
        self.bitmap_size = 0
        self._load_font_info()

    def _load_font_info(self):
        try:
            self.font = open(self.font_file_path, "rb", buffering=0) # buffering=0 for MicroPython
            self.bmf_info = self.font.read(16)

            if self.bmf_info[0:2] != b"BM":
                raise TypeError("字体文件格式不正确: " + self.font_file_path)

            self.version = self.bmf_info[2]
            if self.version != 3:
                raise TypeError("字体文件版本不正确: " + str(self.version))

            self.map_mode = self.bmf_info[3]
            self.start_bitmap = _bmf_bytes_to_int(self.bmf_info[4:7])
            self.font_size = self.bmf_info[7]
            self.bitmap_size = self.bmf_info[8]
            self.font.seek(0) # Reset file pointer after reading info
        except Exception as e:
            if self.font:
                self.font.close()
            self.font = None # Indicate font loading failed
            raise e

    def _get_index(self, word):
        if not self.font: return -1 # Font not loaded
        
        word_code = ord(word)
        start = 0x10 # Start of index table
        end = self.start_bitmap - 2 # End of index table
        
        # Ensure file pointer is at the beginning of the index table for search
        # self.font.seek(0x10, 0) # This seek is not needed within the loop if mid is calculated correctly

        while start <= end:
            # mid must be an even offset for 2-byte word codes
            mid = start + ((end - start) // 2 // 2) * 2 
            
            self.font.seek(mid, 0)
            target_code = _bmf_bytes_to_int(self.font.read(2))
            
            if word_code == target_code:
                # Calculate index relative to the start of index table (0x10)
                # Each entry is 2 bytes (word_code) + 2 bytes (bitmap_offset) = 4 bytes
                # But the get_bitmap uses index * bitmap_size, so index is just character count.
                # Let's re-evaluate based on the original ufont's logic:
                # original: return (mid - 16) >> 1
                # This returns the index in the word_code list, not byte offset in bitmap section.
                # The bitmap section is self.start_bitmap + index * self.bitmap_size
                # So the index is indeed (mid - 0x10) / 2
                return (mid - 0x10) // 2
            elif word_code < target_code:
                end = mid - 2
            else:
                start = mid + 2
        return -1

    def get_bitmap(self, word):
        """
        获取点阵图 (字节列表)
        :param word: 字
        :return: 字节列表，如果失败则返回一个默认的问号点阵
        """
        if not self.font:
            # Return a default "question mark" or empty bitmap
            # This is a placeholder for a 12x12 font, 12*12/8 = 18 bytes
            return [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] # Empty or simple error
            
        index = self._get_index(word)
        if index == -1:
            # Default "question mark" bitmap for 12x12
            # This is a simplified 12x12 question mark
            return [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, # 6 bytes for top 4 rows
                    0x0C, 0x03, 0x0C, 0x03, 0x0C, 0x03, # ? top
                    0x0C, 0x03, 0x00, 0x00, 0x00, 0x00, # ? bottom
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00] # 6 bytes for bottom 4 rows
        
        self.font.seek(self.start_bitmap + index * self.bitmap_size, 0)
        return list(self.font.read(self.bitmap_size)) # Return as list of integers for byte_to_bit

# ==============================================================================
# End of ufont.py content
# ==============================================================================


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
        fill_byte = 0x00 if color == Color.WHITE else 0xFF
        for i in range(len(self.img)):
            self.img[i] = fill_byte
    
    def _convert_coor(self, x_pos, y_pos):
        if x_pos < 0 or y_pos < 0 or x_pos >= self.width or y_pos >= self.height:
            return -1, -1 # Invalid coordinates

        px, py = x_pos, y_pos
        
        if self.rotate == Rotate.ROTATE_0:
            pass
        elif self.rotate == Rotate.ROTATE_90:
            px, py = self.screen.width - y_pos - 1, x_pos
        elif self.rotate == Rotate.ROTATE_180:
            px, py = self.screen.width - x_pos - 1, self.screen.height - y_pos - 1
        elif self.rotate == Rotate.ROTATE_270:
            px, py = y_pos, self.screen.height - x_pos - 1
            
        if px < 0 or py < 0 or px >= self.screen.width or py >= self.screen.height:
            return -1, -1
            
        return px, py
    
    def draw_point(self, x_pos, y_pos, color=Color.BLACK):
        px, py = self._convert_coor(x_pos, y_pos)
        if px == -1 or py == -1:
            return
        
        addr = px // 8 + py * self.screen.width_bytes
        bit_mask = (1 << (7 - px % 8))
        
        if color == Color.BLACK:
            self.img[addr] |= bit_mask
        else:
            self.img[addr] &= ~bit_mask
            
    def draw_line(self, x_start, y_start, x_end, y_end, color=Color.BLACK):
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
            for y in range(min(y_start, y_end), max(y_start, y_end) + 1):
                for x in range(min(x_start, x_end), max(x_start, x_end) + 1):
                    self.draw_point(x, y, color)
        else:
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
            
    # show_char and show_string will now be handled by IL0373 instance directly using BMF font
    # They will be "passthrough" methods to the IL0373's BMF rendering
    def show_char(self, char, x_start, y_start, font_size, color=Color.BLACK):
        # This will be overridden by IL0373's BMF rendering
        pass # Not directly used by Paint anymore
                
    def show_string(self, string, x_start, y_start, font_size, color=Color.BLACK):
        # This will be overridden by IL0373's BMF rendering
        pass # Not directly used by Paint anymore
            
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


class IL0373():
    def __init__(self, spi, dc, busy, cs, res, width=152, height=152, rotate=Rotate.ROTATE_0, bg_color=Color.WHITE):
        super().__init__()
        self.spi = spi
        self.dc = dc
        self.busy = busy
        self.cs = cs
        self.res = res
        
        self.screen = Screen(width=width, height=height)
        self.paint = Paint(self.screen, rotate=rotate, bg_color=bg_color)
        
        self.is_sleeping = True 
        self.cs(1) 
        
        # --- 初始化 BMF 字体 ---
        self.bmf_font = None # Default to None
        self.font_width = 0 # Default font width
        self.font_height = 0 # Default font height
        try:
            self.bmf_font = BMFont("fusion-pixel-12-6881-12.v3.bmf")
            self.font_width = self.bmf_font.font_size
            self.font_height = self.bmf_font.font_size
            print(f"BMF font loaded. Size: {self.font_width}x{self.font_height}")
        except Exception as e:
            print(f"Failed to load BMF font fusion-pixel-12-6880-12.v3.bmf: {e}")
            print("Text display will be unavailable.")

    def read_busy(self, info="wait busy timeout!", timeout=30):
        st = time.time()
        print(f"Waiting for BUSY pin to go HIGH (idle)...")
        while self.busy.value() == 0:
            if (time.time() - st) > timeout:
                raise TimeoutError(info)
            time.sleep_ms(10)
        print(f"BUSY went HIGH. EPD is idle. Waited {time.time() - st:.2f}s")
        
    def hw_rst(self):
        print("hardware resetting...")
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        time.sleep_ms(10)
        print("hardware reset signal sent.")
        
    def write_cmd(self, cmd: int):
        self.chip_sel()
        self.dc(0)
        self.spi.write(cmd.to_bytes(1, 'big'))
        self.dc(1)
        self.chip_desel()
        
    def write_data(self, data: int):
        self.chip_sel()
        self.dc(1)
        self.spi.write(data.to_bytes(1, 'big'))
        self.chip_desel()

    def _Init_FullUpdate(self):
        self.write_cmd(0x82)
        self.write_data(0x08)
        self.write_cmd(0X50)
        self.write_data(0x97)

        self.write_cmd(0x20)
        self._write_bytes(lut_20_vcomDC)

        self.write_cmd(0x21)
        self._write_bytes(lut_21_ww)

        self.write_cmd(0x22)
        self._write_bytes(lut_22_bw)

        self.write_cmd(0x23)
        self._write_bytes(lut_23_wb)

        self.write_cmd(0x24)
        self._write_bytes(lut_24_bb)

    def _write_bytes(self, data_bytes: bytearray):
        self.chip_sel()
        self.dc(1)
        self.spi.write(data_bytes)
        self.chip_desel()
        
    def _wakeUp(self):
        print("Waking up EPD (IL0373 initialization sequence)...")
        self.hw_rst()

        self.write_cmd(0x01)
        self.write_data(0x03)
        self.write_data(0x00)
        self.write_data(0x2b)
        self.write_data(0x2b)
        self.write_data(0x03)

        self.write_cmd(0x06)
        self.write_data(0x17)
        self.write_data(0x17)
        self.write_data(0x17)

        self.write_cmd(0x04)
        self.read_busy("_wakeUp Power On timeout!")

        self.write_cmd(0x00)
        self.write_data(0xbf)
        self.write_data(0x0d)

        self.write_cmd(0x30)
        self.write_data(0x3a)

        self.write_cmd(0x61)
        self.write_data(self.screen.width)
        self.write_data(self.screen.height >> 8)
        self.write_data(self.screen.height & 0xFF)

        self._Init_FullUpdate()
        print("EPD woke up.")
        self.is_sleeping = False

    def _sleep(self):
        print("Putting EPD to sleep...")
        self.write_cmd(0x02)
        self.read_busy("_sleep Power Off timeout!")
        
        self.write_cmd(0x07)
        self.write_data(0xa5)
        print("EPD is in deep sleep.")
        self.is_sleeping = True
        
    def init(self):
        self._wakeUp()
        
    def update_mem(self):
        print("updating the memory...")
        self.write_cmd(0x10)
        self.chip_sel()
        self.dc(1)
        for _ in range(self.paint.screen.height_bytes * self.paint.screen.width_bytes):
            self.spi.write(b'\xFF')
        self.chip_desel()
            
        self.write_cmd(0x13)
        self.chip_sel()
        self.dc(1)
        for k in range(self.paint.screen.height_bytes * self.paint.screen.width_bytes):
            byte = ~self.paint.img[k] & 0xFF
            self.spi.write(byte.to_bytes(1, 'big'))
        self.chip_desel()
        print("updating memory successful")
        
    def update_screen(self):
        print("updating the screen (display refresh)...")
        self.write_cmd(0x12)
        self.read_busy("update screen timeout!")
        print("update screen successful")
        self._sleep()
        
    def update(self):
        if self.is_sleeping:
            print("Waking up EPD for update...")
            self._wakeUp()
        
        self.update_mem()
        self.update_screen()

    def chip_sel(self):
        self.cs(0)
        
    def chip_desel(self):
        self.cs(1)

    # --- 统一的文本显示方法 ---
    def show_string(self, text, x_start, y_start, multiplier=1, color=Color.BLACK):
        if not self.bmf_font:
            print("BMF font not loaded. Cannot display text.")
            return

        original_font_size = self.font_width 
        # displayed_font_size = original_font_size * multiplier # 不再直接使用此值作为步进

        current_x = x_start

        for char_idx, char in enumerate(text):
            byte_data = self.bmf_font.get_bitmap(char)
            char_bitmap_2d = _bmf_byte_to_bit(byte_data, original_font_size)

            # --- 计算字符的实际内容宽度 ---
            min_pixel_x = original_font_size # 最左边的有效像素列
            max_pixel_x = -1                  # 最右边的有效像素列
            has_pixel = False

            for r_offset in range(original_font_size):
                for c_offset in range(original_font_size):
                    if char_bitmap_2d[r_offset][c_offset] == 1:
                        has_pixel = True
                        if c_offset < min_pixel_x:
                            min_pixel_x = c_offset
                        if c_offset > max_pixel_x:
                            max_pixel_x = c_offset
            
            # 字符的实际内容宽度 (在原始字体大小下)
            # 对于完全空白的字符 (如空格 ' ')，has_pixel 会是 False
            if has_pixel:
                char_content_width_original = max_pixel_x - min_pixel_x + 1
            else:
                # 对于空格或无法识别的字符，给一个默认的宽度，例如半个字体宽度
                char_content_width_original = original_font_size // 2 # 12 // 2 = 6
                min_pixel_x = 0 # 对于空白字符，从0开始绘制 (虽然不会画任何东西)

            # 确保内容宽度至少为1，避免步进为0
            if char_content_width_original <= 0:
                char_content_width_original = 1
            
            # --- 绘制字符 ---
            # 绘制时，从 `min_pixel_x` 开始，而不是从 0 开始，以削减左侧空白
            for r_offset in range(original_font_size):
                for c_offset in range(original_font_size):
                    if char_bitmap_2d[r_offset][c_offset] == 1:
                        for mr in range(multiplier):
                            for mc in range(multiplier):
                                # 绘制的 X 坐标 = 当前字符起始 X + (原始像素列 - 最小像素列) * 放大倍数 + 放大像素内的偏移
                                self.paint.draw_point(
                                    current_x + (c_offset - min_pixel_x) * multiplier + mc,
                                    y_start + r_offset * multiplier + mr,
                                    color
                                )
            
            # --- 计算下一个字符的起始 X 坐标 (步进) ---
            # 字符的实际步进 = 放大后的内容宽度 + 额外间距
            # 额外间距可以在放大后设定，例如 1 * multiplier 像素
            ADDITIONAL_SPACING_PIXELS = 1 # 每个字符之间额外增加 1 像素间距 (在原始字体大小下)
            
            # 计算下一个字符的起始 X 坐标
            next_char_advance = (char_content_width_original + ADDITIONAL_SPACING_PIXELS) * multiplier
            
            # 确保步进不会过小，至少要保证能够显示字符
            if next_char_advance <= 0: # 避免步进为0或负数导致字符重叠
                next_char_advance = 1 * multiplier # 强制最小步进
                
            current_x += next_char_advance
            
        print(f"show_string: finished '{text}'.")

    # --- 新增：计算字符串总显示宽度的方法 ---
    def get_string_display_width(self, text, multiplier=1):
        if not self.bmf_font:
            return len(text) * self.font_width * multiplier # Fallback if font not loaded
        
        total_width = 0
        original_font_size = self.font_width
        ADDITIONAL_SPACING_PIXELS = 1 # 对应 show_string 中的 ADDITIONAL_SPACING_PIXELS
        
        for char in text:
            byte_data = self.bmf_font.get_bitmap(char)
            char_bitmap_2d = _bmf_byte_to_bit(byte_data, original_font_size)

            min_pixel_x = original_font_size
            max_pixel_x = -1
            has_pixel = False

            for r_offset in range(original_font_size):
                for c_offset in range(original_font_size):
                    if char_bitmap_2d[r_offset][c_offset] == 1:
                        has_pixel = True
                        if c_offset < min_pixel_x:
                            min_pixel_x = c_offset
                        if c_offset > max_pixel_x:
                            max_pixel_x = c_offset
            
            if has_pixel:
                char_content_width_original = max_pixel_x - min_pixel_x + 1
            else:
                char_content_width_original = original_font_size // 2

            if char_content_width_original <= 0:
                char_content_width_original = 1
                
            next_char_advance = (char_content_width_original + ADDITIONAL_SPACING_PIXELS) * multiplier
            if next_char_advance <= 0:
                next_char_advance = 1 * multiplier
                
            total_width += next_char_advance
            
        return total_width

    # --- Passthrough methods (保持不变) ---
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
        
    def show_bitmap(self, *args, **kwargs):
        self.paint.show_bitmap(*args, **kwargs)
        
    def show_img(self, *args, **kwargs):
        self.paint.show_img(*args, **kwargs)
    

if __name__ == "__main__": # test block
    # --- ESP32-S3 Pin Definitions (ADJUST AS NEEDED) ---
    spi_id = 1
    sck_pin = 13
    mosi_pin = 12
    miso_pin = 19

    busy_pin = 8
    reset_pin = 11
    dc_pin = 10
    cs_pin = 9

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

    epd = IL0373(
            spi_epd,
            dc,
            busy,
            cs,
            res,
            width=152,
            height=152,
            rotate=Rotate.ROTATE_0,
            bg_color=Color.WHITE
            )

    epd.init()
    epd.clear(Color.WHITE)
    
    epd.draw_rectangle(0, 0, 151, 151, Color.BLACK)
    epd.draw_line(0, 75, 151, 75, Color.BLACK)
    epd.draw_line(75, 0, 75, 151, Color.BLACK)
    epd.draw_rectangle(110, 10, 140, 40, Color.BLACK, filled=True)
    epd.draw_circle(75, 75, 30, Color.BLACK)
    epd.draw_circle(75, 75, 15, Color.BLACK, filled=True)

    # All text now uses the BMF font, no multiplier needed for size
    epd.show_string("IL0373 Driver", 5, 5, color=Color.BLACK)
    epd.show_string("1.54 inch", 5, 15, color=Color.BLACK)
    epd.show_string("你好世界", 5, 30, 2, color=Color.BLACK)
    epd.show_string("天气时钟", 5, 60, color=Color.BLACK)
    epd.show_string("MicroPython!", 5, 100, color=Color.BLACK)
    epd.show_string("152x152", 5, 120, 2, color=Color.BLACK)

    heart_bitmap = [
        [0,1,0,1,0],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [0,1,1,1,0],
        [0,0,1,0,0]
    ]
    epd.show_bitmap(heart_bitmap, 120, 120, multiplier=3, color=Color.BLACK)
    
    epd.update()
    print("Demo finished. Displaying content.")
    #time.sleep(10)
    
    #epd.clear(Color.WHITE)
    #epd.update()
    #time.sleep(1)

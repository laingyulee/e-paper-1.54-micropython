# main.py
import time
from machine import Pin, SPI
from il0373 import IL0373, Color, Rotate # 导入修改后的驱动和相关常量

# --- 定义引脚 (请根据你的ESP32-S3开发板实际连接修改这些引脚) ---
# 以下是一些常见的ESP32-S3 GPIO引脚，但请务必查阅你开发板的引脚图！

# SPI 配置
# ESP32-S3通常使用SPI(1)或SPI(2)作为通用SPI外设。SPI(0)常用于内部闪存。
spi_id = 1
sck_pin = 13    # SPI SCK (Clock)
mosi_pin = 12   # SPI MOSI (Data Out)

# 控制引脚
busy_pin = 8   # BUSY pin (Input)
reset_pin = 11  # RESET pin (Output)
dc_pin = 10     # Data/Command pin (Output)
cs_pin = 9     # Chip Select pin (Output)

# 初始化SPI
spi_epd = SPI(
    spi_id,
    baudrate=4_000_000, # 墨水屏刷新速度较慢，但SPI速度可以高一些
    polarity=0,
    phase=0,
    sck=Pin(sck_pin),
    mosi=Pin(mosi_pin),
)

# 初始化控制引脚
busy = Pin(busy_pin, Pin.IN)
res = Pin(reset_pin, Pin.OUT)
dc = Pin(dc_pin, Pin.OUT)
cs = Pin(cs_pin, Pin.OUT)

# 实例化IL0373驱动
# 传入正确的宽度和高度，以及所需的旋转角度
epd = IL0373(
    spi_epd,
    dc,
    busy,
    cs,
    res,
    width=152,  # 1.54寸墨水屏的宽度
    height=152, # 1.54寸墨水屏的高度
    rotate=Rotate.ROTATE_0, # 0度旋转，直接映射像素到缓冲区
    bg_color=Color.WHITE # 背景色为白色
)

print("EPD Driver initialized.")

def main_demo():
    print("Starting EPD demo...")
    
    # 1. 初始化显示屏
    epd.init()
    
    # 2. 清屏为白色
    epd.clear(Color.WHITE)
    print("Screen cleared to white.")
    
    # 3. 绘制一些图形和文本
    
    # 绘制边框
    epd.draw_rectangle(0, 0, 151, 151, Color.BLACK) # 边框
    epd.draw_rectangle(5, 5, 146, 146, Color.BLACK) # 内边框
    
    # 绘制直线
    epd.draw_line(10, 10, 140, 140, Color.BLACK)
    epd.draw_line(10, 140, 140, 10, Color.BLACK)
    
    # 绘制填充矩形
    epd.draw_rectangle(20, 20, 50, 50, Color.BLACK, filled=True)
    
    # 绘制空心圆和填充圆
    epd.draw_circle(75, 75, 40, Color.BLACK)
    epd.draw_circle(75, 75, 20, Color.BLACK, filled=True)
    
    # 显示文本 (ASCII 08x06 字体)
    epd.show_string("Hello,", 60, 10, multiplier=1, color=Color.BLACK)
    epd.show_string("MicroPython!", 5, 60, multiplier=2, color=Color.BLACK) # 放大2倍
    epd.show_string("152x152", 5, 100, multiplier=3, color=Color.BLACK)    # 放大3倍
    
    # 显示一个小图标 (bitmap)
    heart_bitmap = [
        [0,1,0,1,0],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [0,1,1,1,0],
        [0,0,1,0,0]
    ]
    epd.show_bitmap(heart_bitmap, 120, 120, multiplier=1, color=Color.BLACK)
    
    # 4. 更新显示屏
    epd.update()
    print("Content displayed. Waiting 5 seconds...")
    time.sleep(5) # 显示内容5秒
    
    # 5. 清屏并显示新内容
    epd.clear(Color.WHITE) # 清屏
    epd.show_string("Cleared!", 20, 60, multiplier=3, color=Color.BLACK)
    epd.update()
    print("Screen cleared again and new text displayed. Waiting 3 seconds...")
    time.sleep(3)
    
    print("Demo finished.")

if __name__ == "__main__":
    main_demo()


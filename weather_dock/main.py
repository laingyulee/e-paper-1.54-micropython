# main.py
import time
import urequests # 用于HTTP请求
import json # 用于解析JSON
import network # 用于检查Wi-Fi连接状态
import ntptime # 用于时间同步
from machine import Pin, SPI, RTC
from il0373_cn import IL0373, Color, Rotate # 不再导入 fonts.py

# 导入配置
import config

# --- EPD 引脚定义 (从你的 config.py 读取) ---
spi_id = config.SPI_ID
sck_pin = config.SCK_PIN
mosi_pin = config.MOSI_PIN
res_pin = config.RES_PIN
dc_pin = config.DC_PIN
cs_pin = config.CS_PIN
busy_pin = config.BUSY_PIN

# MISO pin is not strictly needed for EPD, but SPI constructor might require it.
# If your board requires it, define an unused GPIO for MISO or connect to a dummy.
# For ESP32-S3, you might need to provide a MISO pin. Let's assume for now it's okay without it
# or you've handled it in your SPI setup. If not, add miso_pin=19 or similar.
# Example: miso_pin = 19
# spi_epd = SPI(spi_id, baudrate=4_000_000, polarity=0, phase=0, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))
spi_epd = SPI(spi_id, baudrate=4_000_000, polarity=0, phase=0, sck=Pin(sck_pin), mosi=Pin(mosi_pin))

busy = Pin(busy_pin, Pin.IN)
res = Pin(res_pin, Pin.OUT)
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
    rotate=Rotate.ROTATE_180, # 根据你的实际安装方向调整
    bg_color=Color.WHITE
)

print("EPD Driver initialized.")

# --- 优化后的天气图标 bitmaps (16x16 像素) ---

# 晴朗/太阳 ICON_SUNNY
ICON_SUNNY = [
    [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0], # Top rays
    [0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
    [0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
    [0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0],
    [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0], # Inner circle
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0],
    [0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
    [0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
    [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0], # Bottom rays
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# 多云 ICON_CLOUDY
ICON_CLOUDY = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0], # Main cloud
    [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# 下雨 ICON_RAIN (云朵+雨滴)
ICON_RAIN = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0], # Cloud
    [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0], # Rain drops
    [0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,0],
    [1,0,0,1,0,0,1,0,0,1,0,0,0,0,0,0],
    [0,0,1,0,0,1,0,0,1,0,0,0,0,0,0,0],
    [0,1,0,0,1,0,0,1,0,0,0,0,0,0,0,0],
    [1,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# 下雪 ICON_SNOW (云朵+雪花)
ICON_SNOW = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0], # Cloud
    [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [0,0,1,0,1,0,1,0,1,0,1,0,0,0,0,0], # Snowflakes
    [0,1,0,1,0,1,0,1,0,1,0,1,0,0,0,0],
    [0,0,1,0,1,0,1,0,1,0,1,0,0,0,0,0],
    [0,1,0,1,0,1,0,1,0,1,0,1,0,0,0,0],
    [0,0,1,0,1,0,1,0,1,0,1,0,0,0,0,0],
    [0,1,0,1,0,1,0,1,0,1,0,1,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# 晴朗夜晚 ICON_CLEAR_NIGHT (月亮+星星)
ICON_CLEAR_NIGHT = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0], # Moon
    [0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0],
    [0,0,0,1,1,1,0,1,1,0,0,0,0,0,0,0],
    [0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# 映射天气描述到图标
weather_icon_map = {
    "clear": ICON_SUNNY,
    "clouds": ICON_CLOUDY,
    "rain": ICON_RAIN,
    "drizzle": ICON_RAIN,
    "thunderstorm": ICON_RAIN,
    "snow": ICON_SNOW,
    "mist": ICON_CLOUDY, # Could add a foggy icon
    "haze": ICON_CLOUDY,
    "sand": ICON_CLOUDY,
    "dust": ICON_CLOUDY,
    "fog": ICON_CLOUDY,
    # Add more mappings as needed from OpenWeatherMap API
}


# 映射天气描述到图标的辅助函数
def get_weather_icon(description, current_hour):
    description_lower = description.lower()
    return weather_icon_map[description_lower]

# --- 功能函数 ---

def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        timeout = 10
        while not sta_if.isconnected() and timeout > 0:
            print('.', end='')
            time.sleep(1)
            timeout -= 1
        if sta_if.isconnected():
            print('\nnetwork config:', sta_if.ifconfig())
            return True
        else:
            print('\nFailed to connect to Wi-Fi.')
            return False
    else:
        return True

def sync_time():
    print("Synchronizing time with NTP server...")
    try:
        ntptime.host = "ntp.aliyun.com"
        ntptime.settime()
        print("Time synchronized.")
        
        rtc = RTC()
        current_time_tuple = time.localtime()
        
        current_timestamp = time.mktime(current_time_tuple)
        offset_timestamp = current_timestamp + (config.TIMEZONE_OFFSET * 3600)
        new_time_tuple = time.localtime(offset_timestamp)
        
        rtc.datetime((new_time_tuple[0], new_time_tuple[1], new_time_tuple[2], new_time_tuple[6],
                      new_time_tuple[3], new_time_tuple[4], new_time_tuple[5], 0))
        
        year, month, day, hour, minute, second, _, _ = time.localtime()
        formatted_time = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        print(f"Local time (UTC+{config.TIMEZONE_OFFSET}): {formatted_time}")
    except Exception as e:
        print(f"Failed to synchronize time: {e}")

def get_weather_data():
    api_url = f"http://api.openweathermap.org/data/2.5/weather?q={config.OPENWEATHER_CITY_NAME}&appid={config.OPENWEATHER_API_KEY}&units={config.OPENWEATHER_UNIT}&lang={config.OPENWEATHER_LANG}"
    print(f"Fetching weather from: {api_url}")
    try:
        response = urequests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            response.close()
            return data
        else:
            print(f"Error fetching weather: HTTP Status {response.status_code}")
            response.close()
            return None
    except Exception as e:
        print(f"Network or JSON error: {e}")
        return None

def display_clock_and_weather(epd, weather_data):
    epd.clear(Color.WHITE)
    
    current_time_tuple = time.localtime()
    year = current_time_tuple[0]
    month = current_time_tuple[1]
    day = current_time_tuple[2]
    hour = current_time_tuple[3]
    minute = current_time_tuple[4]
    weekday = current_time_tuple[6]
    
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    date_str = f"{year}-{month:02d}-{day:02d}"
    time_str = f"{hour:02d}:{minute:02d}"
    weekday_str = weekdays_zh[weekday]
    
    # 获取字体基本尺寸 (12x12)
    BASE_FONT_SIZE = epd.font_width # This will be 12 if fusion-pixel-12 is loaded
    LINE_HEIGHT = BASE_FONT_SIZE + 2 # 每行文本的垂直间距，比字体高一点
    
    # 定义一些常用的 X 坐标
    LEFT_MARGIN = 5
    RIGHT_MARGIN = epd.paint.width - 5
    CENTER_X = epd.paint.width // 2
    
    # --- 布局设计 (152x152 像素) ---
    # 所有文本都使用 12x12 BMF 字体
    # ---------------------------------------|
    # | 日期 (左)                  星期 (右)  | (y=5, 12x12)
    # | ------------------------------------ |
    # |            城市名称 (居中)            | (y=20, 12x12)
    # | ------------------------------------ |
    # |             HH:MM (居中,大)           | (y=40, 12x12, 放大2倍)
    # | -------------------------------------| (y=70, 分隔线)
    # | 图标 (左)         温度 (右, 大)       | (y=75, 图标32x32, 温度 12x12 放大2倍)
    # | 天气描述 (12x12)   体感温度 (右, 12x12)| (y=98)
    # |                                      | (y=110)
    # | 湿度 (左, 12x12)     气压 (右, 12x12) | (y=125)
    # | 风速 (左, 12x12) 日出/日落 (右, 12x12) | (y=138)
    # ------------------------------------

    # --- 垂直位置计算 ---
    y_current = 5 # 初始 Y 坐标
    
    # 1. 日期和星期 (12x12 BMF 字体)
    epd.show_string(date_str, LEFT_MARGIN, y_current, color=Color.BLACK)
    weekday_width = epd.get_string_display_width(weekday_str)
    epd.show_string(weekday_str, RIGHT_MARGIN - weekday_width, y_current, color=Color.BLACK)
    y_current += LINE_HEIGHT # 移动到下一行

    # 2. 城市名称 (12x12 BMF 字体)
    city_name = weather_data.get('name', "城市 N/A") if weather_data else "城市 N/A"
    city_name_width = epd.get_string_display_width(city_name)
    epd.show_string(city_name, CENTER_X - (city_name_width // 2), y_current, color=Color.BLACK)
    y_current += LINE_HEIGHT # 移动到下一行

    # 3. 时间 (12x12 BMF 字体，放大2倍 -> 24x24px)
    TIME_MULTIPLIER = 2
    time_displayed_font_size = BASE_FONT_SIZE * TIME_MULTIPLIER
    time_width = epd.get_string_display_width(time_str, multiplier=TIME_MULTIPLIER)
    epd.show_string(time_str, CENTER_X - (time_width // 2), y_current, multiplier=TIME_MULTIPLIER, color=Color.BLACK)
    epd.show_string(time_str, CENTER_X - (time_width // 2), y_current + 1, multiplier=TIME_MULTIPLIER, color=Color.BLACK)
    epd.show_string(time_str, CENTER_X - (time_width // 2) + 1, y_current, multiplier=TIME_MULTIPLIER, color=Color.BLACK)
    epd.show_string(time_str, CENTER_X - (time_width // 2) + 1, y_current + 1, multiplier=TIME_MULTIPLIER, color=Color.BLACK)

    y_current += time_displayed_font_size + 5 # 加上放大后的高度和额外间距

    # 4. 分隔线
    epd.draw_line(LEFT_MARGIN, y_current, RIGHT_MARGIN, y_current, Color.BLACK)
    y_current += 5 # 分隔线下方留白

    # 5. 天气信息
    if weather_data:
        weather_info = weather_data.get('weather', [{}])[0]
        weather_main = weather_info.get('main', "few clouds")
        weather_main_desc = weather_info.get('description', "未知")
        
        main_data = weather_data.get('main', {})
        current_temp = main_data.get('temp', 0.0)
        feels_like_temp = main_data.get('feels_like', 0.0)
        humidity = main_data.get('humidity', 0)
        pressure = main_data.get('pressure', 0)
        
        wind_data = weather_data.get('wind', {})
        wind_speed = wind_data.get('speed', 0.0)
        
        sys_data = weather_data.get('sys', {})
        sunrise_ts = sys_data.get('sunrise', 0)
        sunset_ts = sys_data.get('sunset', 0)
        
        rain_1h = weather_data.get('rain', {}).get('1h')
        
        sunrise_str = "N/A"
        sunset_str = "N/A"
        if sunrise_ts > 0:
            sunrise_local = time.localtime(sunrise_ts + (config.TIMEZONE_OFFSET * 3600))
            sunrise_str = f"{sunrise_local[3]:02d}:{sunrise_local[4]:02d}"
        if sunset_ts > 0:
            sunset_local = time.localtime(sunset_ts + (config.TIMEZONE_OFFSET * 3600))
            sunset_str = f"{sunset_local[3]:02d}:{sunset_local[4]:02d}"

        # 5.1 天气图标 (16x16, multiplier=2 -> 32x32) 和 当前温度 (12x12 BMF 字体，放大2倍 -> 24x24px)
        ICON_SIZE = 16 * 2 # 原始16x16，放大2倍
        icon_x = LEFT_MARGIN
        icon_y = y_current
        epd.show_bitmap(get_weather_icon(weather_main, hour), icon_x, icon_y, multiplier=2, color=Color.BLACK)
        
        # 5.2 天气描述 (12x12)，放置在体感温度下方
        desc_str = weather_main_desc
        DESC_MULTIPLIER = 1
        desc_str_display_width = epd.get_string_display_width(desc_str, multiplier=DESC_MULTIPLIER)
        epd.show_string(desc_str, LEFT_MARGIN + ICON_SIZE + 2, y_current + 8, multiplier=DESC_MULTIPLIER, color=Color.BLACK)

        # 5.3 当前温度 (放大2倍 -> 24x24px)，放置在图标右侧
        TEMP_MULTIPLIER = 2
        temp_str = f"{current_temp:.1f}°C"
        temp_str_display_width = epd.get_string_display_width(temp_str, multiplier=TEMP_MULTIPLIER)
        
        temp_x = RIGHT_MARGIN - temp_str_display_width
        temp_y = y_current
        epd.show_string(temp_str, temp_x, temp_y, multiplier=TEMP_MULTIPLIER, color=Color.BLACK)

        # 5.4 体感温度 (12x12)，放置在温度下方
        y_current_weather_info = y_current + (BASE_FONT_SIZE * TEMP_MULTIPLIER) # 从温度下方开始
        
        feels_str = f"体感: {feels_like_temp:.1f}°C"
        feels_str_display_width = epd.get_string_display_width(feels_str)
        epd.show_string(feels_str, RIGHT_MARGIN - feels_str_display_width, y_current_weather_info - 2, color=Color.BLACK)
        y_current = y_current_weather_info + LINE_HEIGHT +2

        
        # 5.5 湿度和气压 (12x12)
        humidity_str = f"湿度: {humidity}%"
        pressure_str = f"气压: {pressure}hPa"
        pressure_str_display_width = epd.get_string_display_width(pressure_str)
        
        epd.show_string(humidity_str, LEFT_MARGIN, y_current, color=Color.BLACK)
        epd.show_string(pressure_str, RIGHT_MARGIN - pressure_str_display_width, y_current, color=Color.BLACK)
        y_current += LINE_HEIGHT

        # 5.6 风速和日出/日落 (12x12)
        wind_str = f"风速: {wind_speed:.1f}m/s"
        epd.show_string(wind_str, LEFT_MARGIN, y_current, color=Color.BLACK)

        if rain_1h is not None and rain_1h > 0:
            rain_str = f"雨量: {rain_1h:.1f}mm"
            set_str_display_width = epd.get_string_display_width(set_str)
            epd.show_string(rain_str, RIGHT_MARGIN - set_str_display_width, y_current, color=Color.BLACK)
        y_current += LINE_HEIGHT
        
        rise_str = f"日出: {sunrise_str}"
        set_str = f"日落: {sunset_str}"
        set_str_display_width = epd.get_string_display_width(set_str)
        epd.show_string(rise_str, LEFT_MARGIN, y_current, color=Color.BLACK)
        epd.show_string(set_str, RIGHT_MARGIN - set_str_display_width, y_current, color=Color.BLACK)
        
    else:
        epd.show_string("天气数据 N/A", LEFT_MARGIN, y_current + 10, color=Color.BLACK)
        epd.show_string("请检查WiFi/API", LEFT_MARGIN, y_current + 10 + LINE_HEIGHT, color=Color.BLACK)
        epd.show_string("或等待刷新", LEFT_MARGIN, y_current + 10 + 2 * LINE_HEIGHT, color=Color.BLACK)
        
    epd.update()
    print(f"Display updated at {time_str}")

def main_weather_clock():
    print("Starting desktop weather clock...")
    epd.init()
    last_weather_update_time = 0
    weather_update_interval_sec = 30 * 60

    weather_data = None
    if do_connect():
        sync_time()
        weather_data = get_weather_data()
        last_weather_update_time = time.time()
    else:
        print("WiFi not connected, skipping initial weather and time update.")

    while True:
        current_unix_time = time.time()
        
        if current_unix_time - last_weather_update_time >= weather_update_interval_sec:
            if not network.WLAN(network.STA_IF).isconnected():
                print("Wi-Fi disconnected, attempting to reconnect...")
                if do_connect():
                    sync_time()
                else:
                    print("Could not reconnect to Wi-Fi. Skipping weather update.")
                    time.sleep(60)
                    continue
            
            weather_data = get_weather_data()
            last_weather_update_time = current_unix_time
            
        display_clock_and_weather(epd, weather_data)
        
        current_seconds = time.localtime()[5]
        sleep_seconds = 60 - current_seconds
        if sleep_seconds <= 0:
            sleep_seconds = 60
        
        print(f"Sleeping for {sleep_seconds} seconds until next minute...")
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    main_weather_clock()


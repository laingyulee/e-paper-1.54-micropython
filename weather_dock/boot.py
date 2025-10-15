# boot.py
import network
import time
import ntptime
from machine import Pin, RTC
import config # 导入你的配置

# Wi-Fi 连接
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
        print('Already connected to network.')
        print('network config:', sta_if.ifconfig())
        return True

# NTP 时间同步
def sync_time():
    print("Synchronizing time with NTP server...")
    try:
        ntptime.host = "ntp.aliyun.com" # You can choose other NTP servers
        ntptime.settime()
        print("Time synchronized.")
        # Apply timezone offset
        rtc = RTC()
        current_time = list(rtc.datetime())
        # Convert to seconds, add offset, convert back
        # MicroPython RTC is Y, M, D, W, H, M, S, MS
        current_timestamp = time.mktime((current_time[0], current_time[1], current_time[2],
                                          current_time[4], current_time[5], current_time[6], 0, 0))
        offset_timestamp = current_timestamp + (config.TIMEZONE_OFFSET * 3600)
        new_time_tuple = time.localtime(offset_timestamp)
        # Set RTC with new time (Y, M, D, W, H, M, S, 0)
        rtc.datetime((new_time_tuple[0], new_time_tuple[1], new_time_tuple[2], new_time_tuple[6],
                      new_time_tuple[3], new_time_tuple[4], new_time_tuple[5], 0))
        current_local_time = time.localtime()
        year, month, day, hour, minute, second, _, _ = current_local_time
        formatted_time = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        print(f"Local time (UTC+{config.TIMEZONE_OFFSET}): {formatted_time}")
    except Exception as e:
        print(f"Failed to synchronize time: {e}")

# 连接Wi-Fi并同步时间
if do_connect():
    sync_time()
else:
    print("Skipping time sync due to Wi-Fi connection failure.")

# 可以选择在这里禁用Wi-Fi以节省功耗，如果天气更新频率不高的话
# sta_if = network.WLAN(network.STA_IF)
# sta_if.active(False)
# print("Wi-Fi deactivated.")

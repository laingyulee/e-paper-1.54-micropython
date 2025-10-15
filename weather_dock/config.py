# config.py

# SPI number, set 1 for ESP32 serial boards.
SPI_ID = 1

# Pin Settings
SCK_PIN = 13
MOSI_PIN = 12 # Also called SDA pin
RES_PIN = 11
DC_PIN = 10
CS_PIN = 9
BUSY_PIN = 8

# Wi-Fi Configuration
WIFI_SSID = "WIFI_SSID"
WIFI_PASSWORD = "WIFI_PASSWORD"

# OpenWeatherMap API Configuration
# Get your API key from https://openweathermap.org/api
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"

# Find your city ID: http://bulk.openweathermap.org/sample/city.list.json.gz
# Or search on their website for your city and check the URL for the ID.
OPENWEATHER_CITY_NAME = "Wuhan" # e.g. Wuhan, Beijing, New York  
OPENWEATHER_UNIT = "metric" # "metric" for Celsius, "imperial" for Fahrenheit
OPENWEATHER_LANG = "zh_cn" # Language for weather description (e.g., "zh_cn", "en")

# Timezone offset in hours from UTC.
# For example, Beijing is UTC+8, so TIMEZONE_OFFSET = 8
TIMEZONE_OFFSET = 8 # Adjust for your timezone

INTERVAL = 60 * 60
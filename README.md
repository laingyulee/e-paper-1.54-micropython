# e-paper-1.54-micropython

![IMG_6243](https://github.com/user-attachments/assets/a4fb1e1d-dcdd-49d1-b037-9920e5d48f90)

Driver for 1.54 inch (152x152, IL0373) e-Paper 2 colour display on ESP32 with micropython.

Migrated from Arduino driver at https://github.com/ZinggJM/GxEPD/tree/master/src/GxGDEW0154T8, credit goes to @ZinggJM.

For English user, please download il0737.py and fonts.py, and refer to demo.py for usage.

1.54寸双色电纸屏Micropython驱动（分辨率152x152，驱动芯片IL0373）

感谢@ZinggJM大佬发布的Arduino驱动，由该驱动移植而来。

如果只需展示英文字符，下载il0737.py和fonts.py文件即可，如需中文支持，继续往下看。

## Chinese Support / 中文支持

Please goto `Chinese` subfolder.

Added Simplified Chinese support, with a BMF pixel font from Unifont (Size 12). This font class supports a 'mutiplier' parameter for enlarged display (eg. 2x, 3x).

Chinese support version removed original alphabet font (the fonts.py file).

Chinese support version ships with a simple demo.

参考 `Chinese` 文件夹下的内容。

增加了中文支持，采用Unifont 12号字体的bmf点阵格式，支持倍数放大。

中文字体包含英文字符，因此移除了英文字库。

类文件自带一个demo，请参考使用。

## Weather Dock / 天气钟程序

![IMG_6245](https://github.com/user-attachments/assets/68238779-2faa-4311-8b36-f31fa55e251b)

Added a weather dock demo, using OpenWeatherMap API for weather data. This demo displays in Chinese only.

我做了一个天气钟演示这个墨水屏的功能。使用OpenWeatherMap API获取天气数据。界面是中文的哟。

下载weather_dock目录下的文件，以及chinese目录下的文件，放到一块，然后打开config.py，配置你的引脚、OpenWeatherMap API密钥和你所在的位置。

> Get your API key from https://openweathermap.org/api

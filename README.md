# e-paper-1.54-micropython

Driver for 1.54 inch (152x152, IL0373) e-Paper 2 colour display on ESP32 with micropython.

1.54寸双色电纸屏Micropython驱动（分辨率152x152，驱动芯片IL0373）

Migrated from Arduino driver at https://github.com/ZinggJM/GxEPD/tree/master/src/GxGDEW0154T8, credit goes to @ZinggJM.

感谢@ZinggJM大佬发布的Arduino驱动，由该驱动移植而来。


![IMG_6243](https://github.com/user-attachments/assets/a4fb1e1d-dcdd-49d1-b037-9920e5d48f90)


## Chinese Support / 中文支持

增加了中文支持，采用Unifont 12号字体的bmf点阵格式，支持倍数放大。

Added Simplified Chinese support, with a BMF pixel font from Unifont (Size 12). This font class supports a 'mutiplier' parameter for enlarged display (eg. 2x, 3x).

中文字体包含英文字符，因此移除了英文字库。

Chinese support version removed original alphabet font (the fonts.py file).

类文件自带一个demo，请参考使用。

Chinese support version ships with a simple demo.

#coding = utf-8
import serial
from serial.serialutil import PARITY_NONE

ser_light = serial.Serial(port = "COM5",baudrate = 9600,bytesize = 8,parity = PARITY_NONE,stopbits = 1)
if not ser_light.is_open:
    ser_light.open()
    print("端口未打开\n已将端口打开")

#for_input = "01 05 00 00 ff 00 8C 3A"
#ser_light.write(bytes.fromhex(for_input))
R_open = "01 05 00 00 ff 00 8C 3A"
R_close = "01 05 00 00 00 00 CD CA"
Y_open = "01 05 00 01 ff 00 DD FA"
Y_close = "01 05 00 01 00 00 9C 0A"
G_open = "01 05 00 02 ff 00 2D FA"
G_close = "01 05 00 02 00 00 6C 0A"
Bell_open = "01 05 00 03 ff 00 7C 3A"
Bell_close = "01 05 00 03 00 00 3D CA"
All_open = "01 05 00 FF FF 00 BC 0A"
All_close = "01 05 00 EF FF 00 BD CF"

R_2Hz = "01 05 00 00 f0 00 89 CA"
R_1Hz = "01 05 00 00 f1 00 88 5A"
R_05Hz = "01 05 00 00 f2 00 88 AA"
R_025Hz = "01 05 00 00 f3 00 89 3A"

Y_2Hz = "01 05 00 01 f0 00 D8 0A"
Y_1Hz = "01 05 00 01 f1 00 D9 9A"
Y_05Hz = "01 05 00 01 f2 00 D9 6A"
Y_025Hz = "01 05 00 01 f3 00 D8 FA"

G_2Hz = "01 05 00 02 f0 00 28 0A"
G_1Hz = "01 05 00 02 F1 00 29 9A"
G_05Hz = "01 05 00 02 f2 00 29 6A"
G_025Hz = "01 05 00 02 f3 00 28 FA"

Bell_2Hz = "01 05 00 03 f0 00 79 CA"
Bell_1Hz = "01 05 00 03 f1 00 78 5A"
Bell_05Hz = "01 05 00 03 f2 00 78 AA"
Bell_025Hz = "01 05 00 03 f3 00 79 3A"

ser_light.write(bytes.fromhex(R_open))

ser_light.close()
print("端口已关闭")

print("输入任意键退出")
_ = input()
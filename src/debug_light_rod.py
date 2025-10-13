# debug_traffic_light.py

import argparse
import time

import serial
from PySide6.QtCore import QObject  # For compatibility

from tools import LoggerMixin, setup_logger


class TrafficLightController(QObject, LoggerMixin):
	# 从 alarm_manager.py 提取的三色灯控制器
	COMMANDS = {
		'red_on': bytes.fromhex('01 05 00 00 ff 00 8C 3A'),
		'green_on': bytes.fromhex('01 05 00 02 ff 00 2D FA'),
		'buzzer_on': bytes.fromhex('01 05 00 03 ff 00 7C 3A'),
		'all_off': bytes.fromhex('01 05 00 EF FF 00 BD CF'),
		'red_flash_1hz': bytes.fromhex('01 05 00 00 f1 00 88 5A'),
		'buzzer_1hz': bytes.fromhex('01 05 00 03 f1 00 78 5A'),
	}

	def __init__(self, port: str, baudrate: int):
		super().__init__()
		self.port = port
		self.baudrate = baudrate
		self.serial_conn = None
		self.is_connected = False

	def connect_serial(self) -> bool:
	#注意QObject本身有connect方法（信号和槽），所以不要命名为connect
		try:
			self.serial_conn = serial.Serial(
				port=self.port,
				baudrate=self.baudrate,
				timeout=1)
			self.is_connected = True
			self.logger.info(f"三色灯连接成功: {self.port}")
			return True
		except Exception as e:
			self.is_connected = False
			self.logger.error(f"三色灯连接失败: {e}")
			return False

	def disconnect_serial(self) -> None:
		if self.serial_conn and self.serial_conn.is_open:
			self.serial_conn.close()
		self.is_connected = False
		self.logger.info("三色灯已断开连接")

	def send_command(self, command_name: str) -> bool:
		if not self.is_connected: return False
		command = self.COMMANDS.get(command_name)
		if not command:
			self.logger.error(f"未知指令: {command_name}")
			return False
		try:
			self.serial_conn.write(command)
			self.logger.debug(f"发送指令: {command_name} -> {command.hex()}")
			return True
		except Exception as e:
			self.logger.error(f"发送指令失败: {e}")
			return False

	def set_normal_status(self) -> bool:
		self.logger.info("设置状态为 [正常]: 绿灯常亮")
		self.send_command('all_off')
		time.sleep(0.1)
		return self.send_command('green_on')

	def set_alarm_status(self) -> bool:
		self.logger.info("设置状态为 [报警]: 红灯闪烁")
		self.send_command('all_off')
		time.sleep(0.1)
		return self.send_command('red_flash_1hz')

	def all_off(self) -> bool:
		self.logger.info("设置状态为 [全部关闭]")
		return self.send_command('all_off')


def main():
	parser = argparse.ArgumentParser(description="调试三色报警灯功能")
	parser.add_argument("--port", type=str, required=True, help="三色灯的 COM 端口号, e.g., COM1")
	parser.add_argument("--baudrate", type=int, default=9600, help="波特率")
	parser.add_argument("action", choices=['alarm', 'normal', 'off'],
						help="要执行的动作: 'alarm' (报警), 'normal' (恢复正常), 'off' (关闭)")
	args = parser.parse_args()

	setup_logger()
	light = TrafficLightController(port=args.port, baudrate=args.baudrate)

	try:
		if light.connect_serial():
			success = False
			if args.action == 'alarm':
				success = light.set_alarm_status()
			elif args.action == 'normal':
				success = light.set_normal_status()
			elif args.action == 'off':
				success = light.all_off()

			print("\n" + "=" * 20 + " 执行结果 " + "=" * 20)
			if success:
				print(f"  指令 '{args.action}' 发送成功。")
			else:
				print(f"  指令 '{args.action}' 发送失败。")
			print("=" * 52 + "\n")
		else:
			print(f"\n错误：无法连接到端口 {args.port}，请检查设备连接和端口号。\n")
	finally:
		light.disconnect_serial()


if __name__ == "__main__":
	main()
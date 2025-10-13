# debug_ln2_reader.py

import argparse
import time
from typing import Dict, Optional

from pymodbus.client import ModbusTcpClient
from PySide6.QtCore import QObject  # pymodbus internally may use Qt, so keep it for compatibility

from tools import LoggerMixin, setup_logger


class LN2SeparatorReader(QObject, LoggerMixin):
	"""
	从 external_data_source.py 提取的液氮分离器数据读取器类
	"""
	LIQUID_LEVEL_ADDRESS = 0  # 40001 对应的实际地址
	PRESSURE_ADDRESS = 1  # 40002 对应的实际地址

	def __init__(self, host: str, port: int, unit_id: int = 1):
		super().__init__()
		self.host = host
		self.port = port
		self.unit_id = unit_id
		self.client: Optional[ModbusTcpClient] = None
		self.is_connected = False
		self.logger.info(f"液氮分离器读取器初始化: {host}:{port}")

	def connect_LN2(self) -> bool:
		try:
			self.client = ModbusTcpClient(host=self.host, port=self.port, timeout=5)
			if self.client.connect():
				self.is_connected = True
				self.logger.info(f"成功连接到 PLC: {self.host}:{self.port}")
				return True
			else:
				self.is_connected = False
				self.logger.error(f"无法连接到 PLC: {self.host}:{self.port}")
				return False
		except Exception as e:
			self.is_connected = False
			self.logger.error(f"连接 PLC 时发生错误: {e}", exc_info=True)
			return False

	def disconnect_LN2(self) -> None:
		try:
			if self.client:
				self.client.close()
			self.is_connected = False
			self.logger.info("已断开 PLC 连接")
		except Exception as e:
			self.logger.error(f"断开 PLC 连接时发生错误: {e}")

	def read_holding_register(self, address: int) -> Optional[int]:
		if not self.is_connected or not self.client:
			return None
		try:
			result = self.client.read_holding_registers(address, count=1, device_id=self.unit_id)
			if result.isError():
				self.logger.error(f"读取寄存器失败, 地址: {address}, 错误: {result}")
				return None
			return result.registers[0]
		except Exception as e:
			self.logger.error(f"读取寄存器时发生异常, 地址: {address}: {e}")
			return None

	def read_current_data(self) -> Dict[str, Optional[float]]:
		if not self.is_connected:
			return {"液位": None, "压力": None}

		self.logger.info("开始读取数据...")
		liquid_level_raw = self.read_holding_register(self.LIQUID_LEVEL_ADDRESS)
		time.sleep(0.1)  # 短暂延时避免 PLC 响应不及
		pressure_raw = self.read_holding_register(self.PRESSURE_ADDRESS)

		liquid_level = float(liquid_level_raw) if liquid_level_raw is not None else None
		pressure = float(pressure_raw) / 100.0 if pressure_raw is not None else None  # 转换为 MPa

		return {"液位": liquid_level, "压力": pressure}


def main():
	parser = argparse.ArgumentParser(description="调试液氮分离器数据读取功能")
	parser.add_argument("--host", type=str, default="192.168.0.200", help="PLC的IP地址")
	parser.add_argument("--port", type=int, default=502, help="Modbus TCP 端口")
	args = parser.parse_args()

	setup_logger()

	reader = LN2SeparatorReader(host=args.host, port=args.port)

	try:
		if reader.connect_LN2():
			data = reader.read_current_data()
			print("\n" + "=" * 20 + " 读取结果 " + "=" * 20)
			if data["液位"] is not None:
				print(f"  液氮分离器液位: {data['液位']} mm")
			else:
				print("  液氮分离器液位: 读取失败")

			if data["压力"] is not None:
				print(f"  液氮分离器压力: {data['压力']:.2f} MPa")
			else:
				print("  液氮分离器压力: 读取失败")
			print("=" * 52 + "\n")
		else:
			print("\n错误：无法连接到设备，请检查网络和IP地址。\n")

	finally:
		reader.disconnect_LN2()


if __name__ == "__main__":
	main()
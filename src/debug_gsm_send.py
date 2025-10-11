# debug_gsm_sms.py

import argparse
import time
from typing import Tuple

import serial
from PySide6.QtCore import QObject  # For compatibility

from helpers import LoggerMixin, setup_logger


class SMSPDUError(Exception):
	pass

class SMSPDUCodec:
	# 从 alarm_manager.py 提取的 PDU 编解码器
	def __init__(self, sms_center: str = "+8613344181200"):
		self.sms_center = sms_center

	def _encode_phone_number(self, phone: str) -> str:
		if not phone:
			raise SMSPDUError("手机号码不能为空")
		normalized_phone = phone[3:] if phone.startswith("+86") else (phone[1:] if phone.startswith('+') else phone)
		if len(normalized_phone) % 2 == 1: normalized_phone += 'F'
		encoded_digits = "".join(
			[normalized_phone[i + 1] + normalized_phone[i] for i in range(0, len(normalized_phone), 2)])
		address_type = 0x91 if phone.startswith('+') else 0x81
		return f"{len(normalized_phone) - 1 if 'F' in normalized_phone else len(normalized_phone):02X}{address_type:02X}{encoded_digits}"

	def _encode_sms_center(self, sms_center: str) -> str:
		if not sms_center: return "00"
		normalized = sms_center[1:] if sms_center.startswith('+') else sms_center
		if len(normalized) % 2 == 1: normalized += 'F'
		encoded_digits = "".join([normalized[i + 1] + normalized[i] for i in range(0, len(normalized), 2)])
		return f"{(1 + len(encoded_digits) // 2):02X}91{encoded_digits}"

	def encode_sms(self, phone: str, message: str) -> str:
		sca = self._encode_sms_center(self.sms_center)
		pdu_type = 0x11
		da = self._encode_phone_number(phone)
		user_data = message.encode('utf-16-be').hex().upper()
		udl = len(user_data) // 2
		return f"{sca}{pdu_type:02X}00{da}0008AA{udl:02X}{user_data}"

	def get_pdu_length(self, pdu: str) -> int:
		sca_length = int(pdu[0:2], 16)
		return (len(pdu) - (sca_length + 1) * 2) // 2


class GSMController(QObject, LoggerMixin):
	# 从 alarm_manager.py 提取的 GSM 控制器
	def __init__(self, port: str, baudrate: int):
		super().__init__()
		self.port = port
		self.baudrate = baudrate
		self.serial_conn = None
		self.is_connected = False
		self.pdu_codec = SMSPDUCodec()

	def connect_gsm(self) -> bool:
		try:
			self.serial_conn = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=5)
			self.is_connected = True
			self.logger.info(f"GSM 模块连接成功: {self.port}")
			return True
		except Exception as e:
			self.is_connected = False
			self.logger.error(f"GSM 模块连接失败: {e}")
			return False

	def disconnect_gsm(self) -> None:
		if self.serial_conn and self.serial_conn.is_open:
			self.serial_conn.close()
		self.is_connected = False
		self.logger.info("GSM 模块已断开连接")

	# --- MODIFIED FUNCTION ---
	def send_at_command(self, command: str, timeout: float = 5.0) -> Tuple[bool, str]:
		"""发送 AT 指令并等待响应 (已修改为调试模式)"""
		if not self.is_connected or not self.serial_conn:
			return False, "模块未连接"

		try:
			# 清理缓冲区，确保接收到的是本次命令的响应
			self.serial_conn.reset_input_buffer()

			# 发送指令，AT指令需要以回车符(\r)结尾
			cmd_bytes = (command + '\r').encode('ascii')
			self.serial_conn.write(cmd_bytes)
			self.logger.info(f"发送 AT 指令: {command}")

			# 使用循环读取数据，比 read_until 更可靠
			response_bytes = b''
			start_time = time.time()
			while time.time() - start_time < timeout:
				if self.serial_conn.in_waiting > 0:
					response_bytes += self.serial_conn.read(self.serial_conn.in_waiting)
					# 提前结束的条件：收到 OK 或 ERROR 或 > (等待输入)
					if any(terminator in response_bytes for terminator in [b'OK', b'ERROR', b'>']):
						# 再稍等一下，确保接收完整
						time.sleep(0.05)
						if self.serial_conn.in_waiting > 0:
							response_bytes += self.serial_conn.read(self.serial_conn.in_waiting)
						break
				time.sleep(0.1)

			# === 核心调试代码：直接在控制台打印原始返回值 ===
			print("\n" + ("-" * 20))
			print(f"命令 '{command}' 的原始返回值 (bytes):")
			print(response_bytes)
			print("-" * 20)
			# ============================================

			# 解码并判断结果
			response_str = response_bytes.decode('ascii', 'ignore')
			success = 'OK' in response_str or '>' in response_str

			self.logger.debug(f"AT 指令响应 (decoded): {response_str.strip()}")
			return success, response_str.strip()

		except Exception as e:
			self.logger.error(f"发送AT指令时发生异常: {e}", exc_info=True)
			return False, str(e)

	# --- MODIFIED FUNCTION ---
	def send_sms(self, phone: str, message: str) -> bool:
		"""发送短信 (已修改最终响应的读取逻辑)"""
		self.logger.info(f"准备向 {phone} 发送短信: '{message}'")
		try:
			pdu = self.pdu_codec.encode_sms(phone, message)
			pdu_length = self.pdu_codec.get_pdu_length(pdu)

			self.logger.info("设置 PDU 模式 (AT+CMGF=0)")
			ok, _ = self.send_at_command("AT+CMGF=0")
			if not ok: return False
			time.sleep(0.5)

			self.logger.info(f"发送 CMGS 指令 (AT+CMGS={pdu_length})")
			ok, response = self.send_at_command(f"AT+CMGS={pdu_length}", timeout=3.0)
			if not ok or '>' not in response:
				self.logger.error(f"CMGS 指令失败, 响应: {response}")
				return False
			time.sleep(0.5)

			self.logger.info("发送 PDU 数据和 CTRL+Z...")
			self.serial_conn.write(pdu.encode('ascii'))
			self.serial_conn.write(bytes([0x1A]))  # CTRL+Z

			# === 核心修改部分：使用可靠的循环方式读取最终响应 ===
			self.logger.info("等待短信发送最终确认...")
			final_response_bytes = b''
			start_time = time.time()
			# 短信发送可能需要较长时间，设置15秒超时
			while time.time() - start_time < 15.0:
				if self.serial_conn.in_waiting > 0:
					final_response_bytes += self.serial_conn.read(self.serial_conn.in_waiting)
					# 收到 OK 或 ERROR 就认为响应结束
					if b'OK' in final_response_bytes or b'ERROR' in final_response_bytes:
						break
				time.sleep(0.2)  # 避免CPU空转

			# 同样打印出原始返回值用于调试
			print("\n" + ("-" * 20))
			print(f"PDU 发送后的原始返回值 (bytes):")
			print(final_response_bytes)
			print("-" * 20)

			self.logger.debug(f"PDU 发送响应 (decoded): {final_response_bytes.decode('ascii', 'ignore').strip()}")
			# 最终的成功判断
			return b'OK' in final_response_bytes
		# =======================================================
		except Exception as e:
			self.logger.error(f"发送短信时发生异常: {e}", exc_info=True)
			return False


def main():
	parser = argparse.ArgumentParser(description="调试 GSM 模块短信发送功能")
	parser.add_argument("--port", type=str, default="COM8", help="GSM 模块的 COM 端口号, e.g., COM3")
	parser.add_argument("--baudrate", type=int, default=115200, help="波特率")
	parser.add_argument("--phone", type=str, default="17712689742", help="接收短信的手机号码")
	parser.add_argument("--message", type=str, default="这是一条来自点检系统的测试短信。", help="短信内容")
	args = parser.parse_args()

	setup_logger()
	gsm = GSMController(port=args.port, baudrate=args.baudrate)

	try:
		if gsm.connect_gsm():
			print("\n正在检查模块状态...")
			ok, resp = gsm.send_at_command("AT")
			print(f"AT -> {'成功' if ok else '失败'}")
			if not ok: return

			ok, resp = gsm.send_at_command("AT+CPIN?")
			print(f"AT+CPIN? (SIM卡状态) -> {'成功' if ok and 'READY' in resp else '失败'}")
			if not ok or 'READY' not in resp: return

			ok, resp = gsm.send_at_command("AT+CSQ")
			print(f"AT+CSQ (信号质量) -> {resp.splitlines()[1] if ok else '失败'}")

			print("\n准备发送短信...")
			success = gsm.send_sms(args.phone, args.message)

			print("\n" + "=" * 20 + " 发送结果 " + "=" * 20)
			if success:
				print(f"  短信成功发送至 {args.phone}")
			else:
				print(f"  短信发送失败，请检查日志 logs/debug_console.log 获取详细信息。")
			print("=" * 52 + "\n")
		else:
			print(f"\n错误：无法连接到端口 {args.port}，请检查设备连接和端口号。\n")
	finally:
		gsm.disconnect_gsm()


if __name__ == "__main__":
	main()
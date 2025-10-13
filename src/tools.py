import sys
import psutil
import ctypes
import functools
import logging
import logging.handlers
from pathlib import Path

BlockInput = ctypes.windll.user32.BlockInput


def run_as_admin():
	"""检查当前用户是否为管理员"""
	if ctypes.windll.shell32.IsUserAnAdmin():
		return
	else:
		# 如果不是管理员，则以管理员权限重新运行此脚本
		print("权限不足，正在尝试以管理员身份重新启动...")
		try:
			# 使用 ShellExecuteW 重新启动脚本
			# sys.executable 是 python 解释器的路径
			# " ".join(sys.argv) 是当前脚本的路径和所有参数
			ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
			# 成功发起提权请求后，退出当前这个没有权限的进程
			sys.exit(0)
		except Exception as e:
			print(f"提权失败: {e}")
			# 如果用户在UAC窗口点击“否”，也会触发异常
			sys.exit(1)


def get_pids_by_name(process_name):
	"""根据进程名获取所有匹配的PID列表"""
	pids = []
	for proc in psutil.process_iter(['pid', 'name']):
		if proc.info['name'].lower() == process_name.lower():
			pids.append(proc.info['pid'])
	return pids


def block_input(func):
	"""
	一个装饰器，用于在函数执行期间阻止物理键鼠输入。
	它确保了即使函数执行出错，输入锁定也总能被解除。
	"""

	@functools.wraps(func)  # 保持原函数的元信息（如函数名、文档字符串）
	def wrapper(*args, **kwargs):
		print(f"--- [装饰器] 准备执行 '{func.__name__}'，即将锁定输入。 ---")
		locked = False
		try:
			# 锁定物理输入
			if BlockInput(True):
				locked = True
				print("--- [装饰器] 物理输入已锁定。---")
			else:
				print("--- [装饰器] 警告：无法锁定输入！---")

			# 执行原始的、被装饰的函数
			result = func(*args, **kwargs)
			return result

		# 这里我们不捕获异常，让它正常抛出，但 finally 仍然会执行

		finally:
			if locked:
				# 解锁物理输入
				BlockInput(False)
				print(f"--- [装饰器] 物理输入已解锁。---")
			print(f"--- [装饰器] '{func.__name__}' 执行完毕。 ---")

	return wrapper

def setup_logger(log_level: int = logging.INFO) -> None:
	"""
	为控制台程序设置一个简单的日志记录器
	"""
	log_dir = Path("logs")
	log_dir.mkdir(exist_ok=True)
	log_file = log_dir / "debug_console.log"

	formatter = logging.Formatter(
		fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S'
	)

	# 配置根日志器
	root_logger = logging.getLogger()
	root_logger.setLevel(log_level)
	root_logger.handlers.clear()

	# 文件处理器
	file_handler = logging.handlers.RotatingFileHandler(
		log_file, maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8'
	)
	file_handler.setFormatter(formatter)
	root_logger.addHandler(file_handler)

	# 控制台处理器
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	root_logger.addHandler(console_handler)

	logging.info("=" * 20 + " Logger Initialized " + "=" * 20)


class LoggerMixin:
	"""
	为其他类提供日志功能的混入类
	"""

	@property
	def logger(self) -> logging.Logger:
		return logging.getLogger(self.__class__.__name__)


if __name__ == "__main__":
	molly_pids = get_pids_by_name("Clash for Windows.exe")
	print(f"找到了以下名为 'molly.exe' 的进程 PID: {molly_pids}")
# 输出可能像这样: [1234, 5678, 9012]

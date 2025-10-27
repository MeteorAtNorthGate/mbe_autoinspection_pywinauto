# -*- coding: utf-8 -*-

"""
这是一个可直接运行的 Python 脚本，用于从 Molly 2000 面板获取数据。
它结合了 pywinauto, OpenCV, 和 Tesseract OCR。

*** 优化版工作流 ***
1.  **短暂交互**: 脚本会一次性完成所有GUI操作（获取文本、获取控件坐标、截取主窗口图像）。
2.  **离线分析**: 之后的所有图像处理（像素取色、OCR）都在截取的图像上进行，不再打扰GUI。

安装前置库:
pip install pywinauto opencv-python pytesseract numpy pyautogui

注意:
1. 请确保已安装 Google Tesseract OCR 引擎并将其添加到系统的 PATH 环境变量中。
2. Tesseract 是一个完全离线的工具，运行时不会联网。
"""

import cv2
import numpy as np
import pyautogui
import pytesseract
from pywinauto.application import Application

from tools import get_pids_by_name

# --- 1. 用户配置 (User Configuration) ---
MOLLY_MAIN_PANEL = "Lbar5.exe"


# 如果 Tesseract OCR 引擎不在系统的 PATH 环境变量中，请取消下面的注释并指定其可执行文件路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# --- 2. 辅助函数 (Helper Functions) ---

def find_controls_and_print(window):
	"""
    打印指定窗口下的所有控件信息，帮助用户定位控件。
    """
	print("=" * 80)
	print(f"正在为窗口 '{window.window_text()}' 打印所有控件信息...")
	print("请根据下面的 'child_window' 信息来修改脚本中的控件定位参数。")
	window.print_control_identifiers(depth=4)  # 增加深度以查看更多细节
	print("=" * 80)


def get_shutter_status_from_image(main_screenshot_bgr, main_win_coords, panel_coords):
	"""
    (离线分析) 从已截取的图像中通过像素颜色获取快门状态。
    """
	# 这些是指示灯相对于其面板左上角的偏移量，需要您精确测量
	relative_x_offset = 20
	relative_y_offset = 15

	# 计算指示灯在截图中的相对坐标
	# 绝对坐标 -> 截图内的相对坐标
	dot_relative_x = (panel_coords.left + relative_x_offset) - main_win_coords.left
	dot_relative_y = (panel_coords.top + relative_y_offset) - main_win_coords.top

	# 从截图中直接读取像素颜色 (注意OpenCV的BGR顺序)
	b, g, r = main_screenshot_bgr[dot_relative_y, dot_relative_x]

	# 定义颜色阈值
	GREEN_R_MAX, GREEN_G_MIN, GREEN_B_MAX = 80, 200, 80
	RED_R_MIN, RED_G_MAX, RED_B_MAX = 200, 80, 80

	if g > GREEN_G_MIN and r < GREEN_R_MAX and b < GREEN_B_MAX:
		return "Open"
	elif r > RED_R_MIN and g < RED_G_MAX and b < RED_B_MAX:
		return "Closed"
	else:
		return f"Unknown (R={r}, G={g}, B={b})"


def get_reading_ocr_from_image(main_screenshot_bgr, main_win_coords, panel_coords, whitelist):
	"""
    (离线分析) 从已截取的图像中 OCR 获取仪表读数。
    """
	try:
		# 1. 计算要裁剪区域在主截图中的相对坐标
		crop_x_start = panel_coords.left - main_win_coords.left
		crop_y_start = panel_coords.top - main_win_coords.top
		crop_x_end = panel_coords.right - main_win_coords.left
		crop_y_end = panel_coords.bottom - main_win_coords.top

		# 2. 从主截图中裁剪出目标区域
		cropped_image = main_screenshot_bgr[crop_y_start:crop_y_end, crop_x_start:crop_x_end]

		# --- 图像预处理 ---
		# 3. 转换为灰度图
		gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
		# 4. 增强对比度
		contrast_image = cv2.convertScaleAbs(gray_image, alpha=2.0, beta=0)

		# --- OCR 配置 ---
		custom_config = f'--psm 7 -c tessedit_char_whitelist={whitelist}'
		text = pytesseract.image_to_string(contrast_image, config=custom_config)
		return text.strip()
	except Exception as e:
		return f"OCR Error: {e}"


# --- 3. 主逻辑 (Main Logic) ---

def main():
	"""Main execution function."""
	# --- 阶段 1: 短暂的GUI交互 ---
	try:
		molly_pid = get_pids_by_name(MOLLY_MAIN_PANEL)[0]
	except:
		print("could not get access to molly !")
		raise
	try:
		print("--- [阶段 1] 开始与GUI进行短暂交互 ---")
		print(f"正在连接到进程 PID: {molly_pid}...")
		app = Application(backend="win32").connect(process=molly_pid)
		main_window = app.window(title_re="Molly 2000.*")
		main_window.wait('visible', timeout=10)
		main_window.set_focus()
		print(f"成功连接到主窗口: '{main_window.window_text()}'")

		# 运行此函数来查找您需要的控件信息！
		# find_controls_and_print(main_window)

		# 1a. 获取所有需要交互的控件
		### TODO ###: 根据 find_controls_and_print 的输出修改这里的定位参数
		reactor_panel = main_window.child_window(class_name="ListView20WndClass",found_index=3)
		shutter_panel = main_window.child_window(title="Shutter", found_index=0)
		vacuum_gauge_panel = main_window.child_window(class_name="Static", found_index=10)
		temp_gauge_panel = main_window.child_window(class_name="Static", found_index=12)

		# 1b. 一次性获取所有文本和坐标
		reactor_texts = reactor_panel.texts()
		main_win_coords = main_window.rectangle()
		shutter_coords = shutter_panel.rectangle()
		vacuum_coords = vacuum_gauge_panel.rectangle()
		temp_coords = temp_gauge_panel.rectangle()

		# 1c. 截取整个主窗口的图像
		screenshot_pil = pyautogui.screenshot(region=(
			main_win_coords.left, main_win_coords.top,
			main_win_coords.width(), main_win_coords.height()
		))
		# 将图像转换为OpenCV格式，为后续处理做准备
		main_screenshot_bgr = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)

		print("--- GUI交互完成。所有后续操作均为离线分析 ---")

	except Exception as e:
		print(f"\n在GUI交互阶段发生错误: {e}")
		print("请确认 PID 是否正确，以及所有控件定位参数是否准确。")
		return

	# --- 阶段 2: 离线图像和数据分析 ---
	print("\n--- [阶段 2] 开始离线数据分析 ---")

	# 分析任务1: 处理源炉数据
	print("\n[分析 1] 处理源炉数据...")
	if reactor_texts:
		print(f"源炉面板数据 (前5行): {reactor_texts[:5]}")
	else:
		print("未能获取源炉数据。")

	# 分析任务2: 分析快门状态
	print("\n[分析 2] 分析快门状态...")
	try:
		shutter_status = get_shutter_status_from_image(main_screenshot_bgr, main_win_coords, shutter_coords)
		print(f"快门 1 状态: {shutter_status}")
	except Exception as e:
		print(f"分析快门状态失败: {e}")

	# 分析任务3: OCR识别仪表读数
	print("\n[分析 3] OCR识别仪表读数...")
	try:
		vacuum_whitelist = '0123456789.E-'
		vacuum_reading = get_reading_ocr_from_image(main_screenshot_bgr, main_win_coords, vacuum_coords,
													vacuum_whitelist)
		print(f"真空计读数: {vacuum_reading}")
	except Exception as e:
		print(f"OCR识别真空计失败: {e}")

	try:
		temp_whitelist = '0123456789Kk.'
		temp_reading = get_reading_ocr_from_image(main_screenshot_bgr, main_win_coords, temp_coords, temp_whitelist)
		print(f"冷泵温度读数: {temp_reading}")
	except Exception as e:
		print(f"OCR识别冷泵温度失败: {e}")

	print("\n--- 所有分析任务完成 ---")


if __name__ == "__main__":
	main()


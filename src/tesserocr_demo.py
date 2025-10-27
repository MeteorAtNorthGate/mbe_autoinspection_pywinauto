from PIL import Image, ImageDraw, ImageFont
import os
import time
# 导入 tesserocr 模块，注意导入的名称
from tesserocr import PyTessBaseAPI, PSM, OEM


# --- 辅助函数：创建一个用于演示的PNG图片 ---
# (与之前版本相同)
def create_dummy_image(filename="test_image.png"):
	"""
	如果图片文件不存在，则创建一个包含演示文本的PNG图片。
	"""
	if os.path.exists(filename):
		# print(f"'{filename}' already exists. Skipping creation.")
		return

	print(f"Creating dummy image: '{filename}'")
	img = Image.new('RGB', (500, 400), color='white')
	d = ImageDraw.Draw(img)
	try:
		font = ImageFont.truetype("arial.ttf", 40)
	except IOError:
		font = ImageFont.load_default()

	# 裁剪框内的文本现在使用您指定的字符
	d.text((100, 120), "Value: -1.23E+5", fill='black', font=font)
	d.text((100, 180), "Unit: 4.56 KT", fill='black', font=font)

	# 这是演示图片中绘制的红框坐标，我将用这个作为有效的裁剪坐标
	d.rectangle([98, 108, 371, 273], outline='red', width=2)
	img.save(filename)


# --- 主函数 (tesserocr 版本) ---
def main():
	image_path = "test_image.png"
	output_txt_path = "tesserocr_optimized_output.txt"

	# 1. 确保演示图片存在
	create_dummy_image(image_path)

	# 2. 定义裁剪坐标
	# 注意：我修改了坐标以匹配 create_dummy_image 中实际绘制的红框
	# 原始脚本中的 (166, 1545, 316, 1576) 对于这个 500x400 的演示图片是无效的
	crop_box = (98, 108, 371, 273)

	# --- 优化点 1: 定义字符白名单 ---
	char_whitelist = "0123456789.,+-EKTValue:Unit "  # 增加了Value/Unit/冒号/空格，以便识别完整

	# 模式设置 PSM.SINGLE_BLOCK (6) SINGLE_LINE (7)
	psm_mode = PSM.SINGLE_LINE

	print(f"--- Tesserocr Demo ---")
	print(f"Using Config: PSM={psm_mode}")
	print(f"Using Whitelist: '{char_whitelist}'")

	try:
		# 3. 使用 Pillow 打开图片
		img = Image.open(image_path)

		# 4. 裁剪图片
		cropped_img = img.crop(crop_box)

		# (可选) 图像预处理：转换为灰度图
		cropped_img = cropped_img.convert('L')
		# (可选) 保存裁剪后的图片以便检查
		# cropped_img.save("tesserocr_cropped_debug.png")

		# 5. 调用 tesserocr API
		# 这是关键：我们初始化 API 一次
		# 使用 'with' 语句可以确保资源被正确释放
		# oem=OEM.LSTM_ONLY (3) 是现代引擎，通常是默认值
		with PyTessBaseAPI(lang='eng', psm=psm_mode, oem=OEM.DEFAULT) as api:

			# 设置白名单变量
			api.SetVariable("tessedit_char_whitelist", char_whitelist)

			# 计时开始（在 API 初始化之后，在识别之前）
			start_time = time.perf_counter()

			# 将 PIL 图像设置到 API 实例中
			api.SetImage(cropped_img)

			# 获取识别结果
			text = api.GetUTF8Text()

			# 计时结束
			end_time = time.perf_counter()
		# tesserocr 的速度会快非常多，开销主要在 SetImage 和 GetUTF8Text
		# 而不是进程创建

		# 6. 将识别的文本写入 .txt 文件
		with open(output_txt_path, 'w', encoding='utf-8') as f:
			f.write(text)

		print(f"Successfully processed '{image_path}'.")
		print(f"OCR operation took: {end_time - start_time:.4f} seconds.")
		print(f"Extracted text:\n---\n{text.strip()}\n---")  # 使用 .strip() 清理空白
		print(f"Output saved to '{output_txt_path}'.")

	except ImportError:
		print("Tesserocr Error: 'tesserocr' library not found.")
		print("Please install it via: pip install tesserocr")
	except RuntimeError as e:
		print(f"Tesserocr Runtime Error: {e}")
		print("This often means tesserocr cannot find the 'tessdata' folder.")
		print("Ensure Tesseract is installed correctly and the TESSDATA_PREFIX environment variable is set.")
	except Exception as e:
		print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
	main()
from PIL import Image, ImageDraw, ImageFont
import os
import time
# 导入 tesserocr 模块
from tesserocr import PyTessBaseAPI, PSM, OEM


# --- 辅助函数：创建一个用于演示的PNG图片 ---
# (与之前版本相同)
def create_dummy_image(filename="test_image.png"):
	"""
	如果图片文件不存在，则创建一个包含演示文本的PNG图片。
	"""
	if os.path.exists(filename):
		return

	print(f"Creating dummy image: '{filename}'")
	img = Image.new('RGB', (500, 400), color='white')
	d = ImageDraw.Draw(img)
	try:
		font = ImageFont.truetype("arial.ttf", 40)
	except IOError:
		font = ImageFont.load_default()

	d.text((100, 120), "Value: -1.23E+5", fill='black', font=font)
	d.text((100, 180), "Unit: 4.56 KT", fill='black', font=font)
	d.rectangle([98, 108, 371, 273], outline='red', width=2)
	img.save(filename)


# --- 主函数 (tesserocr 版本) ---
def main():
	image_path = "test_image.png"
	output_txt_path = "tesserocr_optimized_output.txt"

	# --- 关键修正：指定 Tesseract 安装路径 ---
	# tesserocr 需要指向 tessdata 文件夹的 *父目录*
	# 根据你之前的 pytesseract 脚本，我们假设路径如下：
	tesseract_path = r'C:\Program Files\Tesseract-OCR'
	# 如果你的 tessdata 文件夹在别处 (例如 C:\tess\tessdata)，
	# 那么这里应该设置为 tesseract_path = r'C:\tess'

	# 1. 确保演示图片存在
	create_dummy_image(image_path)

	# 2. 定义裁剪坐标
	# crop_box = (98, 108, 371, 273) #下面那个是真实截图指定的坐标，但超过了dummy_image的尺寸范围
	crop_box = (166, 1545, 316, 1576)

	# --- 优化点 1: 定义字符白名单 ---
	char_whitelist = "0123456789.,+-EKTValue:Unit "

	# --- 优化点 2: 设置页面分割模式 (PSM) ---
	# .SINGLE_BLOCK是psm 6, SINGLE_LINE是psm 7
	psm_mode = PSM.SINGLE_LINE

	print(f"--- Tesserocr Demo ---")
	print(f"Attempting to use Tesseract path: {tesseract_path}")
	print(f"Using Config: PSM={psm_mode}")
	print(f"Using Whitelist: '{char_whitelist}'")

	try:
		# 3. 使用 Pillow 打开图片
		img = Image.open(image_path)

		# 4. 裁剪图片
		cropped_img = img.crop(crop_box)
		cropped_img = cropped_img.convert('L')
		# cropped_img.save("tesserocr_cropped_debug.png")

		# 5. 调用 tesserocr API
		# 这是关键：我们初始化 API 一次，并传入 path 参数
		with PyTessBaseAPI(path=tesseract_path, lang='eng', psm=psm_mode, oem=OEM.DEFAULT) as api:

			# 设置白名单变量
			api.SetVariable("tessedit_char_whitelist", char_whitelist)

			# 计时开始
			start_time = time.perf_counter()

			# 将 PIL 图像设置到 API 实例中
			api.SetImage(cropped_img)

			# 获取识别结果
			text = api.GetUTF8Text()

			# 计时结束
			end_time = time.perf_counter()

		# 6. 将识别的文本写入 .txt 文件
		with open(output_txt_path, 'w', encoding='utf-8') as f:
			f.write(text)

		print(f"Successfully processed '{image_path}'.")
		print(f"OCR operation took: {end_time - start_time:.4f} seconds.")
		print(f"Extracted text:\n---\n{text.strip()}\n---")
		print(f"Output saved to '{output_txt_path}'.")

	except RuntimeError as e:
		print(f"Tesserocr Runtime Error: {e}")
		print("--- DEBUGGING HELP ---")
		print(f"The path '{tesseract_path}' was provided to tesserocr.")
		print(f"Please VERIFY that this directory contains a subdirectory named 'tessdata'.")
		print(f"e.g., '{tesseract_path}\\tessdata\\eng.traineddata' should exist.")
		print("If not, please update the 'tesseract_path' variable in the script.")
		raise
	except Exception as e:
		print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
	main()
from PIL import Image, ImageDraw, ImageFont
import os
import time
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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

	d.rectangle([98, 108, 371, 273], outline='red', width=2)
	img.save(filename)


# --- 主函数 ---
def main():
	image_path = "test_image.png"
	output_txt_path = "output/pytesseract_optimized_output.txt"

	# 1. 确保演示图片存在
	# 我们更新一下演示图片，使其包含科学计数法
	create_dummy_image(image_path)

	# 2. 定义裁剪坐标
	crop_box = (166, 1545, 316, 1576)

	# --- 优化点 1: 定义字符白名单 ---
	# 根据您的描述：[0~9, ., ,, +, -, E, K, T, <space>]
	# 注意：Tesseract 配置字符串中不要有逗号
	char_whitelist = "0123456789.,+-EKT"

	# --- 优化点 2: 设置页面分割模式 (PSM) ---
	# 假设裁剪的区域是几行文字（但不是完整的段落）。
	# --psm 6: 假设是一个统一的文本块。
	# --psm 7: 假设是一行文本 (如果只有一行，这个会非常快)。
	# 根据您的确认，我们使用 psm 7
	psm_mode = 7

	# 将配置组合成一个字符串
	tesseract_config = f"--psm {psm_mode} -c tessedit_char_whitelist={char_whitelist}"
	# 旧引擎，可以试试，对于屏幕截图这种标准字体可能更快
	# tesseract_config = f"--oem 0 --psm {psm_mode} -c tessedit_char_whitelist={char_whitelist}"

	print(f"--- Optimized Pillow Demo ---")
	print(f"Using Config: {tesseract_config}")

	try:
		# 3. 使用 Pillow 打开图片
		img = Image.open(image_path)

		# 4. 裁剪图片
		cropped_img = img.crop(crop_box)

		# (可选) 图像预处理：转换为灰度图可以提高稳定性
		cropped_img = cropped_img.convert('L')

		# (可选) 保存裁剪后的图片以便检查
		# cropped_img.save("pillow_optimized_cropped_debug.png")

		# 5. 调用 pytesseract 并传入优化配置
		start_time = time.perf_counter()
		text = pytesseract.image_to_string(cropped_img, lang='eng', config=tesseract_config)
		end_time = time.perf_counter()
		# 默认配置下，进行一次匹配（单行真空度）消耗的时间大约为0.15秒，可能大多数时间都花在了创建进程或者说读硬盘上，这不好。

		# 6. 将识别的文本写入 .txt 文件
		with open(output_txt_path, 'w', encoding='utf-8') as f:
			f.write(text)

		print(f"Successfully processed '{image_path}'.")
		print(f"OCR operation took: {end_time - start_time:.4f} seconds.")
		print(f"Extracted text:\n---\n{text}\n---")
		print(f"Output saved to '{output_txt_path}'.")

	except pytesseract.TesseractNotFoundError:
		print("Tesseract Error: The Tesseract executable was not found.")
	except Exception as e:
		print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
	main()


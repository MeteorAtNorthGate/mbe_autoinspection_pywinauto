import time

from pywinauto.application import Application
from pywinauto.findwindows import ElementNotFoundError

from tools import block_input,run_as_admin

app = Application(backend="win32").start("notepad.exe")
dlg = app.top_window()
dlg.wait('ready', timeout=10)

@block_input
def perform_safe_typing(window, text_to_type):
    """一个安全的打字操作，执行时会阻止用户干扰。"""
    print(f"  [函数内部] 正在输入: '{text_to_type}'")
    window.Edit.type_keys(text_to_type, with_spaces=True)
    time.sleep(2)
    print("  [函数内部] 输入完成。")

@block_input
def simulate_error_operation(window):
    """一个会故意出错的操作，用来演示 finally 的效果。"""
    print("  [函数内部] 尝试操作一个不存在的控件...")
    # 这行代码会因为找不到控件而抛出 ElementNotFoundError 异常
    window.child_window(title="一个不存在的按钮").click()
    print("  [函数内部] 这行代码永远不会被执行。")


# --- 3. 主执行逻辑 ---

if __name__ == "__main__":
    run_as_admin()
    print("程序开始，请准备。在输入锁定期间，你的鼠标键盘将无效。\n")
    time.sleep(2)

    # 调用第一个被装饰的函数，它会成功执行
    perform_safe_typing(dlg, "这是第一个安全的自动化操作。")

    print("\n等待3秒，准备执行下一个会出错的操作...\n")
    time.sleep(3)

    # 调用第二个被装饰的函数，它会中途失败
    try:
        simulate_error_operation(dlg)
    except ElementNotFoundError as e:
        print(f"\n捕获到预期中的错误: {e.__class__.__name__}")
        print("注意：即使函数出错了，装饰器的 finally 块也已执行，并解锁了输入。\n")

    # 验证输入是否真的已解锁
    print("测试完成。请检查你的鼠标键盘是否已恢复正常。")
    dlg.close()


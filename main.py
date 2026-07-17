# -*- coding: utf-8 -*-
"""Stealth Note v2.9.7 - 入口"""

import sys
import os

# 确保项目根目录在 sys.path 中
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from app import StealthNoteApp


def _show_debug_bg(app):
    """v2.9.7.6 调试模式：在全屏最底层生成黑白黄三色底色控件，便于截图识别效果。

    v2.9.7.6 修复：原实现创建独立 Tk() 实例与 app 的 Tk() 冲突，
    且 app.run() 的 mainloop 不会处理 debug_root 的事件。
    改为在 app 创建后，以 app.root 的 Toplevel 形式创建底色窗口，
    通过 lower() 置于最底层，确保事件循环统一。

    用法：python main.py --debug-bg
    正式打包时不带此参数，不影响正常运行。
    """
    import tkinter as tk
    root = tk.Toplevel(app.root)
    root.overrideredirect(True)
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{sw}x{sh}+0+0")
    # 三色竖条：黑、白、黄
    third = sw // 3
    tk.Frame(root, bg="#000000").place(x=0, y=0, width=third, height=sh)
    tk.Frame(root, bg="#FFFFFF").place(x=third, y=0, width=third, height=sh)
    tk.Frame(root, bg="#FFFF00").place(x=third * 2, y=0, width=sw - third * 2, height=sh)
    root.attributes("-topmost", False)
    root.attributes("-alpha", 1.0)
    root.lower()  # 置于最底层
    return root


def main():
    debug_bg = "--debug-bg" in sys.argv
    app = StealthNoteApp()
    debug_root = None
    if debug_bg:
        debug_root = _show_debug_bg(app)
    app.run()
    if debug_root:
        debug_root.destroy()


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""Stealth Note - 常量定义模块"""

import os
import sys
import ctypes
from ctypes import wintypes

APP_NAME = "Stealth Note"
VERSION = "v2.9.3"
AUTHOR = "Magicxh & TRAE"
CONTACT_EMAIL = "17296509@qq.com"

# Windows API 常量
GWL_EXSTYLE = -20
GWL_WNDPROC = -4
WS_EX_LAYERED = 0x80000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
LWA_ALPHA = 0x00000002
LWA_COLORKEY = 0x00000001

WM_ACTIVATE = 0x0006
WA_ACTIVE = 1
WA_CLICKACTIVE = 2
WM_SHOWWINDOW = 0x0018
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE = 0xF020
SC_RESTORE = 0xF120
SC_CLOSE = 0xF060
SW_SHOW = 5
SW_RESTORE = 9
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CONTROL = 0x11

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

# Windows API DLL
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

SetWindowLongPtrW = user32.SetWindowLongPtrW if hasattr(user32, 'SetWindowLongPtrW') else user32.SetWindowLongW
SetWindowLongPtrW.restype = ctypes.c_longlong
SetWindowLongPtrW.argtypes = [ctypes.c_longlong, ctypes.c_int, ctypes.c_longlong]

CallWindowProcW = user32.CallWindowProcW
CallWindowProcW.restype = ctypes.c_longlong
CallWindowProcW.argtypes = [ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong]

# 窗口过程回调类型
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint,
    ctypes.c_longlong, ctypes.c_longlong
)

# 易读模式色键（近黑色 #010101，避免紫红毛边）
COLORKEY = "#010101"
COLORKEY_INT = 0x00010101  # BGR格式

# 主窗口根背景色
ROOT_BG = "#000000"

# 深色/浅色模式预设配色
THEME_PALETTES = {
    "dark": {
        "bg_color": "#000000",
        "text_color": "#FFFFFF",
        "corner_color": "#FFFFFF",
        "read_bg_color": "#222222",
        "panel_bg_color": "#2c2c2c",
    },
    "light": {
        "bg_color": "#FFFFFF",
        "text_color": "#000000",
        "corner_color": "#000000",
        "read_bg_color": "#DDDDDD",
        "panel_bg_color": "#E8E8E8",
    },
}

# === 保护值与最小尺寸 ===
MIN_WINDOW_OPACITY = 0.25
MIN_PANEL_OPACITY = 0.35
MIN_TEXT_OPACITY = 0.10
MIN_READ_BG_OPACITY = 0.05
MIN_CORNER_OPACITY = 0.10
MIN_CORNER_LINE = 1
MIN_CORNER_LEN = 10
MAX_CORNER_LEN = 80
MAX_CORNER_LINE = 8
MIN_HANDLE_SIZE = 8
MAX_HANDLE_SIZE = 64
MIN_WINDOW_W = 300
MIN_WINDOW_H = 200
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 48

# === UI 尺寸常量 ===
TEXT_PAD_X = 24
TEXT_PAD_Y = 20
STEALTH_PAD_Y = 4
SCROLLBAR_WIDTH = 3
SCROLLBAR_PAD_RIGHT = 4
CORNER_MARGIN = 4
CORNER_HOT_SIZE = 14
HANDLE_WIN_PADDING = 12
HANDLE_REF_R = 9
PANEL_BTN_SIZE = 36
PANEL_PADDING = 4
PANEL_BTN_GAP = 2
PANEL_WIDTH = PANEL_PADDING * 2 + PANEL_BTN_SIZE * 11 + PANEL_BTN_GAP * 10
PANEL_HEIGHT = PANEL_PADDING * 2 + PANEL_BTN_SIZE

# === 配置防抖 ===
CONFIG_SAVE_DEBOUNCE_MS = 500

# === 路径计算 ===
if getattr(sys, 'frozen', False):
    _CONFIG_DIR = os.path.dirname(sys.executable)
else:
    _CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_CONFIG_DIR, "stealth_note_config.json")
ICON_FILE = os.path.join(_CONFIG_DIR, "stealth_note.ico")
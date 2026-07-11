# -*- coding: utf-8 -*-
# =============================================================================
# Stealth Note v2.0.0
# 隐秘笔记 - 完全透明的记事本
# 作者：Magicxh & TRAE
# =============================================================================

import os
import sys
import json
import copy
import shutil
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, font as tkfont
import ctypes
from ctypes import wintypes
import threading

# =============================================================================
# 常量定义
# =============================================================================

APP_NAME = "Stealth Note"
VERSION = "v2.7.3"
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

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

SetWindowLongPtrW = user32.SetWindowLongPtrW if hasattr(user32, 'SetWindowLongPtrW') else user32.SetWindowLongW
SetWindowLongPtrW.restype = ctypes.c_longlong
SetWindowLongPtrW.argtypes = [ctypes.c_longlong, ctypes.c_int, ctypes.c_longlong]

CallWindowProcW = user32.CallWindowProcW
CallWindowProcW.restype = ctypes.c_longlong
CallWindowProcW.argtypes = [ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong]

# 易读模式色键（近黑色 #010101，避免紫红毛边）
COLORKEY = "#010101"
COLORKEY_INT = 0x00010101  # BGR格式

# 主窗口根背景色（纯黑，配合LWA_ALPHA使用，无色键）
ROOT_BG = "#000000"

# 深色/浅色模式预设配色：控件颜色与背景匹配，减少文字抗锯齿毛边
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
STEALTH_PAD_Y = 4  # 隐写模式上下边距 = TEXT_PAD_Y 的 20%
SCROLLBAR_WIDTH = 3
SCROLLBAR_PAD_RIGHT = 4
CORNER_MARGIN = 4
CORNER_HOT_SIZE = 14
HANDLE_WIN_PADDING = 12
HANDLE_REF_R = 9  # 手柄圆心固定参考半径，不随 handle_size 变化，保证缩放时圆心不变
PANEL_BTN_SIZE = 36
PANEL_PADDING = 4
PANEL_BTN_GAP = 2
PANEL_WIDTH = PANEL_PADDING * 2 + PANEL_BTN_SIZE * 11 + PANEL_BTN_GAP * 10
PANEL_HEIGHT = PANEL_PADDING * 2 + PANEL_BTN_SIZE

# === 配置防抖 ===
CONFIG_SAVE_DEBOUNCE_MS = 500

if getattr(sys, 'frozen', False):
    _CONFIG_DIR = os.path.dirname(sys.executable)
else:
    _CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_CONFIG_DIR, "stealth_note_config.json")
ICON_FILE = os.path.join(_CONFIG_DIR, "stealth_note.ico")

# =============================================================================
# 默认配置
# =============================================================================

DEFAULT_CONFIG = {
    "window_width": 600,
    "window_height": 400,
    "window_x": None,
    "window_y": None,
    "topmost": False,
    "show_taskbar": True,
    "show_titlebar": False,
    "show_statusbar": False,
    "bg_color": "#000000",
    "bg_opacity": 0.50,
    "text_color": "#FFFFFF",
    "text_opacity": 0.80,
    "text_size": 12,
    "text_font": "Microsoft YaHei UI",
    "encoding": "auto",
    "read_mode": False,
    "read_bg_color": "#000000",
    "read_bg_opacity": 0.30,
    "invert_mode": False,
    "theme_mode": "dark",  # dark / light，用于匹配控件色彩以减少毛边
    "corner_size": 40,
    "corner_line_width": 2,
    "corner_color": "#FFFFFF",
    "corner_opacity": 0.80,
    "handle_size": 18,
    "handle_opacity": 0.80,
    "handle_color": "#FFFFFF",
    "show_scrollbar": True,
    "show_panel": True,
    "panel_opacity": 0.85,
    "panel_bg_color": "#2c2c2c",
    "panel_x": None,
    "panel_y": None,
    "stealth_mode": False,
    "stealth_lines": 3,
    "recent_files": [],
}

# =============================================================================
# 工具函数
# =============================================================================

def invert_color(hex_color):
    try:
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return f"#{255 - r:02x}{255 - g:02x}{255 - b:02x}"
    except Exception:
        return "#000000" if hex_color.lower() == "#ffffff" else "#FFFFFF"


def mix_color(fg_hex, opacity, bg_hex="#000000"):
    try:
        fc = fg_hex.lstrip('#')
        fr, fg_i, fb = int(fc[0:2], 16), int(fc[2:4], 16), int(fc[4:6], 16)
        bc = bg_hex.lstrip('#')
        br, bg_i2, bb = int(bc[0:2], 16), int(bc[2:4], 16), int(bc[4:6], 16)
        r = int(fr * opacity + br * (1 - opacity))
        g = int(fg_i * opacity + bg_i2 * (1 - opacity))
        b = int(fb * opacity + bb * (1 - opacity))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return fg_hex


def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


def detect_encoding(file_path):
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(8192)
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            return 'utf-16'
        try:
            raw.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass
        try:
            raw.decode('gbk')
            return 'gbk'
        except UnicodeDecodeError:
            pass
        try:
            raw.decode('gb2312')
            return 'gb2312'
        except UnicodeDecodeError:
            pass
        return 'latin-1'
    except Exception:
        return 'utf-8'


def read_text_file(file_path, encoding='auto'):
    enc = encoding if encoding != 'auto' else detect_encoding(file_path)
    try:
        with open(file_path, 'r', encoding=enc) as f:
            return f.read(), enc
    except (UnicodeDecodeError, LookupError):
        for e in ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=e) as f:
                    return f.read(), e
            except Exception:
                continue
        raise RuntimeError("无法识别文件编码")


def write_text_file(file_path, content, encoding='utf-8'):
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


def validate_config(cfg):
    result = dict(cfg)

    def _clamp(key, min_v, max_v):
        if key in result and result[key] is not None:
            try:
                result[key] = clamp(result[key], min_v, max_v)
            except (TypeError, ValueError):
                result[key] = DEFAULT_CONFIG[key]

    _clamp("window_width", MIN_WINDOW_W, 10000)
    _clamp("window_height", MIN_WINDOW_H, 10000)
    _clamp("bg_opacity", 0.0, 1.0)
    _clamp("text_opacity", MIN_TEXT_OPACITY, 1.0)
    _clamp("text_size", MIN_FONT_SIZE, MAX_FONT_SIZE)
    _clamp("read_bg_opacity", MIN_READ_BG_OPACITY, 1.0)
    _clamp("corner_size", MIN_CORNER_LEN, MAX_CORNER_LEN)
    _clamp("corner_line_width", MIN_CORNER_LINE, MAX_CORNER_LINE)
    _clamp("corner_opacity", MIN_CORNER_OPACITY, 1.0)
    _clamp("handle_size", MIN_HANDLE_SIZE, MAX_HANDLE_SIZE)
    _clamp("handle_opacity", MIN_CORNER_OPACITY, 1.0)
    _clamp("panel_opacity", MIN_PANEL_OPACITY, 1.0)
    _clamp("stealth_lines", 1, 3)

    for k in ["topmost", "show_taskbar", "show_titlebar", "show_statusbar",
              "read_mode", "invert_mode", "show_scrollbar", "show_panel",
              "stealth_mode"]:
        if k in result and not isinstance(result[k], bool):
            result[k] = DEFAULT_CONFIG[k]

    for k in ["bg_color", "text_color", "read_bg_color", "corner_color", "handle_color", "panel_bg_color"]:
        if k in result:
            v = result[k]
            if not isinstance(v, str) or not v.startswith('#') or len(v) != 7:
                result[k] = DEFAULT_CONFIG[k]

    if "text_font" not in result or not isinstance(result["text_font"], str):
        result["text_font"] = DEFAULT_CONFIG["text_font"]

    valid_themes = ["dark", "light"]
    if "theme_mode" not in result or result["theme_mode"] not in valid_themes:
        result["theme_mode"] = DEFAULT_CONFIG["theme_mode"]

    valid_enc = ["auto", "utf-8", "gbk", "gb2312", "latin-1", "utf-16", "utf-8-sig"]
    if "encoding" not in result or result["encoding"] not in valid_enc:
        result["encoding"] = DEFAULT_CONFIG["encoding"]

    if "recent_files" not in result or not isinstance(result["recent_files"], list):
        result["recent_files"] = []

    return result


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = copy.deepcopy(v)
            cfg = validate_config(cfg)
            return cfg
    except Exception as e:
        print(f"[配置] 加载失败: {e}")
        try:
            if os.path.exists(CONFIG_FILE):
                shutil.copy2(CONFIG_FILE, CONFIG_FILE + '.corrupt')
                print(f"[配置] 损坏文件已备份")
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_CONFIG)


def set_layered_transparent(hwnd, alpha=255, use_colorkey=False, show_taskbar=True):
    """设置窗口分层透明属性"""
    try:
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_LAYERED
        if show_taskbar:
            ex_style |= WS_EX_APPWINDOW
            ex_style &= ~WS_EX_TOOLWINDOW
        else:
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

        flags = LWA_ALPHA
        if use_colorkey:
            flags |= LWA_COLORKEY
        colorkey = COLORKEY_INT if use_colorkey else 0
        user32.SetLayeredWindowAttributes(hwnd, colorkey, int(alpha), flags)

        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
        return True
    except Exception as e:
        print(f"[透明] 设置失败: {e}")
        return False


def create_app_icon():
    if os.path.exists(ICON_FILE):
        return ICON_FILE
    try:
        from PIL import Image, ImageDraw, ImageFont
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size // 2, size // 2
        r = size // 2 - 16
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=(45, 45, 45, 245),
                     outline=(255, 255, 255, 255), width=4)
        try:
            font = ImageFont.truetype("arial.ttf", 140)
        except Exception:
            font = ImageFont.load_default()
        draw.text((cx, cy), "S", fill=(255, 255, 255, 255), font=font, anchor="mm")
        img.save(ICON_FILE, format='ICO',
                 sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return ICON_FILE
    except Exception as e:
        print(f"[图标] 生成失败: {e}")
        return None


def check_single_instance():
    mutex_name = "StealthNote_SingleInstance_Mutex_v271"
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(mutex)
        return None
    return mutex


# 窗口过程回调类型
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint,
    ctypes.c_longlong, ctypes.c_longlong
)

# =============================================================================
# 主应用类
# =============================================================================

class StealthNoteApp:
    def __init__(self):
        self._mutex = check_single_instance()
        if not self._mutex:
            self._show_single_instance_msg()
            sys.exit(0)

        self.cfg = load_config()
        self.current_file = None
        self.current_encoding = 'utf-8'
        self._modified = False

        self._drag_active = False
        self._drag_dx = 0
        self._drag_dy = 0
        self._resize_edge = None
        self._resize_start = (0, 0, 0, 0)
        self._panel_drag_active = False
        self._panel_drag_dx = 0
        self._panel_drag_dy = 0
        self._window_visible = True
        self._corner_dirty = True
        self._save_after_id = None
        self._resize_after_id = None
        self._syncing_text = False

        # 隐写模式滚轮事件累积器：避免触控板微滚动导致光标跳动
        self._stealth_wheel_acc = 0

        self._root_hwnd = None
        self._handle_hwnd = None
        self._panel_hwnd = None

        self.icon_path = create_app_icon()

        # 1. 创建主窗口（无边框）
        self._create_root()
        # 2. 创建隐藏窗口作为任务栏钩子
        self._create_taskbar_host()
        # 3. 初始化所有UI组件
        self._init_content()
        self._init_corners()
        self._init_handle()
        self._init_panel()
        self._init_shortcuts()

        # 应用初始样式
        self._apply_window_style()
        self._apply_text_appearance()
        self.root.after(100, self._layout_all)

        self.root.deiconify()
        self.root.lift()
        self._window_visible = True

        if not os.path.exists(CONFIG_FILE):
            self._save_config_debounced()

        # 延迟初始化托盘（在主线程的after中调度）
        self.root.after(300, self._init_tray)
        self.root.after(200, self._focus_text)
        if self.cfg.get('stealth_mode'):
            self.root.after(250, self._apply_stealth_state)

    def _show_single_instance_msg(self):
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(APP_NAME, f"{APP_NAME} 已经在运行中。\n\n请查看系统托盘或任务栏。")
            root.destroy()
        except Exception:
            pass

    def _save_config_debounced(self):
        if self._save_after_id:
            try:
                self.root.after_cancel(self._save_after_id)
            except Exception:
                pass
        self._save_after_id = self.root.after(CONFIG_SAVE_DEBOUNCE_MS, self._do_save_config)

    def _do_save_config(self):
        self._save_after_id = None
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[配置] 保存失败: {e}")

    def _force_foreground(self):
        """强制将所有窗口带到最前台（使用Windows API）"""
        try:
            user32.SetForegroundWindow(self._root_hwnd)
            user32.BringWindowToTop(self._root_hwnd)
        except Exception:
            pass
        self.root.attributes("-topmost", True)
        self.content_win.attributes("-topmost", True)
        self.root.lift()
        self.content_win.lift()
        self.root.after(80, lambda: (
            self.root.attributes("-topmost", self.cfg['topmost']),
            self.content_win.attributes("-topmost", self.cfg['topmost'])
        ))
        self.handle_win.lift()
        if self.cfg['show_panel']:
            self.panel.lift()

    # -------------------------------------------------------------------------
    # 主窗口
    # -------------------------------------------------------------------------

    def _create_root(self):
        """创建根窗口（完全透明，仅作容器，content_win 负责实际显示）"""
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception:
                pass

        self.root.overrideredirect(True)

        w = max(MIN_WINDOW_W, int(self.cfg['window_width']))
        h = max(MIN_WINDOW_H, int(self.cfg['window_height']))

        if self.cfg['window_x'] is None or self.cfg['window_y'] is None:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
        else:
            x = int(self.cfg['window_x'])
            y = int(self.cfg['window_y'])

        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # root 完全透明（COLORKEY），content_win 负责实际显示
        self.root.configure(bg=COLORKEY, bd=0, highlightthickness=0)
        self.bg_frame = tk.Frame(self.root, bg=COLORKEY, bd=0, highlightthickness=0)
        self.bg_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.root.update_idletasks()
        self._root_hwnd = self.root.winfo_id()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 绑定窗口事件（根窗口 + 内容窗口双保险，确保四角缩放可命中）
        self.root.bind("<ButtonPress-1>", self._on_root_button_press)
        self.root.bind("<B1-Motion>", self._on_root_resize)
        self.root.bind("<ButtonRelease-1>", self._on_root_resize_end)
        self.root.bind("<Motion>", self._on_root_motion)
        self.root.bind("<MouseWheel>", self._on_root_wheel)
        self.root.bind("<Configure>", self._on_window_configure)

    def _create_taskbar_host(self):
        """创建任务栏代理窗口（透明正常窗口，确保任务栏图标显示且点击有效）"""
        self.host = tk.Toplevel(self.root)
        self.host.title(APP_NAME)
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.host.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"[任务栏] 设置图标失败: {e}")

        self.host.geometry("1x1+-10000+-10000")
        self.host.update_idletasks()
        self._host_hwnd = self.host.winfo_id()

        ex_style = user32.GetWindowLongW(self._host_hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_LAYERED
        user32.SetWindowLongW(self._host_hwnd, GWL_EXSTYLE, ex_style)
        user32.SetLayeredWindowAttributes(self._host_hwnd, 0, 0, LWA_ALPHA)

        self.host.protocol("WM_DELETE_WINDOW", self._on_host_close)
        self.host.bind("<Unmap>", self._on_host_unmap)
        self.host.bind("<Map>", self._on_host_map)
        self.host.bind("<FocusIn>", self._on_host_focus)

        self._host_minimizing = False
        self._host_restoring = False

    def _on_host_close(self):
        """任务栏窗口关闭：退出程序"""
        self.exit_app()

    def _on_host_unmap(self, event=None):
        """任务栏窗口被最小化：同步隐藏主窗口"""
        if self._host_restoring:
            return
        self._host_minimizing = True
        if self._window_visible:
            self._hide_window()
        self.host.after(50, lambda: setattr(self, '_host_minimizing', False))

    def _on_host_map(self, event=None):
        """任务栏窗口被恢复：同步显示主窗口"""
        if self._host_minimizing:
            return
        self._host_restoring = True
        if not self._window_visible:
            self._show_window()
        self.host.after(50, lambda: setattr(self, '_host_restoring', False))

    def _on_host_focus(self, event=None):
        """任务栏窗口获得焦点：将主窗口带到前台"""
        if self._window_visible:
            self._force_foreground()

    def _sync_taskbar_host(self):
        """同步任务栏代理窗口与主窗口的显示状态"""
        if not hasattr(self, 'host') or not self.host.winfo_exists():
            return
        if not self.cfg['show_taskbar']:
            self.host.withdraw()
            return

        if self._window_visible:
            self.host.deiconify()
            self.host.lower()
        else:
            self.host.iconify()

    def _apply_window_style(self):
        try:
            bg_op = max(0.05, self.cfg['bg_opacity'])
            
            self.root.attributes("-transparentcolor", COLORKEY)
            ex_style = user32.GetWindowLongW(self._root_hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_LAYERED
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(self._root_hwnd, GWL_EXSTYLE, ex_style)
            user32.SetLayeredWindowAttributes(self._root_hwnd, COLORKEY_INT, 255, LWA_COLORKEY)
            user32.SetWindowPos(self._root_hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
            
            if not hasattr(self, '_content_hwnd'):
                self._content_hwnd = self.content_win.winfo_id()
            ex2 = user32.GetWindowLongW(self._content_hwnd, GWL_EXSTYLE)
            ex2 |= WS_EX_LAYERED
            ex2 |= WS_EX_TOOLWINDOW
            ex2 &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(self._content_hwnd, GWL_EXSTYLE, ex2)
            user32.SetLayeredWindowAttributes(self._content_hwnd, COLORKEY_INT, int(bg_op * 255), LWA_ALPHA | LWA_COLORKEY)
            user32.SetWindowPos(self._content_hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
            
            if self.cfg['topmost']:
                self.root.attributes("-topmost", True)
                self.content_win.attributes("-topmost", True)
                if hasattr(self, 'handle_win') and self.handle_win:
                    self.handle_win.attributes("-topmost", True)
                if hasattr(self, 'panel') and self.panel:
                    self.panel.attributes("-topmost", True)
            else:
                self.root.attributes("-topmost", False)
                self.content_win.attributes("-topmost", False)
                if hasattr(self, 'handle_win') and self.handle_win:
                    self.handle_win.attributes("-topmost", False)
                if hasattr(self, 'panel') and self.panel:
                    self.panel.attributes("-topmost", False)
            
            self._sync_taskbar_host()
        except Exception as e:
            print(f"[窗口样式] 设置失败: {e}")

    def _set_taskbar_visible(self, visible):
        """设置任务栏是否显示"""
        self.cfg['show_taskbar'] = visible
        self._apply_window_style()

    # -------------------------------------------------------------------------
    # 内容区（文本 + 滚动条）
    # -------------------------------------------------------------------------

    def _init_content(self):
        """初始化内容层窗口：content_win 使用 LWA_ALPHA 统一半透明，
        所有子元素 bg=raw_bg 实色，保证文本交互顺滑且无黑底色差。
        关键：四角画布/热区在文本容器之前创建，确保天然位于文本之下，不会遮挡文字。"""
        raw_bg = self.cfg['bg_color']
        self.content_win = tk.Toplevel(self.root)
        self.content_win.withdraw()
        self.content_win.overrideredirect(True)
        self.content_win.configure(bg=raw_bg, bd=0, highlightthickness=0)
        self.content_win.attributes("-topmost", True)

        self.content_frame = tk.Frame(self.content_win, bg=raw_bg, bd=0, highlightthickness=0)
        self.content_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # ===== 四角框线画布和热区 =====
        # 在文本容器之前创建，确保自然位于文本之下，彻底避免遮挡文字
        self._corner_frames = {}      # 14x14 缩放热区
        self._corner_canvases = {}    # 独立视觉画布，绘制单个角的框线
        self._corner_bg_canvas = None

        corners = [
            ("nw", "top_left_corner"),
            ("ne", "top_right_corner"),
            ("sw", "bottom_left_corner"),
            ("se", "bottom_right_corner"),
        ]

        for name, cursor in corners:
            # 热区：仅保留角落 14x14，用于触发缩放
            frame = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0)
            frame.bind("<ButtonPress-1>", lambda e, n=name: self._on_resize_start(e, n))
            frame.bind("<B1-Motion>", self._on_resize)
            frame.bind("<ButtonRelease-1>", self._on_resize_end)
            frame.bind("<Motion>", self._on_content_motion)

            # 视觉画布：独立绘制单个角的框线
            canvas = tk.Canvas(self.content_frame, bg=raw_bg, highlightthickness=0, bd=0, cursor=cursor)
            canvas.bind("<ButtonPress-1>", lambda e, n=name: self._on_resize_start(e, n))
            canvas.bind("<B1-Motion>", self._on_resize)
            canvas.bind("<ButtonRelease-1>", self._on_resize_end)
            canvas.bind("<Motion>", self._on_content_motion)

            self._corner_frames[name] = frame
            self._corner_canvases[name] = canvas

        self.text_container = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0)
        self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)

        self.text = tk.Text(
            self.text_container,
            bg=raw_bg,
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            selectbackground="#3399FF",
            selectforeground="#FFFFFF",
            font=("Microsoft YaHei UI", 12),
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=6,
            pady=6,
            undo=True,
            maxundo=100,
            exportselection=True,
        )
        self.text.pack(side="left", fill="both", expand=True)

        # ===== 隐写框集群 =====
        # 隐写容器：独立于文本框容器，切换模式时显示/隐藏
        self.stealth_container = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0)

        # 隐写文本框：无框，继承普通文本框样式，宽度填充，高度由行数决定
        # 垂直内边距设为 0，确保 winfo_reqheight / metrics 能精确对应行数
        self.stealth_text = tk.Text(
            self.stealth_container,
            bg=raw_bg,
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            selectbackground="#3399FF",
            selectforeground="#FFFFFF",
            font=("Microsoft YaHei UI", 12),
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=6,
            pady=0,
            undo=True,
            maxundo=100,
            height=3,
            exportselection=True,
        )
        # 顶部锚定，确保单行模式下文本位于容器顶端，横线可正确绘制在文字下方
        self.stealth_text.pack(side="left", fill="x", expand=False, anchor="n")
        # 隐写行分隔线（视觉提示：光标所在行下方）
        # 采用 1px 黑线 + 1px 白线上下叠合，总高度 2px
        # 放置在 content_frame 上，避免容器 padx 影响坐标计算
        self._stealth_line_container = tk.Frame(self.content_frame, bg="#000000", height=2, width=1)
        self._stealth_line_black = tk.Frame(self._stealth_line_container, bg="#000000", height=1)
        self._stealth_line_black.pack(side="top", fill="x", expand=False)
        self._stealth_line_white = tk.Frame(self._stealth_line_container, bg="#FFFFFF", height=1)
        self._stealth_line_white.pack(side="top", fill="x", expand=False)
        self._stealth_line_container.place_forget()
        self._stealth_line_visible = False

        # 保存切换前的窗口高度（用于从隐写模式返回时恢复）
        self._normal_window_height = None

        # 自定义滚动条
        self.sb_container = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0,
                                     width=SCROLLBAR_WIDTH + SCROLLBAR_PAD_RIGHT * 2)
        self.sb_container.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0, relheight=1.0)

        self._sb_canvas = tk.Canvas(self.sb_container, bg=raw_bg, highlightthickness=0, bd=0,
                                    width=SCROLLBAR_WIDTH)
        self._sb_canvas.pack(side="right", fill="y", padx=(0, SCROLLBAR_PAD_RIGHT))

        self._sb_visible = False

        self.text.configure(yscrollcommand=self._on_scroll)

        self._sb_canvas.bind("<ButtonPress-1>", self._on_sb_press)
        self._sb_canvas.bind("<B1-Motion>", self._on_sb_drag)
        self._sb_canvas.bind("<Enter>", lambda e: self._sb_hover(True))
        self._sb_canvas.bind("<Leave>", lambda e: self._sb_hover(False))

        self._set_scrollbar_visible(False)

        self.text.focus_set()
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.stealth_text.bind("<<Modified>>", self._on_stealth_text_modified)

        # 文本框背景已改为实色，恢复原生鼠标/键盘交互。
        # 仅保留隐写视图同步和滚轮增强，不再模拟点击/拖拽选区。
        for widget in (self.text, self.stealth_text):
            # 键盘输入/光标移动后同步隐写视图
            widget.bind("<KeyRelease>", self._on_text_cursor_moved)
            # 鼠标释放后刷新隐写视图（仅隐写模式生效）
            widget.bind("<ButtonRelease-1>", self._on_text_button_release)

        # 普通文本框：绑定滚轮滚动（Tkinter Text 在 Windows 上无原生滚轮支持）
        self.text.bind("<MouseWheel>", self._on_text_wheel_smooth)
        # 普通文本框容器空白区：转发滚轮给文本框
        self.text_container.bind("<MouseWheel>", lambda e: self._route_wheel_to_text(e, self.text))

        # 隐写文本框：滚轮用于移动光标/行
        self.stealth_text.bind("<MouseWheel>", self._on_stealth_wheel)
        self.stealth_container.bind("<MouseWheel>", lambda e: self._route_wheel_to_text(e, self.stealth_text))

        # 创建隐写行数 IntVar（供菜单 radiobutton 使用）
        self._stealth_lines_var = tk.IntVar(value=self.cfg.get('stealth_lines', 3))

        self._create_context_menu()

        self.content_win.update_idletasks()
        self.content_win.deiconify()

        # 内容窗口也需要响应四角缩放与滚轮（根窗口可能被内容窗口遮挡）
        self.content_win.bind("<ButtonPress-1>", self._on_content_button_press)
        self.content_win.bind("<B1-Motion>", self._on_content_resize)
        self.content_win.bind("<ButtonRelease-1>", self._on_content_resize_end)
        self.content_win.bind("<Motion>", self._on_content_motion)
        self.content_win.bind("<MouseWheel>", self._on_root_wheel)

    def _is_stealth_container_visible(self):
        """判断隐写框容器当前是否处于显示状态（从布局管理器派生，避免状态不一致）"""
        try:
            return self.stealth_container.winfo_manager() == "pack"
        except Exception:
            return False

    def _calc_bg_color(self):
        """计算当前应显示的背景色（考虑易读模式、反色模式和透明度）。

        根窗口使用 LWA_ALPHA 实现真实半透明，因此这里返回原始背景色（含反色），
        由 Windows 的 alpha 通道负责透明度混合。若再预乘一次透明度，会导致文本区
        域双重变暗、呈现不自然的黑色底色。
        """
        if self.cfg['read_mode']:
            return COLORKEY
        else:
            bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                bg = invert_color(bg)
            return bg

    def _apply_text_appearance(self):
        """应用文本外观设置（反色、易读模式与基础属性叠加，不修改模式开关）"""
        # 原始背景色（不含透明度预乘），content_win 的 LWA_ALPHA 负责实际半透明
        raw_bg = self.cfg['bg_color']
        if self.cfg['invert_mode']:
            raw_bg = invert_color(raw_bg)

        # 文字颜色：按原始背景色混合，LWA_ALPHA 统一控制最终透明度
        tc = self.cfg['text_color']
        if self.cfg['invert_mode']:
            tc = invert_color(tc)
        fg_op = self.cfg['text_opacity']
        fg_color = mix_color(tc, fg_op, raw_bg)

        # 更醒目的选区颜色
        sel_bg = mix_color("#3399FF", 0.85, raw_bg)
        sel_fg = "#FFFFFF"

        # 文本框背景：raw_bg 实色（content_win 使用 LWA_ALPHA 控制透明度）
        text_bg = raw_bg
        stealth_bg = raw_bg

        self.text.configure(
            bg=text_bg,
            fg=fg_color,
            insertbackground=fg_color,
            selectbackground=sel_bg,
            selectforeground=sel_fg,
            font=(self.cfg['text_font'], self.cfg['text_size'])
        )
        if hasattr(self, 'stealth_text') and self.stealth_text:
            self.stealth_text.configure(
                bg=stealth_bg,
                fg=fg_color,
                insertbackground=fg_color,
                selectbackground=sel_bg,
                selectforeground=sel_fg,
                font=(self.cfg['text_font'], self.cfg['text_size'])
            )

        # 容器背景：raw_bg 实色（content_win 使用 LWA_ALPHA 控制透明度）
        if hasattr(self, 'text_container') and self.text_container:
            self.text_container.configure(bg=raw_bg)
        if hasattr(self, 'stealth_container') and self.stealth_container:
            self.stealth_container.configure(bg=raw_bg)

        # 易读模式背景
        if self.cfg['read_mode']:
            self._apply_read_mode_bg()
        else:
            try:
                self.text.tag_remove("read_bg", "1.0", "end")
                if hasattr(self, 'stealth_text') and self.stealth_text:
                    self.stealth_text.tag_remove("read_bg", "1.0", "end")
            except Exception:
                pass

        # 隐写模式下字号变化时同步更新窗口高度
        if self.cfg.get('stealth_mode') and hasattr(self, 'stealth_container') and self._is_stealth_container_visible():
            ww = self.root.winfo_width()
            new_h = self._calc_stealth_window_height()
            if abs(new_h - self.root.winfo_height()) > 2:
                self.root.geometry(f"{ww}x{new_h}")
                self.content_win.geometry(f"{ww}x{new_h}")
                self._corner_dirty = True
                self._update_corners()
                self._layout_handle()

        if self._sb_visible:
            self._redraw_scrollbar()

    def _apply_read_mode_bg(self):
        """易读模式：仅在有文字的行显示背景色（反色优先叠加）"""
        try:
            row_bg = self.cfg['read_bg_color']
            if self.cfg['invert_mode']:
                row_bg = invert_color(row_bg)
            read_op = self.cfg['read_bg_opacity']
            # 按 raw_bg 混合，与 content_win 的 LWA_ALPHA 统一叠加
            raw_bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                raw_bg = invert_color(raw_bg)
            row_bg = mix_color(row_bg, read_op, raw_bg)

            for widget in [self.text, getattr(self, 'stealth_text', None)]:
                if not widget or not widget.winfo_exists():
                    continue
                widget.tag_remove("read_bg", "1.0", "end")
                widget.tag_configure("read_bg", background=row_bg)
                count = int(widget.index("end-1c").split(".")[0])
                for i in range(1, count + 1):
                    line_start = f"{i}.0"
                    line_end = f"{i}.end"
                    line_text = widget.get(line_start, line_end)
                    if line_text.strip():
                        widget.tag_add("read_bg", line_start, line_end)
        except Exception as e:
            print(f"[易读模式] 应用失败: {e}")

    # -------------------------------------------------------------------------
    # 滚动条
    # -------------------------------------------------------------------------

    def _sb_hover(self, entering):
        self._redraw_scrollbar(highlight=entering)

    def _on_scroll(self, *args):
        need_scroll = not (float(args[0]) <= 0.0 and float(args[1]) >= 1.0)
        if self.cfg['show_scrollbar'] and need_scroll:
            self._set_scrollbar_visible(True)
            self._update_scrollbar_thumb(float(args[0]), float(args[1]))
        else:
            self._set_scrollbar_visible(False)

    def _set_scrollbar_visible(self, visible):
        if visible == self._sb_visible:
            return
        self._sb_visible = visible
        if visible:
            self.sb_container.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0, relheight=1.0)
            self._redraw_scrollbar()
        else:
            self.sb_container.place_forget()

    def _update_scrollbar_thumb(self, first, last):
        self._sb_first = first
        self._sb_last = last
        self._redraw_scrollbar()

    def _redraw_scrollbar(self, highlight=False):
        canvas = self._sb_canvas
        canvas.delete("all")
        if not self._sb_visible:
            return

        w = SCROLLBAR_WIDTH
        h = canvas.winfo_height()
        if h < 10:
            return

        cs = max(MIN_CORNER_LEN, self.cfg['corner_size'])
        margin_top = cs + 4
        margin_bottom = cs + 4
        track_top = margin_top
        track_bottom = h - margin_bottom
        track_h = track_bottom - track_top

        if track_h < 20:
            return

        first = getattr(self, '_sb_first', 0.0)
        last = getattr(self, '_sb_last', 1.0)
        thumb_h = max(20, int(track_h * (last - first)))
        thumb_y = track_top + int(track_h * first)

        base_color = self.cfg['corner_color']
        if self.cfg['invert_mode']:
            base_color = invert_color(base_color)

        track_color = mix_color(base_color, 0.2, "#000000")
        thumb_color = mix_color(base_color, 0.6 if not highlight else 0.9, "#000000")

        canvas.create_rectangle(
            w // 2 - 1, track_top, w // 2 + 1, track_bottom,
            fill=track_color, outline="")

        canvas.create_rectangle(
            0, thumb_y, w, thumb_y + thumb_h,
            fill=thumb_color, outline="")

        self._sb_thumb_y = thumb_y
        self._sb_thumb_h = thumb_h
        self._sb_track_top = track_top
        self._sb_track_bottom = track_bottom

    def _on_sb_press(self, event):
        if not hasattr(self, '_sb_thumb_y'):
            return
        if self._sb_thumb_y <= event.y <= self._sb_thumb_y + self._sb_thumb_h:
            self._sb_drag_start_y = event.y
            self._sb_drag_start_first = getattr(self, '_sb_first', 0.0)
        else:
            delta = 1.0 if event.y > self._sb_thumb_y else -1.0
            self.text.yview_scroll(int(delta), "pages")

    def _on_sb_drag(self, event):
        if not hasattr(self, '_sb_drag_start_y'):
            return
        track_h = self._sb_track_bottom - self._sb_track_top
        if track_h <= 0:
            return
        dy = event.y - self._sb_drag_start_y
        ratio = dy / track_h
        new_first = clamp(self._sb_drag_start_first + ratio, 0.0, 1.0)
        self.text.yview_moveto(new_first)

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="撤销", command=lambda: self.text.event_generate("<<Undo>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="剪切", command=lambda: self.text.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="复制", command=lambda: self.text.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="粘贴", command=lambda: self.text.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="删除", command=lambda: self.text.delete("sel.first", "sel.last"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="全选", command=lambda: self.text.event_generate("<<SelectAll>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="隐写模式" if not self.cfg.get('stealth_mode') else "退出隐写模式",
            command=self.toggle_stealth)
        self.context_menu.add_separator()
        # 隐写行数选择：radiobutton 自带选中指示器，无需额外图标
        for lines, label in [(1, "一行模式"), (2, "两行模式"), (3, "三行模式")]:
            self.context_menu.add_radiobutton(
                label=label,
                value=lines,
                variable=self._stealth_lines_var,
                command=lambda n=lines: self._set_stealth_lines(n))
        self.text.bind("<Button-3>", self._show_context_menu)
        self.stealth_text.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        try:
            label = "退出隐写模式" if self.cfg.get('stealth_mode') else "隐写模式"
            try:
                self.context_menu.entryconfigure("隐写模式", label=label)
                self.context_menu.entryconfigure("退出隐写模式", label=label)
            except Exception:
                pass
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_text_modified(self, event):
        if self.text.edit_modified():
            self._modified = True
            self._update_title()
            self.text.edit_modified(False)
            if self.cfg['read_mode']:
                self.root.after(50, self._apply_read_mode_bg)
            if self.cfg.get('stealth_mode'):
                self.root.after(10, self._sync_to_stealth)

    def _on_stealth_text_modified(self, event):
        if self.stealth_text.edit_modified():
            self._modified = True
            self._update_title()
            self.stealth_text.edit_modified(False)
            self.root.after(10, self._sync_from_stealth)

    def _sync_to_stealth(self):
        """将普通文本框内容同步到隐写文本框"""
        if self._syncing_text or not self.cfg.get('stealth_mode'):
            return
        try:
            self._syncing_text = True
            src = self.text.get("1.0", "end-1c")
            dst = self.stealth_text.get("1.0", "end-1c")
            if src != dst:
                cur = self.text.index("insert")
                self.stealth_text.delete("1.0", "end")
                self.stealth_text.insert("1.0", src)
                self.stealth_text.mark_set("insert", cur)
                self._refresh_stealth_view()
        except Exception as e:
            print(f"[隐写同步] to stealth 失败: {e}")
        finally:
            self._syncing_text = False

    def _sync_from_stealth(self):
        """将隐写文本框内容同步回普通文本框"""
        if self._syncing_text:
            return
        try:
            self._syncing_text = True
            src = self.stealth_text.get("1.0", "end-1c")
            dst = self.text.get("1.0", "end-1c")
            if src != dst:
                cur = self.stealth_text.index("insert")
                self.text.delete("1.0", "end")
                self.text.insert("1.0", src)
                self.text.mark_set("insert", cur)
                if self.cfg['read_mode']:
                    self.root.after(50, self._apply_read_mode_bg)
            self._refresh_stealth_view()
        except Exception as e:
            print(f"[隐写同步] from stealth 失败: {e}")
        finally:
            self._syncing_text = False

    def _on_text_button_release(self, event):
        """鼠标释放后刷新隐写视图。"""
        if self.cfg.get('stealth_mode'):
            self.root.after(10, self._refresh_stealth_view)

    def _on_text_cursor_moved(self, event):
        """键盘导致光标/选区变化时保持隐写视图同步"""
        if self.cfg.get('stealth_mode'):
            self.root.after(10, self._refresh_stealth_view)

    def _calc_stealth_window_height(self):
        """精确计算隐写模式下窗口的总高度。

        使用 stealth_text 的实际渲染字体计算 linespace，避免新建 Font 对象
        与实际渲染字体不一致导致行高偏差和半行显示。
        """
        lines = self.cfg.get('stealth_lines', 3)
        try:
            # 使用 stealth_text 的实际字体，而非新建 Font 对象
            font_str = self.stealth_text.cget("font")
            f = tkfont.Font(font=font_str)
            line_height = f.metrics("linespace")
        except Exception:
            line_height = int(self.cfg['text_size'] * 1.6)

        text_height = line_height * lines
        # 容器上下边距（隐写模式已缩小到 20%）+ 横线总高 2px
        return text_height + STEALTH_PAD_Y * 2 + 2

    def _set_stealth_lines(self, lines):
        self.cfg['stealth_lines'] = clamp(lines, 1, 3)
        # 同步 IntVar，更新菜单 radiobutton 选中状态
        if hasattr(self, '_stealth_lines_var'):
            self._stealth_lines_var.set(self.cfg['stealth_lines'])
        self.stealth_text.configure(height=self.cfg['stealth_lines'])
        if self.cfg.get('stealth_mode'):
            self.stealth_text.update_idletasks()
            self._refresh_stealth_view()
            new_h = self._calc_stealth_window_height()
            wx = self.root.winfo_x()
            wy = self.root.winfo_y()
            self.root.geometry(f"{self.root.winfo_width()}x{new_h}")
            self.content_win.geometry(f"{self.root.winfo_width()}x{new_h}")
            self.content_win.update_idletasks()
            self._corner_dirty = True
            self._update_corners()
            self._layout_handle()
        self._save_config_debounced()

    def _refresh_stealth_view(self):
        """根据光标所在行刷新隐写文本框的显示范围与分隔线。

        核心逻辑：
        1. 计算应该显示在顶部的行号（top）
        2. 用 see(top) 将该行带入可见区域
        3. 用 dlineinfo 获取该行在控件内的 y 偏移
        4. 用 yview_scroll 像素级滚动，将 top 行精确对齐到控件顶部
        5. 不调用 see("insert")，避免与滚动定位冲突导致二次滚动

        三行模式：top = cursor-1（光标行在中间）
        两行模式：top = cursor-1（光标行在底部）
        一行模式：top = cursor（仅显示光标行）
        """
        if not self.cfg.get('stealth_mode') or not self.stealth_text.winfo_exists():
            return
        try:
            widget = self.stealth_text if self.root.focus_get() == self.stealth_text else self.text
            cur = widget.index("insert")
            line = int(cur.split(".")[0])

            mode = self.cfg['stealth_lines']
            if mode == 1:
                top = line
            elif mode == 2:
                top = max(1, line - 1)
            else:  # 3 lines
                top = max(1, line - 1)

            # Step 1: 将目标 top 行带入可见区域
            self.stealth_text.see(f"{top}.0")
            self.stealth_text.update_idletasks()

            # Step 2: 像素级微调，将 top 行精确对齐到控件顶部
            bbox = self.stealth_text.dlineinfo(f"{top}.0")
            if bbox:
                y_offset = bbox[1]
                if y_offset > 0:
                    self.stealth_text.yview_scroll(y_offset, "pixels")
                elif y_offset < 0:
                    self.stealth_text.yview_scroll(y_offset, "pixels")

            # 保持光标位置（不调用 see，避免二次滚动）
            self.stealth_text.mark_set("insert", cur)

            self.root.after(10, self._update_stealth_line)
        except Exception as e:
            print(f"[隐写视图] 刷新失败: {e}")

    def _update_stealth_line(self):
        """在光标所在行下方绘制与文本框等宽的横线（缺省 1px 黑线 + 1px 白线叠合）"""
        if not self.cfg.get('stealth_mode') or not self.stealth_text.winfo_exists():
            self._stealth_line_container.place_forget()
            self._stealth_line_visible = False
            return
        try:
            self.stealth_text.update_idletasks()
            self.content_frame.update_idletasks()

            bbox = self.stealth_text.dlineinfo("insert")
            if not bbox:
                self.root.after(20, self._update_stealth_line)
                return
            _, y, _, h, _ = bbox
            # 横线在 content_frame 上的 y：容器上边距 + 光标行底部
            line_y = STEALTH_PAD_Y + y + h

            # 宽度 = content_frame 宽度 - 左右各 TEXT_PAD_X
            fw = self.content_frame.winfo_width()
            if fw <= 1:
                fw = self.root.winfo_width()
            if fw <= 1:
                fw = 600
            width = max(1, fw - TEXT_PAD_X * 2)

            # 同时设置 configure(width=...) 和 place(width=...) 确保宽度生效
            self._stealth_line_container.configure(width=width)
            self._stealth_line_container.place(x=TEXT_PAD_X, y=line_y, width=width)
            self._stealth_line_container.update_idletasks()
            self._stealth_line_container.lift()
            self._stealth_line_visible = True
        except Exception as e:
            print(f"[隐写线] 更新失败: {e}")

    def _select_word(self, widget, event):
        """双击选词"""
        try:
            index = widget.index(f"@{event.x},{event.y}")
            widget.tag_remove("sel", "1.0", "end")
            widget.tag_add("sel", f"{index} wordstart", f"{index} wordend")
            widget.mark_set("insert", f"{index} wordend")
            widget.focus_set()
            self._on_text_cursor_moved(event)
            return "break"
        except Exception:
            return None

    def _select_line(self, widget, event):
        """三击选行"""
        try:
            index = widget.index(f"@{event.x},{event.y}")
            line = index.split(".")[0]
            widget.tag_remove("sel", "1.0", "end")
            widget.tag_add("sel", f"{line}.0", f"{line}.end")
            widget.mark_set("insert", f"{line}.end")
            widget.focus_set()
            self._on_text_cursor_moved(event)
            return "break"
        except Exception:
            return None

    def _update_title(self):
        if self.current_file:
            name = os.path.basename(self.current_file)
            mark = "*" if self._modified else ""
            title = f"{mark}{name} - {APP_NAME} [{self.current_encoding}]"
        else:
            mark = "*" if self._modified else ""
            title = f"{mark}未命名 - {APP_NAME}"
        self.root.title(title)

    def _focus_text(self):
        try:
            if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
                self.stealth_text.focus_set()
            else:
                self.text.focus_set()
        except Exception:
            pass

    def text_select_all(self):
        try:
            widget = self.root.focus_get()
            if widget not in (self.text, self.stealth_text):
                widget = self.stealth_text if self.cfg.get('stealth_mode') else self.text
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "end-1c")
        except Exception:
            pass

    def _on_window_configure(self, event):
        if event.widget == self.root:
            # 延迟更新，避免拖动时频繁重绘
            if self._resize_after_id:
                try:
                    self.root.after_cancel(self._resize_after_id)
                except Exception:
                    pass
            self._resize_after_id = self.root.after(30, self._on_window_resized)

    def _sync_content_window(self):
        """同步内容窗口与背景窗口的位置和大小"""
        try:
            if hasattr(self, 'content_win') and self.content_win and self.content_win.winfo_exists():
                x = self.root.winfo_x()
                y = self.root.winfo_y()
                w = self.root.winfo_width()
                h = self.root.winfo_height()
                self.content_win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception as e:
            print(f"[同步内容窗口] 失败: {e}")

    def _on_window_resized(self):
        self._resize_after_id = None
        self._sync_content_window()
        self._layout_corners()
        self._layout_handle()
        if self._sb_visible:
            self._redraw_scrollbar()
        if self.cfg.get('stealth_mode'):
            self._refresh_stealth_view()
        if self._window_visible:
            self.cfg['window_width'] = self.root.winfo_width()
            self.cfg['window_x'] = self.root.winfo_x()
            self.cfg['window_y'] = self.root.winfo_y()
            if not self.cfg.get('stealth_mode'):
                self.cfg['window_height'] = self.root.winfo_height()
            self._save_config_debounced()

    def _on_focus_change(self):
        self._lift_all()
        self._update_handle()

    # -------------------------------------------------------------------------
    # 角部边框
    # -------------------------------------------------------------------------

    def _init_corners(self):
        """初始化四角框线：角元素已在 _init_content 中创建（位于文本之下），
        此处仅完成初始布局绘制。注意：只调用 _layout_corners()，不调用 _layout_all()，
        因为 _init_handle 还未执行，handle_win 尚不存在。"""
        self._layout_corners()

    def _layout_all(self):
        self._layout_corners()
        self._layout_handle()
        self._update_handle()
        if self._sb_visible:
            self._redraw_scrollbar()

    def _layout_corners(self):
        # 隐写模式下完全隐藏四角线框与缩放热区
        if self.cfg.get('stealth_mode'):
            for name in self._corner_frames:
                self._corner_frames[name].place_forget()
                self._corner_canvases[name].place_forget()
            return

        cs = max(MIN_CORNER_LEN, int(self.cfg['corner_size']))
        lw = max(MIN_CORNER_LINE, int(self.cfg['corner_line_width']))
        hs = CORNER_HOT_SIZE
        margin = CORNER_MARGIN

        # 热区位置（14x14）
        for name in self._corner_frames:
            frame = self._corner_frames[name]
            frame.configure(width=hs, height=hs)
            relx = 1.0 if 'e' in name else 0.0
            rely = 1.0 if 's' in name else 0.0
            x_offset = margin if 'w' in name else -margin
            y_offset = margin if 'n' in name else -margin
            frame.place(relx=relx, rely=rely, anchor=name, x=x_offset, y=y_offset)

        # 视觉画布位置：以角为锚点，大小 = size，确保框线完整显示
        for name in self._corner_canvases:
            canvas = self._corner_canvases[name]
            canvas.configure(width=cs, height=cs)
            relx = 0.0 if 'w' in name else 1.0
            rely = 0.0 if 'n' in name else 1.0
            anchor = name
            x_offset = margin if 'w' in name else -margin
            y_offset = margin if 'n' in name else -margin
            canvas.place(relx=relx, rely=rely, anchor=anchor, x=x_offset, y=y_offset)

        if self._corner_dirty:
            self._draw_all_corners()
            self._corner_dirty = False

        # 四角已用 place() 布局，热区 frame 在画布之上（用于缩放交互）。
        # 由于画布和热区在 text_container 之前创建，天然位于文本之下，无需 lower()。

    def _draw_all_corners(self):
        self._draw_corners_on_bg()

    def _draw_corners_on_bg(self):
        """在四个独立视觉画布上分别绘制对应角的框线。"""
        size = max(MIN_CORNER_LEN, int(self.cfg['corner_size']))
        lw = max(MIN_CORNER_LINE, int(self.cfg['corner_line_width']))

        color = self.cfg['corner_color']
        if self.cfg['invert_mode']:
            color = invert_color(color)
        corner_op = self.cfg['corner_opacity']
        # 按 raw_bg 混合，与 content_win 的 LWA_ALPHA 统一叠加
        raw_bg = self.cfg['bg_color']
        if self.cfg['invert_mode']:
            raw_bg = invert_color(raw_bg)
        color = mix_color(color, corner_op, raw_bg)

        half = max(1, lw // 2)
        line_len = max(1, size - lw)
        end = half + line_len

        def draw_corner(canvas, name):
            canvas.delete("all")
            if name == "nw":
                canvas.create_line(half, half, end, half, fill=color, width=lw)
                canvas.create_line(half, half, half, end, fill=color, width=lw)
            elif name == "ne":
                canvas.create_line(size - end, half, size - half, half, fill=color, width=lw)
                canvas.create_line(size - half, half, size - half, end, fill=color, width=lw)
            elif name == "sw":
                canvas.create_line(half, size - end, half, size - half, fill=color, width=lw)
                canvas.create_line(half, size - half, end, size - half, fill=color, width=lw)
            elif name == "se":
                canvas.create_line(size - end, size - half, size - half, size - half, fill=color, width=lw)
                canvas.create_line(size - half, size - end, size - half, size - half, fill=color, width=lw)

        for name in self._corner_canvases:
            draw_corner(self._corner_canvases[name], name)

    def _update_corners(self):
        self._corner_dirty = True
        self._layout_corners()

    def _on_resize_start(self, event, edge):
        # 隐写模式下禁止纵向缩放（高度由行数决定）
        if self.cfg.get('stealth_mode') and ('n' in edge or 's' in edge):
            return
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self._resize_edge = edge
        self._resize_start = (event.x_root, event.y_root, w, h)
        self._corner_dirty = True

    def _on_resize(self, event):
        if not self._resize_edge:
            return
        sx, sy, sw, sh = self._resize_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        edge = self._resize_edge

        nw, nh = sw, sh
        nx, ny = self.root.winfo_x(), self.root.winfo_y()

        if 'e' in edge:
            nw = sw + dx
        if 'w' in edge:
            nw = sw - dx
            nx = sx + dx
        if 's' in edge:
            nh = sh + dy
        if 'n' in edge:
            nh = sh - dy
            ny = sy + dy

        nw = max(MIN_WINDOW_W, nw)
        nh = max(MIN_WINDOW_H, nh)
        self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")

    def _on_resize_end(self, event):
        if self._resize_edge:
            self.cfg['window_width'] = self.root.winfo_width()
            self.cfg['window_x'] = self.root.winfo_x()
            self.cfg['window_y'] = self.root.winfo_y()
            if not self.cfg.get('stealth_mode'):
                self.cfg['window_height'] = self.root.winfo_height()
            self._save_config_debounced()
            self._resize_edge = None
            self._layout_handle()
            self._layout_corners()

    def _get_resize_edge_at(self, x, y):
        """根据鼠标坐标判断当前是否处于四角缩放热区"""
        if self.cfg.get('stealth_mode'):
            return None
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        hs = CORNER_HOT_SIZE
        if x <= hs and y <= hs:
            return "nw"
        if x >= w - hs and y <= hs:
            return "ne"
        if x <= hs and y >= h - hs:
            return "sw"
        if x >= w - hs and y >= h - hs:
            return "se"
        return None

    def _get_active_text_widget(self):
        """返回当前可见的书写框控件"""
        if self.cfg.get('stealth_mode'):
            return self.stealth_text if self._is_stealth_container_visible() else None
        return self.text

    def _root_to_widget_coords(self, widget, rx, ry):
        """将 root 窗口内坐标转换为指定控件内坐标"""
        try:
            sx = self.root.winfo_rootx() + rx
            sy = self.root.winfo_rooty() + ry
            wx = sx - widget.winfo_rootx()
            wy = sy - widget.winfo_rooty()
            return wx, wy
        except Exception:
            return rx, ry

    def _is_point_in_widget(self, widget, rx, ry):
        """判断 root 坐标是否落在指定控件几何区域内"""
        try:
            wx = widget.winfo_rootx() - self.root.winfo_rootx()
            wy = widget.winfo_rooty() - self.root.winfo_rooty()
            ww = widget.winfo_width()
            wh = widget.winfo_height()
            return wx <= rx <= wx + ww and wy <= ry <= wy + wh
        except Exception:
            return False

    def _forward_text_button1(self, widget, rx, ry):
        """将 root 的 Button-1 转发给书写框：设置焦点并定位光标"""
        try:
            widget.focus_set()
            wx, wy = self._root_to_widget_coords(widget, rx, ry)
            idx = widget.index(f"@{wx},{wy}")
            widget.mark_set("insert", idx)
            widget.see("insert")
            self._text_select_widget = widget
            self._text_select_anchor = idx
            self._text_selecting = True
            self._text_click_moved = False
        except Exception:
            pass

    def _forward_text_motion(self, widget, rx, ry):
        """将 root 的 B1-Motion 转发给书写框：模拟拖拽选区"""
        try:
            widget.focus_set()
            wx, wy = self._root_to_widget_coords(widget, rx, ry)
            idx = widget.index(f"@{wx},{wy}")
            widget.mark_set("insert", idx)
            widget.see("insert")
            if self._text_select_anchor:
                widget.tag_remove("sel", "1.0", "end")
                # Tkinter 的 tag_add 会自动处理前后顺序
                widget.tag_add("sel", self._text_select_anchor, idx)
            self._text_click_moved = True
        except Exception:
            pass

    def _forward_text_wheel(self, widget, rx, ry, delta):
        """将 root 的 MouseWheel 转发给普通文本框。隐写模式由 stealth_text 自身处理，不转发。"""
        try:
            if widget is self.stealth_text:
                return False
            if not self._is_point_in_widget(widget, rx, ry):
                return False
            # 左键按下时调整背景透明度
            if self._is_left_button_held():
                d = 1 if delta > 0 else -1
                new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + d * 0.05))
                self.cfg['bg_opacity'] = round(new_op, 2)
                self._apply_window_style()
                self._save_config_debounced()
                return True
            # 每次滚动一行
            lines = -1 if delta > 0 else 1
            widget.yview_scroll(lines, "units")
            return True
        except Exception:
            return False

    def _on_root_button_press(self, event):
        """根窗口按下：仅处理四角缩放，其余情况聚焦文本框。"""
        edge = self._get_resize_edge_at(event.x, event.y)
        if edge:
            self._on_resize_start(event, edge)
            return
        self._focus_text()

    def _on_root_resize(self, event):
        """根窗口拖动：仅处理缩放。"""
        if self._resize_edge:
            self._on_resize(event)

    def _on_root_resize_end(self, event):
        """根窗口释放：仅结束缩放。"""
        if self._resize_edge:
            self._on_resize_end(event)
            self._on_root_motion(event)

    def _on_root_motion(self, event):
        """根窗口移动：在四角热区切换鼠标指针"""
        try:
            edge = self._get_resize_edge_at(event.x, event.y)
            cursor = {
                "nw": "top_left_corner",
                "ne": "top_right_corner",
                "sw": "bottom_left_corner",
                "se": "bottom_right_corner",
            }.get(edge, "")
            self.root.config(cursor=cursor)
            self.content_win.config(cursor=cursor)
        except Exception:
            pass

    def _on_content_button_press(self, event):
        """内容窗口按下：仅处理四角缩放，其余情况聚焦文本框。
        文本框自身为实色不透明控件，事件由 Tkinter 原生处理。"""
        if event.widget in (self.text, self.stealth_text):
            return
        edge = self._get_resize_edge_at(event.x, event.y)
        if edge:
            self._on_resize_start(event, edge)
            return
        self._focus_text()

    def _on_content_resize(self, event):
        """内容窗口拖动：仅处理缩放。"""
        if event.widget in (self.text, self.stealth_text):
            return
        self._on_resize(event)

    def _on_content_resize_end(self, event):
        """内容窗口释放：仅结束缩放。"""
        if event.widget in (self.text, self.stealth_text):
            return
        self._on_resize_end(event)
        self._on_content_motion(event)

    def _on_root_wheel(self, event):
        """根窗口滚轮：仅在普通模式下转发给文本框。隐写模式由 stealth_text 自身处理。"""
        if self.cfg.get('stealth_mode'):
            return None
        widget = self.text
        if widget and self._forward_text_wheel(widget, event.x, event.y, event.delta):
            return "break"

    def _on_content_motion(self, event):
        """内容窗口移动：在四角热区切换鼠标指针"""
        # 事件来自文本框时不干预，避免干扰文本交互
        if event.widget in (self.text, self.stealth_text):
            return
        try:
            edge = self._get_resize_edge_at(event.x, event.y)
            cursor = {
                "nw": "top_left_corner",
                "ne": "top_right_corner",
                "sw": "bottom_left_corner",
                "se": "bottom_right_corner",
            }.get(edge, "")
            self.content_win.config(cursor=cursor)
            self.root.config(cursor=cursor)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 圆形手柄（使用SetWindowRgn实现真圆形，无色键）
    # -------------------------------------------------------------------------

    def _init_handle(self):
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        # 使用无父窗口的 Toplevel（parent=None），避免 root 的 COLORKEY 透明属性影响子窗口渲染
        self.handle_win = tk.Toplevel()
        self.handle_win.withdraw()
        self.handle_win.overrideredirect(True)
        self.handle_win.attributes("-topmost", True)

        # 手柄窗口使用 COLORKEY 色键透明 + SetWindowRgn 实现圆形
        # 非 COLORKEY 区域（绘制的圆环/实心圆）可见，COLORKEY 区域透明
        self.handle_win.configure(bg=COLORKEY, bd=0, highlightthickness=0)
        self.handle_win.geometry(f"{hs}x{hs}+0+0")

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.handle_win.iconbitmap(self.icon_path)
            except Exception:
                pass

        self.handle_canvas = tk.Canvas(
            self.handle_win, bg=COLORKEY, highlightthickness=0, bd=0,
            width=hs, height=hs, cursor="fleur")
        self.handle_canvas.pack(fill="both", expand=True)

        self.handle_win.update_idletasks()
        self._handle_hwnd = self.handle_win.winfo_id()

        # 使用 LWA_COLORKEY 色键透明，alpha=255（完全不透明）
        # 手柄不透明度通过绘制颜色本身控制，不通过 LWA_ALPHA（避免黑底）
        set_layered_transparent(
            self._handle_hwnd, 255,
            use_colorkey=True, show_taskbar=False)

        self._set_handle_region(hs)

        self.root.after(200, self._show_handle)

        self.handle_canvas.bind("<Enter>", lambda e: self._on_handle_hover(True))
        self.handle_canvas.bind("<Leave>", lambda e: self._on_handle_hover(False))
        self.handle_canvas.bind("<ButtonPress-1>", self._on_handle_press)
        self.handle_canvas.bind("<B1-Motion>", self._on_handle_drag)
        self.handle_canvas.bind("<ButtonRelease-1>", self._on_handle_release)
        self.handle_canvas.bind("<MouseWheel>", self._on_handle_wheel)
        self.handle_canvas.bind("<Button-3>", self._show_handle_menu)
        self.handle_canvas.bind("<Button-2>", lambda e: self.toggle_stealth())

        self.handle_menu = tk.Menu(self.root, tearoff=0)
        self.handle_menu.add_command(label="显示/隐藏主窗口", command=self._tray_toggle)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="打开文件", command=self.file_open)
        self.handle_menu.add_command(label="保存文件", command=self.file_save)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(
            label="隐写模式" if not self.cfg.get('stealth_mode') else "退出隐写模式",
            command=self.toggle_stealth)
        self.handle_menu.add_separator()
        # 隐写行数选择：radiobutton 自带选中指示器，无需额外图标
        for lines, label in [(1, "一行模式"), (2, "两行模式"), (3, "三行模式")]:
            self.handle_menu.add_radiobutton(
                label=label,
                value=lines,
                variable=self._stealth_lines_var,
                command=lambda n=lines: self._set_stealth_lines(n))
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="反色显示", command=self.toggle_invert)
        self.handle_menu.add_command(label="易读模式", command=self.toggle_read)
        self.handle_menu.add_command(label="置顶模式", command=self.toggle_topmost)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="设置仪表盘", command=self.show_settings)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="关于", command=self._show_about)
        self.handle_menu.add_command(label="退出", command=self.exit_app)

    def _set_handle_region(self, hs=None):
        """设置手柄窗口为圆形区域。

        hs 参数直接传入窗口尺寸，避免读取 stale winfo_width/height
        导致裁剪圆心与绘制圆心错位。
        """
        try:
            if hs is None:
                hs = self.handle_win.winfo_width()
            if hs > 0:
                rgn = gdi32.CreateEllipticRgn(0, 0, hs, hs)
                user32.SetWindowRgn(self._handle_hwnd, rgn, True)
        except Exception as e:
            print(f"[手柄] 区域设置失败: {e}")

    def _show_handle(self):
        try:
            self.handle_win.deiconify()
            self.handle_win.lift()
            self._layout_handle()
            self._update_handle()
        except Exception as e:
            print(f"[手柄] 显示失败: {e}")

    def _layout_handle(self):
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        self.handle_win.geometry(f"{hs}x{hs}")
        self.handle_canvas.configure(width=hs, height=hs)

        wx = self.root.winfo_x()
        wy = self.root.winfo_y()
        size = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        r = size // 2

        # 手柄位于文本框/隐写框左侧，圆心固定（使用 HANDLE_REF_R 不随尺寸变化），X 方向间距 20px
        hx = wx - hs // 2 - HANDLE_REF_R - 20
        hy = wy + HANDLE_REF_R - hs // 2

        if hx < 0:
            hx = 0
        if hy < 0:
            hy = 0

        self.handle_win.geometry(f"+{hx}+{hy}")
        # 等待 geometry 生效后再设置圆形区域，避免 stale 尺寸导致圆心错位
        self.handle_win.update_idletasks()
        self.handle_win.lift()
        self._set_handle_region(hs)

    def _update_handle(self):
        self.handle_canvas.delete("all")
        size = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        color = self.cfg.get('handle_color', self.cfg['corner_color'])
        if self.cfg['invert_mode']:
            color = invert_color(color)

        # 不与 ROOT_BG 预乘，直接使用原始颜色。
        # handle_win 使用 LWA_COLORKEY 透明，COLORKEY 区域透明，
        # 非 COLORKEY 区域（绘制内容）完全不透明，无黑底。
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        cx, cy = hs // 2, hs // 2
        r = size // 2

        focused = self.root.focus_get() in (self.text, self.stealth_text)

        if focused:
            # 获得焦点：实心圆 + 内部高亮细环 + 黑色外环
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=color, outline=color, width=2)
            self.handle_canvas.create_oval(
                cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4,
                outline=mix_color("#FFFFFF", 0.5, color), width=2)
            # 黑色外环：同圆心，半径比白色圆环大2px，便于在白色背景上识别
            self.handle_canvas.create_oval(
                cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                outline="#000000", width=1)
        else:
            # 未获得焦点：圆环 + 中心不可见填充（捕获鼠标事件）
            # 中心 fill="#010102" 仅比 COLORKEY(#010101) 多1位蓝色，
            # 肉眼不可辨，但非 COLORKEY 不会被 LWA_COLORKEY 透明化，能捕获鼠标事件。
            ring_w = 3
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color, width=ring_w, fill="")
            # 中心填充：用比 COLORKEY 多1位的颜色，视觉透明但捕获事件
            inner_r = max(1, r - ring_w)
            self.handle_canvas.create_oval(
                cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                fill="#010102", outline="")
            # 黑色外环：同圆心，半径比白色圆环大2px，便于在白色背景上识别
            self.handle_canvas.create_oval(
                cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                outline="#000000", width=1)

    def _on_handle_hover(self, entering):
        self._update_handle()

    def _show_handle_menu(self, event):
        try:
            label = "退出隐写模式" if self.cfg.get('stealth_mode') else "隐写模式"
            try:
                self.handle_menu.entryconfigure("隐写模式", label=label)
                self.handle_menu.entryconfigure("退出隐写模式", label=label)
            except Exception:
                pass
            self.handle_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.handle_menu.grab_release()

    def _on_handle_press(self, event):
        self._drag_active = True
        self._drag_dx = event.x_root - self.root.winfo_x()
        self._drag_dy = event.y_root - self.root.winfo_y()
        self._lift_all()
        if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
            self.stealth_text.focus_set()
        else:
            self.text.focus_set()
        self._update_handle()

    def _lift_all(self):
        """将所有窗口提到最上层"""
        try:
            user32.SetForegroundWindow(self._root_hwnd)
        except Exception:
            pass
        self.root.attributes("-topmost", True)
        self.content_win.attributes("-topmost", True)
        self.root.after(50, lambda: (
            self.root.attributes("-topmost", self.cfg['topmost']),
            self.content_win.attributes("-topmost", self.cfg['topmost'])
        ))
        self.root.lift()
        self.content_win.lift()
        self.handle_win.lift()
        if self.cfg['show_panel']:
            self.panel.attributes("-topmost", True)
            self.panel.lift()

    def _on_handle_drag(self, event):
        if not self._drag_active:
            return
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        self.root.geometry(f"+{x}+{y}")
        self._layout_handle()

    def _on_handle_release(self, event):
        if self._drag_active:
            self.cfg['window_x'] = self.root.winfo_x()
            self.cfg['window_y'] = self.root.winfo_y()
            self._save_config_debounced()
            self._drag_active = False

    def _is_left_button_held(self):
        """检测鼠标左键是否按下"""
        try:
            return (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
        except Exception:
            return False

    def _is_ctrl_held(self):
        """检测 Ctrl 键是否按下"""
        try:
            return (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        except Exception:
            return False

    def _on_handle_wheel(self, event):
        """手柄滚轮：左键+滚轮→底色透明度，Ctrl+滚轮→底色透明度，直接滚轮→文字透明度"""
        delta = 1 if event.delta > 0 else -1
        if self._is_left_button_held() or self._is_ctrl_held():
            # 左键或Ctrl按下：仅调整底色透明度
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['bg_opacity']) > 0.001:
                self.cfg['bg_opacity'] = round(new_op, 2)
                self._apply_window_style()
                self._save_config_debounced()
        else:
            # 无修饰键：调整文字透明度
            new_op = max(0.1, min(1.0, self.cfg['text_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['text_opacity']) > 0.001:
                self.cfg['text_opacity'] = round(new_op, 2)
                self._apply_text_appearance()
                self._save_config_debounced()
        return "break"

    def _on_text_wheel_smooth(self, event):
        """文本框滚轮：左键按下时调整背景透明度，否则顺滑滚动文本"""
        # 左键按下时滚轮调整背景透明度
        if self._is_left_button_held():
            delta = 1 if event.delta > 0 else -1
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            self.cfg['bg_opacity'] = round(new_op, 2)
            self._apply_window_style()
            self._save_config_debounced()
            return "break"

        widget = event.widget
        if widget not in (self.text, self.stealth_text):
            return None
        # 每次滚轮事件精确滚动一行，避免步进过大导致隐写框出现半行或横线跳动
        lines = -1 if event.delta > 0 else 1
        widget.yview_scroll(lines, "units")
        return "break"

    def _on_stealth_wheel(self, event):
        """隐写文本框滚轮：累积 delta，每满 120 移动光标一行并刷新视图。"""
        if self._is_left_button_held():
            delta = 1 if event.delta > 0 else -1
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            self.cfg['bg_opacity'] = round(new_op, 2)
            self._apply_window_style()
            self._save_config_debounced()
            return "break"

        widget = self.stealth_text
        self._stealth_wheel_acc += event.delta
        threshold = 120

        try:
            lines = 0
            while self._stealth_wheel_acc >= threshold:
                lines -= 1
                self._stealth_wheel_acc -= threshold
            while self._stealth_wheel_acc <= -threshold:
                lines += 1
                self._stealth_wheel_acc += threshold

            if lines == 0:
                return "break"

            cur = widget.index("insert")
            line = int(cur.split(".")[0])
            total = int(widget.index("end-1c").split(".")[0])
            if total <= 0:
                total = 1
            new_line = max(1, min(total, line + lines))
            widget.mark_set("insert", f"{new_line}.0")
            widget.see("insert")
            self._refresh_stealth_view()
        except Exception:
            pass
        return "break"

    def _route_wheel_to_text(self, event, text_widget):
        """在容器/空白区域滚动时，将事件转发给对应文本框"""
        if not text_widget.winfo_exists():
            return None
        event.widget = text_widget
        if text_widget is self.stealth_text:
            return self._on_stealth_wheel(event)
        return self._on_text_wheel_smooth(event)

    # -------------------------------------------------------------------------
    # 仪表盘（原操作面板，使用色键#010101）
    # -------------------------------------------------------------------------

    def _init_panel(self):
        self.panel = tk.Toplevel(self.root)
        self.panel.overrideredirect(True)

        # 仪表盘使用色键 #010101 实现透明区域
        self.panel.configure(bg=COLORKEY)

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.panel.iconbitmap(self.icon_path)
            except Exception:
                pass

        if self.cfg['panel_x'] is None or self.cfg['panel_y'] is None:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            px = (sw - PANEL_WIDTH) // 2
            py = (sh - PANEL_HEIGHT) // 3
        else:
            px = int(self.cfg['panel_x'])
            py = int(self.cfg['panel_y'])

        self.panel.geometry(f"{PANEL_WIDTH}x{PANEL_HEIGHT}+{px}+{py}")

        self._panel_hwnd = self.panel.winfo_id()
        set_layered_transparent(
            self._panel_hwnd,
            int(max(MIN_PANEL_OPACITY, self.cfg['panel_opacity']) * 255),
            use_colorkey=True,
            show_taskbar=False)

        self.panel_outer = tk.Frame(self.panel, bg="#444444", bd=0)
        self.panel_outer.pack(fill="both", expand=True, padx=PANEL_PADDING, pady=PANEL_PADDING)

        self.panel_inner = tk.Frame(self.panel_outer, bg=self.cfg['panel_bg_color'])
        self.panel_inner.pack(fill="both", expand=True)

        btn_color_14 = "#333333"
        btn_color_58 = "#3d3d3d"
        btn_color_x = "#2a2a2a"
        btn_color_drag = "#ff8800"

        buttons = [
            ("O",   "打开文件\nCtrl+O",       self.file_open,      btn_color_14, False),
            ("S",   "保存文件\nCtrl+S",       self.file_save,      btn_color_14, False),
            ("SN",  "另存为\nCtrl+Shift+S",   self.file_save_as,   btn_color_14, False),
            ("隐",  "隐写模式\n中键切换",     self.toggle_stealth, btn_color_58, "stealth_mode"),
            ("反",  "反色显示\nCtrl+F",       self.toggle_invert,  btn_color_58, "invert_mode"),
            ("易",  "易读模式\nCtrl+Shift+R", self.toggle_read,    btn_color_58, "read_mode"),
            ("顶",  "置顶模式\nCtrl+T",       self.toggle_topmost, btn_color_58, "topmost"),
            ("色",  "主题切换\nCtrl+M",       self.toggle_theme,   btn_color_58, False),
            ("控",  "设置仪表盘\nCtrl+K",     self.show_settings,  btn_color_58, False),
            ("X",   "退出程序",               self.exit_app,       btn_color_x,  False),
        ]

        self.panel_buttons = {}
        self.panel_button_containers = {}
        self.panel_button_dots = {}
        for i, (text, tip, cmd, bg, state_key) in enumerate(buttons):
            container = tk.Frame(self.panel_inner, bg=bg, width=PANEL_BTN_SIZE, height=PANEL_BTN_SIZE)
            container.pack_propagate(False)
            container.grid(row=0, column=i, padx=PANEL_BTN_GAP//2, pady=0)
            self.panel_button_containers[text] = container

            btn = tk.Button(
                container,
                text=text,
                command=cmd,
                bg=bg,
                fg="#ffffff",
                font=("Microsoft YaHei UI", 9, "bold"),
                bd=0,
                relief="flat",
                activebackground="#555555",
                activeforeground="#ffffff",
                cursor="hand2"
            )
            btn.pack(fill="both", expand=True)
            self.panel_buttons[text] = btn

        # 统一创建仪表盘小红点：作为按钮容器的直接子控件，固定坐标定位。
        # 容器 pack_propagate(False) 保证尺寸固定，坐标不受布局时序影响。
        # dot canvas bg 与按钮容器 bg 一致，避免 COLORKEY 在子控件中不透明产生黑块。
        dot_size = 8
        for text, key in [("隐", "stealth_mode"), ("反", "invert_mode"),
                          ("易", "read_mode"), ("顶", "topmost")]:
            container = self.panel_button_containers[text]
            container_bg = container.cget("bg")
            dot_canvas = tk.Canvas(container, bg=container_bg, width=dot_size, height=dot_size,
                                   highlightthickness=0, bd=0)
            # 6x6 红色实心圆点，无描边
            dot_canvas.create_oval(1, 1, 7, 7, fill="#ff3333", outline="")
            # 点击穿透到按钮，避免红点拦截按钮点击
            dot_canvas.bind("<Button-1>", lambda e, t=text: self.panel_buttons[t].invoke())
            dot_canvas.place_forget()
            self.panel_button_dots[text] = dot_canvas

        # 拖动按钮
        drag_container = tk.Frame(self.panel_inner, bg=btn_color_drag,
                                  width=PANEL_BTN_SIZE, height=PANEL_BTN_SIZE)
        drag_container.pack_propagate(False)
        drag_container.grid(row=0, column=len(buttons), padx=PANEL_BTN_GAP//2, pady=0)
        drag_btn = tk.Label(drag_container, text="⋮⋮", bg=btn_color_drag, fg="#ffffff",
                            font=("Microsoft YaHei UI", 9, "bold"), cursor="fleur")
        drag_btn.pack(fill="both", expand=True)
        drag_btn.bind("<ButtonPress-1>", self._on_panel_press)
        drag_btn.bind("<B1-Motion>", self._on_panel_drag)
        drag_btn.bind("<ButtonRelease-1>", self._on_panel_release)

        # 整体拖动
        self.panel_outer.bind("<ButtonPress-1>", self._on_panel_press)
        self.panel_outer.bind("<B1-Motion>", self._on_panel_drag)
        self.panel_outer.bind("<ButtonRelease-1>", self._on_panel_release)
        self.panel_inner.bind("<ButtonPress-1>", self._on_panel_press)
        self.panel_inner.bind("<B1-Motion>", self._on_panel_drag)
        self.panel_inner.bind("<ButtonRelease-1>", self._on_panel_release)

        if self.cfg['show_panel']:
            self.panel.deiconify()
        else:
            self.panel.withdraw()

        # 初始化小红点状态：根据当前 cfg 显示/隐藏各开关指示灯
        self._update_panel_button_states()

    def _update_panel_button_states(self):
        """统一刷新仪表盘开关小红点，状态与 cfg 严格对应。
        小红点是按钮容器的子控件，固定坐标 place，不受布局时序影响。"""
        dot_map = {
            "隐": "stealth_mode",
            "反": "invert_mode",
            "易": "read_mode",
            "顶": "topmost",
        }
        for text, key in dot_map.items():
            canvas = self.panel_button_dots.get(text)
            if not canvas or not canvas.winfo_exists():
                continue
            enabled = bool(self.cfg.get(key, False))
            if enabled:
                canvas.place(x=PANEL_BTN_SIZE - 8 - 1, y=3)
                canvas.tk.call('raise', canvas._w)
            else:
                canvas.place_forget()

    def _on_panel_press(self, event):
        self._panel_drag_active = True
        self._panel_drag_dx = event.x_root - self.panel.winfo_x()
        self._panel_drag_dy = event.y_root - self.panel.winfo_y()
        self.panel.lift()

    def _on_panel_drag(self, event):
        if not self._panel_drag_active:
            return
        x = event.x_root - self._panel_drag_dx
        y = event.y_root - self._panel_drag_dy
        self.panel.geometry(f"+{x}+{y}")

    def _on_panel_release(self, event):
        if self._panel_drag_active:
            self.cfg['panel_x'] = self.panel.winfo_x()
            self.cfg['panel_y'] = self.panel.winfo_y()
            self._save_config_debounced()
            self._panel_drag_active = False

    def toggle_panel(self):
        self.cfg['show_panel'] = not self.cfg['show_panel']
        if self.cfg['show_panel']:
            self.panel.deiconify()
            self.panel.lift()
        else:
            self.panel.withdraw()
        self._save_config_debounced()

    # -------------------------------------------------------------------------
    # 模式切换
    # -------------------------------------------------------------------------

    def toggle_invert(self):
        self.cfg['invert_mode'] = not self.cfg['invert_mode']
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._save_config_debounced()

    def toggle_read(self):
        self.cfg['read_mode'] = not self.cfg['read_mode']
        self._apply_window_style()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._save_config_debounced()

    def toggle_topmost(self):
        self.cfg['topmost'] = not self.cfg['topmost']
        self.root.attributes("-topmost", self.cfg['topmost'])
        self.content_win.attributes("-topmost", self.cfg['topmost'])
        self.handle_win.attributes("-topmost", self.cfg['topmost'])
        if hasattr(self, 'panel') and self.panel:
            self.panel.attributes("-topmost", self.cfg['topmost'])
        if self.cfg['topmost']:
            self.root.lift()
            self.content_win.lift()
            self.handle_win.lift()
            if hasattr(self, 'panel') and self.panel and self.cfg['show_panel']:
                self.panel.lift()
        self._update_panel_button_states()
        self._save_config_debounced()

    def apply_theme(self, mode):
        """切换深色/浅色模式，应用预设配色并刷新界面。

        通过让控件颜色与背景颜色保持一致（深底白字 / 白底黑字），
        减少文字抗锯齿在不同背景上产生的彩色/亮色毛边。
        主题模式目前与反色模式独立，未来可按指令替代反色模式。
        """
        mode = mode if mode in THEME_PALETTES else "dark"
        self.cfg['theme_mode'] = mode
        palette = THEME_PALETTES[mode]
        for key, value in palette.items():
            self.cfg[key] = value

        self._apply_window_style()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._save_config_debounced()

    def _apply_panel_style(self):
        """应用仪表盘外观（背景色 + 透明度）。"""
        try:
            if hasattr(self, 'panel_inner') and self.panel_inner:
                self.panel_inner.configure(bg=self.cfg['panel_bg_color'])
            if hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
                if not hasattr(self, '_panel_hwnd') or not self._panel_hwnd:
                    self._panel_hwnd = self.panel.winfo_id()
                alpha = int(max(MIN_PANEL_OPACITY, self.cfg['panel_opacity']) * 255)
                set_layered_transparent(self._panel_hwnd, alpha, use_colorkey=True, show_taskbar=False)
        except Exception as e:
            print(f"[仪表盘样式] 应用失败: {e}")

    def toggle_theme(self):
        """仪表盘按钮：在深色/浅色模式间切换。"""
        new_mode = "light" if self.cfg.get('theme_mode', 'dark') == 'dark' else 'dark'
        self.apply_theme(new_mode)

    def toggle_stealth(self, lines=None):
        """切换隐写模式。文本框集群与隐写框集群互斥切换，左上角锚定，宽度不变。"""
        self.cfg['stealth_mode'] = not self.cfg.get('stealth_mode', False)
        if lines is not None:
            self.cfg['stealth_lines'] = clamp(lines, 1, 3)

        wx = self.root.winfo_x()
        wy = self.root.winfo_y()
        ww = self.root.winfo_width()

        if self.cfg['stealth_mode']:
            # 保存当前窗口高度（用于恢复）
            self._normal_window_height = self.root.winfo_height()

            # 同步内容和光标
            content = self.text.get("1.0", "end-1c")
            cur = self.text.index("insert")
            self.stealth_text.configure(height=self.cfg['stealth_lines'])
            self.stealth_text.delete("1.0", "end")
            self.stealth_text.insert("1.0", content)
            self.stealth_text.mark_set("insert", cur)

            # 切换容器：隐藏文本框集群，显示隐写框集群
            self.text_container.pack_forget()
            self.sb_container.place_forget()
            self.stealth_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=STEALTH_PAD_Y)

            # 调整窗口高度（左上角锚定，宽度不变）
            self.stealth_text.update_idletasks()
            new_h = self._calc_stealth_window_height()
            self.root.geometry(f"{ww}x{new_h}")
            self.content_win.geometry(f"{ww}x{new_h}")
            self.content_win.update_idletasks()

            self.stealth_text.focus_set()
            self._corner_dirty = True
            self._update_corners()
            self._refresh_stealth_view()
        else:
            # 退出隐写模式：先同步内容
            try:
                content = self.stealth_text.get("1.0", "end-1c")
                cur = self.stealth_text.index("insert")
                if content != self.text.get("1.0", "end-1c"):
                    self.text.delete("1.0", "end")
                    self.text.insert("1.0", content)
                self.text.mark_set("insert", cur)
            except Exception:
                pass

            # 切换容器：隐藏隐写框集群，显示文本框集群
            self.stealth_container.pack_forget()
            self._stealth_line_container.place_forget()
            self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)

            # 恢复窗口高度
            if self._normal_window_height and self._normal_window_height > MIN_WINDOW_H:
                new_h = self._normal_window_height
            else:
                new_h = max(MIN_WINDOW_H, self.cfg.get('window_height', 400))
            self.root.geometry(f"{ww}x{new_h}")
            self.content_win.geometry(f"{ww}x{new_h}")

            self.text.focus_set()
            self._corner_dirty = True
            self._update_corners()
            if self.cfg['show_scrollbar']:
                self._set_scrollbar_visible(self._sb_visible)

        self._apply_text_appearance()
        self._update_panel_button_states()
        self._layout_handle()
        self._save_config_debounced()

    def _apply_stealth_state(self):
        """根据当前 cfg 应用隐写模式状态（不修改配置，仅恢复显示）"""
        try:
            visible = self.cfg.get('stealth_mode', False)
            lines = self.cfg.get('stealth_lines', 3)
            self.stealth_text.configure(height=lines)

            if visible:
                # 进入隐写模式
                if self.text_container.winfo_manager() == "pack":
                    self.text_container.pack_forget()
                self.sb_container.place_forget()
                if not self._is_stealth_container_visible():
                    self.stealth_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=STEALTH_PAD_Y)
                    self.stealth_container.update_idletasks()
                    self._stealth_line_container.lift()

                content = self.text.get("1.0", "end-1c")
                cur = self.text.index("insert")
                self.stealth_text.delete("1.0", "end")
                self.stealth_text.insert("1.0", content)
                self.stealth_text.mark_set("insert", cur)

                # 调整窗口高度
                self.stealth_text.update_idletasks()
                ww = self.root.winfo_width()
                new_h = self._calc_stealth_window_height()
                self.root.geometry(f"{ww}x{new_h}")
                self.content_win.geometry(f"{ww}x{new_h}")
                self.content_win.update_idletasks()
                self._corner_dirty = True
                self._update_corners()

                self.root.after(10, lambda: (
                    self.stealth_text.focus_set(),
                    self._refresh_stealth_view(),
                    self._layout_handle()
                ))
            else:
                # 普通文本框模式
                if self._is_stealth_container_visible():
                    try:
                        content = self.stealth_text.get("1.0", "end-1c")
                        cur = self.stealth_text.index("insert")
                        if content != self.text.get("1.0", "end-1c"):
                            self.text.delete("1.0", "end")
                            self.text.insert("1.0", content)
                        self.text.mark_set("insert", cur)
                    except Exception:
                        pass
                    self.stealth_container.pack_forget()
                    self._stealth_line_container.place_forget()
                if self.text_container.winfo_manager() != "pack":
                    self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)
                if self.cfg['show_scrollbar']:
                    self._set_scrollbar_visible(self._sb_visible)
                self.text.focus_set()
            self._apply_text_appearance()
            self._update_panel_button_states()
        except Exception as e:
            print(f"[隐写状态] 应用失败: {e}")

    # -------------------------------------------------------------------------
    # 文件操作
    # -------------------------------------------------------------------------

    def file_open(self):
        if self._check_save_before_close():
            return
        filetypes = [
            ("文本文件", "*.txt"),
            ("配置文件", "*.ini"),
            ("JSON文件", "*.json"),
            ("Markdown文件", "*.md"),
            ("所有文件", "*.*"),
        ]
        path = filedialog.askopenfilename(title="打开文件", filetypes=filetypes)
        if not path:
            return
        try:
            content, encoding = read_text_file(path, self.cfg['encoding'])
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.text.edit_reset()
            self.current_file = path
            self.current_encoding = encoding
            self._modified = False
            self._update_title()
            self._add_recent(path)
            self._save_config_debounced()
        except Exception as e:
            messagebox.showerror("打开失败", str(e))

    def file_save(self):
        if not self.current_file:
            return self.file_save_as()
        try:
            content = self.text.get("1.0", "end-1c")
            write_text_file(self.current_file, content, self.current_encoding)
            self._modified = False
            self._update_title()
            return True
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return False

    def file_save_as(self):
        filetypes = [
            ("文本文件", "*.txt"),
            ("配置文件", "*.ini"),
            ("JSON文件", "*.json"),
            ("Markdown文件", "*.md"),
            ("所有文件", "*.*"),
        ]
        path = filedialog.asksaveasfilename(
            title="另存为", filetypes=filetypes, defaultextension=".txt")
        if not path:
            return False
        try:
            content = self.text.get("1.0", "end-1c")
            write_text_file(path, content, 'utf-8')
            self.current_file = path
            self.current_encoding = 'utf-8'
            self._modified = False
            self._update_title()
            self._add_recent(path)
            self._save_config_debounced()
            return True
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return False

    def file_close(self):
        if self._check_save_before_close():
            return
        self.text.delete("1.0", "end")
        self.current_file = None
        self.current_encoding = 'utf-8'
        self._modified = False
        self._update_title()

    def _check_save_before_close(self):
        if not self._modified:
            return False
        if not self.current_file and not self.text.get("1.0", "end-1c").strip():
            return False
        result = messagebox.askyesnocancel("保存更改", "文件已修改，是否保存？")
        if result is None:
            return True
        elif result:
            return not self.file_save()
        else:
            return False

    def _add_recent(self, path):
        if path in self.cfg['recent_files']:
            self.cfg['recent_files'].remove(path)
        self.cfg['recent_files'].insert(0, path)
        if len(self.cfg['recent_files']) > 10:
            self.cfg['recent_files'] = self.cfg['recent_files'][:10]

    # -------------------------------------------------------------------------
    # 快捷键
    # -------------------------------------------------------------------------

    def _init_shortcuts(self):
        binds = [
            ("<Control-o>",      lambda e: self.file_open()),
            ("<Control-O>",      lambda e: self.file_open()),
            ("<Control-s>",      lambda e: (self.file_save(), "break")[1]),
            ("<Control-S>",      lambda e: (self.file_save(), "break")[1]),
            ("<Control-a>",      lambda e: (self.text_select_all(), "break")[1]),
            ("<Control-A>",      lambda e: (self.text_select_all(), "break")[1]),
            ("<Control-Shift-s>", lambda e: self.file_save_as()),
            ("<Control-Shift-S>", lambda e: self.file_save_as()),
            ("<Control-f>",      lambda e: (self.toggle_invert(), "break")[1]),
            ("<Control-F>",      lambda e: (self.toggle_invert(), "break")[1]),
            ("<Control-Shift-r>", lambda e: (self.toggle_read(), "break")[1]),
            ("<Control-Shift-R>", lambda e: (self.toggle_read(), "break")[1]),
            ("<Control-t>",      lambda e: (self.toggle_topmost(), "break")[1]),
            ("<Control-T>",      lambda e: (self.toggle_topmost(), "break")[1]),
            ("<Control-k>",      lambda e: (self.show_settings(), "break")[1]),
            ("<Control-K>",      lambda e: (self.show_settings(), "break")[1]),
            ("<Control-m>",      lambda e: (self.toggle_theme(), "break")[1]),
            ("<Control-M>",      lambda e: (self.toggle_theme(), "break")[1]),
        ]
        for seq, func in binds:
            self.root.bind(seq, func)
            self.text.bind(seq, func)

        self.text.bind("<FocusIn>", lambda e: self._on_focus_change())
        self.text.bind("<FocusOut>", lambda e: self._update_handle())

    # -------------------------------------------------------------------------
    # 显示/隐藏窗口
    # -------------------------------------------------------------------------

    def _show_window(self):
        """显示所有窗口并带到前台"""
        self.root.deiconify()
        self.content_win.deiconify()
        self.handle_win.deiconify()
        if self.cfg['show_panel']:
            self.panel.deiconify()
        self._window_visible = True
        self._sync_content_window()

        self._force_foreground()
        if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
            self.stealth_text.focus_set()
        else:
            self.text.focus_set()
        self._sync_taskbar_host()

    def _hide_window(self):
        """隐藏所有窗口"""
        self.root.withdraw()
        self.content_win.withdraw()
        self.handle_win.withdraw()
        if self.cfg['show_panel']:
            self.panel.withdraw()
        self._window_visible = False
        self._sync_taskbar_host()

    # -------------------------------------------------------------------------
    # 设置窗口
    # -------------------------------------------------------------------------

    def show_settings(self):
        if (hasattr(self, '_settings_win') and self._settings_win
                and self._settings_win.winfo_exists()):
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        self._settings_win = tk.Toplevel(self.root)
        self._settings_win.title("设置 - Stealth Note")
        self._settings_win.geometry("680x820")
        self._settings_win.resizable(True, True)
        self._settings_win.minsize(600, 700)

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self._settings_win.iconbitmap(self.icon_path)
            except Exception:
                pass

        main = ttk.Frame(self._settings_win, padding=12)
        main.pack(fill="both", expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True)

        self._preview_cfg = copy.deepcopy(self.cfg)

        self._build_tab_system(nb)
        self._build_tab_textbox(nb)
        self._build_tab_panel(nb)
        self._build_tab_about(nb)

        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=10)
        ttk.Button(btns, text="取消", command=self._settings_win.destroy).pack(side="right")
        ttk.Button(btns, text="应用", command=self._apply_settings).pack(side="right", padx=4)
        ttk.Button(btns, text="确定", command=self._ok_settings).pack(side="right", padx=4)

        self._settings_win.transient(self.root)
        self._settings_win.lift()
        self._settings_win.focus_force()

    def _color_button(self, parent, var, on_change=None):
        btn = tk.Button(parent, width=6, height=1, bg=var.get(),
                        fg="#ffffff", bd=1, relief="solid", cursor="hand2",
                        command=lambda: self._pick_color_for(var, btn, on_change))
        return btn

    def _pick_color_for(self, var, btn, on_change):
        color = colorchooser.askcolor(title="选择颜色", initialcolor=var.get())[1]
        if color:
            var.set(color)
            btn.configure(bg=color)
            if on_change:
                on_change()

    def _make_scale_clickable(self, scale, var, from_, to, resolution, on_change=None):
        """完全接管Scale鼠标行为：点击轨道精确定位+平滑拖动"""
        scale.bindtags((str(scale),))
        slider_len = scale.cget("sliderlength")
        try:
            slider_len = int(slider_len)
        except Exception:
            slider_len = 14
        pad = slider_len // 2

        def set_from_event(event):
            try:
                w = scale.winfo_width()
                if w <= pad * 2 + 2:
                    return
                x = max(pad, min(w - pad, event.x))
                rel = (x - pad) / (w - pad * 2)
                val = from_ + rel * (to - from_)
                if resolution and resolution > 0:
                    val = round(val / resolution) * resolution
                val = max(from_, min(to, val))
                if var.get() != val:
                    var.set(val)
                    if on_change:
                        on_change()
            except Exception as e:
                print(f"[滑块] 事件处理失败: {e}")

        scale.bind("<Button-1>", set_from_event)
        scale.bind("<B1-Motion>", set_from_event)
        scale.bind("<ButtonRelease-1>", lambda e: None)
        return scale

    def _opacity_scale(self, parent, var, from_=0.0, to=1.0, on_change=None):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)

        tk.Label(frame, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 4))

        scale = tk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal",
                         command=lambda v, vv=var, oc=on_change: self._on_scale_change(vv, oc),
                         troughcolor="#444444", sliderlength=14, width=8,
                         resolution=0.01, showvalue=False, bigincrement=0.1)
        scale.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale, var, from_, to, 0.01, on_change)

        tk.Label(frame, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(4, 4))

        pct_label = tk.Label(frame, text=f"{int(var.get()*100)}%", width=5, anchor="w")
        pct_label.pack(side="left")

        def update_pct(*args):
            pct_label.config(text=f"{int(var.get()*100)}%")
        var.trace_add("write", update_pct)

        return frame

    def _on_scale_change(self, var, on_change):
        if on_change:
            on_change()

    def _spin_scale(self, parent, var, from_, to, on_change=None):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)

        spin = ttk.Spinbox(frame, from_=from_, to=to, textvariable=var, width=6)
        spin.pack(side="left", padx=(0, 8))

        scale = tk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal",
                         command=lambda v, vv=var, oc=on_change: self._on_scale_change(vv, oc),
                         troughcolor="#444444", sliderlength=14, width=8,
                         resolution=1, showvalue=False, bigincrement=5)
        scale.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale, var, from_, to, 1, on_change)

        return frame

    def _refresh_preview(self):
        """实时预览设置效果（30ms 防抖，避免滑块拖动时闪烁）"""
        if hasattr(self, '_preview_after_id') and self._preview_after_id:
            self.root.after_cancel(self._preview_after_id)
        self._preview_after_id = self.root.after(30, self._do_refresh_preview)

    def _do_refresh_preview(self):
        """实际执行预览刷新"""
        self._preview_after_id = None
        old_cfg = self.cfg
        self.cfg = self._preview_cfg
        try:
            self._apply_window_style()
            self._apply_text_appearance()
            self._apply_stealth_state()
            self._corner_dirty = True
            self._update_corners()
            self._update_handle()
            self._update_panel_button_states()

            self.panel_inner.configure(bg=self._preview_cfg['panel_bg_color'])
            if not self._panel_hwnd:
                self._panel_hwnd = self.panel.winfo_id()
            alpha = int(max(MIN_PANEL_OPACITY, self._preview_cfg['panel_opacity']) * 255)
            set_layered_transparent(self._panel_hwnd, alpha, use_colorkey=True, show_taskbar=False)

            if not self._handle_hwnd:
                self._handle_hwnd = self.handle_win.winfo_id()
            set_layered_transparent(
                self._handle_hwnd, 255,
                use_colorkey=False, show_taskbar=False)

            self.root.attributes("-topmost", self._preview_cfg['topmost'])

            if self._preview_cfg['show_scrollbar']:
                self.text.see("1.0")
            else:
                self._set_scrollbar_visible(False)

            if self._preview_cfg['show_panel']:
                self.panel.deiconify()
            else:
                self.panel.withdraw()

            self._set_taskbar_visible(self._preview_cfg['show_taskbar'])

            self._layout_handle()
        except Exception as e:
            print(f"[预览] 刷新失败: {e}")
        finally:
            self.cfg = old_cfg
            try:
                self._apply_stealth_state()
            except Exception:
                pass
            # 恢复 cfg 后必须刷新一次仪表盘小红点，避免取消/预览后状态残留
            try:
                self._update_panel_button_states()
            except Exception:
                pass

    def _build_tab_system(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="系统设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="显示设置", padding=8)
        gf1.pack(fill="x", pady=6)

        v_invert = tk.BooleanVar(value=cfg['invert_mode'])
        v_read = tk.BooleanVar(value=cfg['read_mode'])
        v_top = tk.BooleanVar(value=cfg['topmost'])
        v_theme = tk.StringVar(value=cfg.get('theme_mode', 'dark'))

        def update_display():
            cfg['invert_mode'] = v_invert.get()
            cfg['read_mode'] = v_read.get()
            cfg['topmost'] = v_top.get()
            new_theme = v_theme.get()
            if new_theme != cfg.get('theme_mode', 'dark'):
                palette = THEME_PALETTES.get(new_theme, THEME_PALETTES['dark'])
                for key, value in palette.items():
                    cfg[key] = value
                cfg['theme_mode'] = new_theme
            self._refresh_preview()

        ttk.Checkbutton(gf1, text="反色显示", variable=v_invert, command=update_display).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="易读模式", variable=v_read, command=update_display).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="置顶模式", variable=v_top, command=update_display).pack(anchor="w", pady=2)

        theme_frame = tk.Frame(gf1)
        theme_frame.pack(anchor="w", pady=2)
        ttk.Label(theme_frame, text="主题模式：").pack(side="left")
        for mode, label in [("dark", "深色"), ("light", "浅色")]:
            ttk.Radiobutton(theme_frame, text=label, variable=v_theme, value=mode,
                            command=update_display).pack(side="left", padx=(4, 0))

        gf2 = ttk.LabelFrame(f, text="运行设置", padding=8)
        gf2.pack(fill="x", pady=6)

        v_taskbar = tk.BooleanVar(value=cfg['show_taskbar'])
        v_show_panel = tk.BooleanVar(value=cfg['show_panel'])

        def update_runtime():
            cfg['show_taskbar'] = v_taskbar.get()
            cfg['show_panel'] = v_show_panel.get()
            self._refresh_preview()

        ttk.Checkbutton(gf2, text="显示任务栏窗口", variable=v_taskbar, command=update_runtime).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf2, text="显示仪表盘", variable=v_show_panel, command=update_runtime).pack(anchor="w", pady=2)

        gf3 = ttk.LabelFrame(f, text="配置文件", padding=8)
        gf3.pack(fill="x", pady=6)

        btns = tk.Frame(gf3)
        btns.pack(fill="x")
        ttk.Button(btns, text="保存设置为文件...", command=self._export_config).pack(side="left", padx=2)
        ttk.Button(btns, text="读取设置文件...", command=self._import_config).pack(side="left", padx=2)

    def _export_config(self):
        path = filedialog.asksaveasfilename(
            title="保存配置", defaultextension=".ini",
            filetypes=[("配置文件", "*.ini"), ("JSON文件", "*.json")])
        if not path:
            return
        try:
            if path.lower().endswith('.json'):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self._preview_cfg, f, indent=2, ensure_ascii=False)
            else:
                cp = configparser.ConfigParser()
                cp.add_section('General')
                for k, v in self._preview_cfg.items():
                    cp.set('General', k, str(v))
                with open(path, 'w', encoding='utf-8') as f:
                    cp.write(f)
            messagebox.showinfo("成功", "配置已保存！")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def _import_config(self):
        path = filedialog.askopenfilename(
            title="读取配置",
            filetypes=[("配置文件", "*.ini;*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            if path.lower().endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                cp = configparser.ConfigParser()
                cp.read(path, encoding='utf-8')
                data = {}
                for sec in cp.sections():
                    for k, v in cp.items(sec):
                        data[k] = v

            for k, v in data.items():
                if k in DEFAULT_CONFIG:
                    def_val = DEFAULT_CONFIG[k]
                    if isinstance(def_val, bool):
                        data[k] = str(v).lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(def_val, (int, float)):
                        try:
                            data[k] = type(def_val)(v)
                        except (ValueError, TypeError):
                            pass

            for k in DEFAULT_CONFIG:
                if k not in data:
                    data[k] = DEFAULT_CONFIG[k]

            self._preview_cfg = validate_config(data)
            self._refresh_preview()
            messagebox.showinfo("成功", "配置已导入！")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def _build_tab_textbox(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="文本框设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="控件设置", padding=8)
        gf1.pack(fill="x", pady=6)

        v_show_titlebar = tk.BooleanVar(value=cfg.get('show_titlebar', False))
        v_show_statusbar = tk.BooleanVar(value=cfg.get('show_statusbar', False))
        v_show_sb = tk.BooleanVar(value=cfg['show_scrollbar'])

        ttk.Checkbutton(gf1, text="显示标题栏（待开发）", variable=v_show_titlebar, state="disabled").pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="显示状态栏（待开发）", variable=v_show_statusbar, state="disabled").pack(anchor="w", pady=2)

        def update_scrollbar():
            cfg['show_scrollbar'] = v_show_sb.get()
            self._refresh_preview()

        ttk.Checkbutton(gf1, text="启用滚动条", variable=v_show_sb, command=update_scrollbar).pack(anchor="w", pady=2)

        # 隐写模式设置
        v_stealth = tk.BooleanVar(value=cfg.get('stealth_mode', False))
        v_stealth_lines = tk.IntVar(value=cfg.get('stealth_lines', 3))

        def update_stealth():
            cfg['stealth_mode'] = v_stealth.get()
            cfg['stealth_lines'] = v_stealth_lines.get()
            self._refresh_preview()

        ttk.Separator(gf1, orient="horizontal").pack(fill="x", pady=8)
        ttk.Checkbutton(gf1, text="启用隐写模式", variable=v_stealth,
                        command=update_stealth).pack(anchor="w", pady=2)
        lines_frame = tk.Frame(gf1)
        lines_frame.pack(anchor="w", pady=2)
        ttk.Label(lines_frame, text="隐写行数：").pack(side="left", padx=(0, 6))
        for lines, label in [(1, "一行"), (2, "两行"), (3, "三行")]:
            ttk.Radiobutton(lines_frame, text=label, variable=v_stealth_lines,
                            value=lines, command=update_stealth).pack(side="left", padx=(0, 8))

        gf2 = ttk.LabelFrame(f, text="文本框外观", padding=8)
        gf2.pack(fill="x", pady=6)

        v_bg_color = tk.StringVar(value=cfg['bg_color'])
        v_bg_opacity = tk.DoubleVar(value=cfg['bg_opacity'])
        v_text_color = tk.StringVar(value=cfg['text_color'])
        v_text_opacity = tk.DoubleVar(value=cfg['text_opacity'])
        v_read_bg_color = tk.StringVar(value=cfg['read_bg_color'])
        v_read_bg_opacity = tk.DoubleVar(value=cfg['read_bg_opacity'])
        v_corner_color = tk.StringVar(value=cfg['corner_color'])
        v_corner_opacity = tk.DoubleVar(value=cfg['corner_opacity'])

        def update_appearance():
            cfg['bg_color'] = v_bg_color.get()
            cfg['bg_opacity'] = round(clamp(v_bg_opacity.get(), 0.0, 1.0), 2)
            cfg['text_color'] = v_text_color.get()
            cfg['text_opacity'] = round(clamp(v_text_opacity.get(), MIN_TEXT_OPACITY, 1.0), 2)
            cfg['read_bg_color'] = v_read_bg_color.get()
            cfg['read_bg_opacity'] = round(clamp(v_read_bg_opacity.get(), MIN_READ_BG_OPACITY, 1.0), 2)
            cfg['corner_color'] = v_corner_color.get()
            cfg['corner_opacity'] = round(clamp(v_corner_opacity.get(), MIN_CORNER_OPACITY, 1.0), 2)
            self._refresh_preview()

        def _color_opacity_row(parent, label_text, color_var, opacity_var, min_op, on_change):
            row = tk.Frame(parent)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label_text, width=10, anchor="e").pack(side="left", padx=(0, 6))
            self._color_button(row, color_var, on_change=on_change).pack(side="left", padx=(0, 8))
            tk.Label(row, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
            scale = tk.Scale(row, from_=min_op, to=1.0, variable=opacity_var, orient="horizontal",
                             command=lambda v: on_change(),
                             troughcolor="#444444", sliderlength=14, width=8,
                             resolution=0.01, showvalue=False, bigincrement=0.1)
            scale.pack(side="left", fill="x", expand=True)
            self._make_scale_clickable(scale, opacity_var, min_op, 1.0, 0.01, on_change)
            tk.Label(row, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
            pct = tk.Label(row, text=f"{int(opacity_var.get()*100)}%", width=5, anchor="w")
            pct.pack(side="left")
            opacity_var.trace_add("write", lambda *a: pct.config(text=f"{int(opacity_var.get()*100)}%"))

        _color_opacity_row(gf2, "文本背景：", v_bg_color, v_bg_opacity, 0.0, update_appearance)
        _color_opacity_row(gf2, "文字外观：", v_text_color, v_text_opacity, MIN_TEXT_OPACITY, update_appearance)
        _color_opacity_row(gf2, "易读模式：", v_read_bg_color, v_read_bg_opacity, MIN_READ_BG_OPACITY, update_appearance)
        _color_opacity_row(gf2, "框线颜色：", v_corner_color, v_corner_opacity, MIN_CORNER_OPACITY, update_appearance)

        ttk.Separator(gf2, orient="horizontal").pack(fill="x", pady=8)

        v_corner_lw = tk.IntVar(value=cfg['corner_line_width'])
        v_corner_sz = tk.IntVar(value=cfg['corner_size'])

        def update_corner_dims():
            cfg['corner_line_width'] = max(MIN_CORNER_LINE, v_corner_lw.get())
            cfg['corner_size'] = clamp(v_corner_sz.get(), MIN_CORNER_LEN, MAX_CORNER_LEN)
            self._refresh_preview()

        row_corner = tk.Frame(gf2)
        row_corner.pack(fill="x", pady=3)
        ttk.Label(row_corner, text="四角框线：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Label(row_corner, text="线宽").pack(side="left", padx=(0, 2))
        ttk.Spinbox(row_corner, from_=MIN_CORNER_LINE, to=MAX_CORNER_LINE, textvariable=v_corner_lw,
                    width=4, command=update_corner_dims).pack(side="left", padx=(0, 8))
        ttk.Label(row_corner, text="边长").pack(side="left", padx=(0, 2))
        ttk.Spinbox(row_corner, from_=MIN_CORNER_LEN, to=MAX_CORNER_LEN, textvariable=v_corner_sz,
                    width=4, command=update_corner_dims).pack(side="left", padx=(0, 8))
        scale_corner = tk.Scale(row_corner, from_=MIN_CORNER_LEN, to=MAX_CORNER_LEN, variable=v_corner_sz, orient="horizontal",
                                command=lambda v: update_corner_dims(),
                                troughcolor="#444444", sliderlength=14, width=8,
                                resolution=1, showvalue=False, bigincrement=5)
        scale_corner.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_corner, v_corner_sz, MIN_CORNER_LEN, MAX_CORNER_LEN, 1, update_corner_dims)

        gf3 = ttk.LabelFrame(f, text="文字样式", padding=8)
        gf3.pack(fill="x", pady=6)

        v_encoding = tk.StringVar(value=cfg['encoding'])
        v_font = tk.StringVar(value=cfg['text_font'])
        v_size = tk.IntVar(value=cfg['text_size'])

        def update_text_style():
            cfg['encoding'] = v_encoding.get()
            cfg['text_font'] = v_font.get()
            cfg['text_size'] = v_size.get()
            self._refresh_preview()

        row_enc = tk.Frame(gf3)
        row_enc.pack(fill="x", pady=3)
        ttk.Label(row_enc, text="文本编码：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Combobox(row_enc, textvariable=v_encoding, state="readonly", width=12,
                     values=["auto", "utf-8", "utf-8-sig", "gbk", "gb2312", "utf-16", "latin-1"]).pack(side="left")

        row_font = tk.Frame(gf3)
        row_font.pack(fill="x", pady=3)
        ttk.Label(row_font, text="字体：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        font_combo = ttk.Combobox(row_font, textvariable=v_font, state="readonly", width=24,
                                  values=["Microsoft YaHei UI", "SimSun", "SimHei", "KaiTi", "Arial", "Courier New", "Times New Roman"])
        font_combo.pack(side="left")
        font_combo.bind("<<ComboboxSelected>>", lambda e: update_text_style())

        row_size = tk.Frame(gf3)
        row_size.pack(fill="x", pady=3)
        ttk.Label(row_size, text="字号：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Spinbox(row_size, from_=MIN_FONT_SIZE, to=MAX_FONT_SIZE, textvariable=v_size,
                    width=4, command=update_text_style).pack(side="left", padx=(0, 8))
        scale_size = tk.Scale(row_size, from_=MIN_FONT_SIZE, to=MAX_FONT_SIZE, variable=v_size, orient="horizontal",
                              command=lambda v: update_text_style(),
                              troughcolor="#444444", sliderlength=14, width=8,
                              resolution=1, showvalue=False, bigincrement=2)
        scale_size.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_size, v_size, MIN_FONT_SIZE, MAX_FONT_SIZE, 1, update_text_style)

        gf4 = ttk.LabelFrame(f, text="控制手柄", padding=8)
        gf4.pack(fill="x", pady=6)

        v_handle_size = tk.IntVar(value=cfg['handle_size'])
        v_handle_opacity = tk.DoubleVar(value=cfg.get('handle_opacity', 0.8))

        def update_handle():
            cfg['handle_size'] = clamp(v_handle_size.get(), MIN_HANDLE_SIZE, MAX_HANDLE_SIZE)
            cfg['handle_opacity'] = round(clamp(v_handle_opacity.get(), 0.1, 1.0), 2)
            self._refresh_preview()

        row_handle = tk.Frame(gf4)
        row_handle.pack(fill="x", pady=3)
        ttk.Label(row_handle, text="手柄尺寸：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Spinbox(row_handle, from_=MIN_HANDLE_SIZE, to=MAX_HANDLE_SIZE, textvariable=v_handle_size,
                    width=4, command=update_handle).pack(side="left", padx=(0, 8))
        scale_handle = tk.Scale(row_handle, from_=MIN_HANDLE_SIZE, to=MAX_HANDLE_SIZE, variable=v_handle_size, orient="horizontal",
                                command=lambda v: update_handle(),
                                troughcolor="#444444", sliderlength=14, width=8,
                                resolution=1, showvalue=False, bigincrement=2)
        scale_handle.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_handle, v_handle_size, MIN_HANDLE_SIZE, MAX_HANDLE_SIZE, 1, update_handle)

        row_ho = tk.Frame(gf4)
        row_ho.pack(fill="x", pady=3)
        ttk.Label(row_ho, text="手柄透明：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        tk.Label(row_ho, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
        scale_ho = tk.Scale(row_ho, from_=0.1, to=1.0, variable=v_handle_opacity, orient="horizontal",
                            command=lambda v: update_handle(),
                            troughcolor="#444444", sliderlength=14, width=8,
                            resolution=0.01, showvalue=False, bigincrement=0.1)
        scale_ho.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_ho, v_handle_opacity, 0.1, 1.0, 0.01, update_handle)
        tk.Label(row_ho, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
        pct_ho = tk.Label(row_ho, text=f"{int(v_handle_opacity.get()*100)}%", width=5, anchor="w")
        pct_ho.pack(side="left")
        v_handle_opacity.trace_add("write", lambda *a: pct_ho.config(text=f"{int(v_handle_opacity.get()*100)}%"))

        ttk.Label(gf4, text="手柄样式（待开发）", foreground="#999999").pack(anchor="w", pady=(8, 2))

    def _build_tab_panel(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="仪表盘设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="仪表盘外观", padding=8)
        gf1.pack(fill="x", pady=6)

        v_panel_bg = tk.StringVar(value=cfg['panel_bg_color'])
        v_panel_opacity = tk.DoubleVar(value=cfg['panel_opacity'])

        def update_panel():
            cfg['panel_bg_color'] = v_panel_bg.get()
            cfg['panel_opacity'] = round(clamp(v_panel_opacity.get(), MIN_PANEL_OPACITY, 1.0), 2)
            self._refresh_preview()

        row1 = tk.Frame(gf1)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="颜色：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        self._color_button(row1, v_panel_bg, on_change=update_panel).pack(side="left", padx=(0, 8))
        tk.Label(row1, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
        scale_panel = tk.Scale(row1, from_=MIN_PANEL_OPACITY, to=1.0, variable=v_panel_opacity, orient="horizontal",
                               command=lambda v: update_panel(),
                               troughcolor="#444444", sliderlength=14, width=8,
                               resolution=0.01, showvalue=False, bigincrement=0.1)
        scale_panel.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_panel, v_panel_opacity, MIN_PANEL_OPACITY, 1.0, 0.01, update_panel)
        tk.Label(row1, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
        pct = tk.Label(row1, text=f"{int(v_panel_opacity.get()*100)}%", width=5, anchor="w")
        pct.pack(side="left")
        v_panel_opacity.trace_add("write", lambda *a: pct.config(text=f"{int(v_panel_opacity.get()*100)}%"))

        gf2 = ttk.LabelFrame(f, text="按钮说明", padding=8)
        gf2.pack(fill="both", expand=True, pady=6)

        btn_info = [
            ("O",  "打开文件",   "Ctrl+O",       "#333333"),
            ("S",  "保存文件",   "Ctrl+S",       "#333333"),
            ("隐", "隐写模式",   "中键切换",     "#333333"),
            ("SN", "另存为",     "Ctrl+Shift+S", "#333333"),
            ("反", "反色显示",   "Ctrl+F",       "#3d3d3d"),
            ("易", "易读模式",   "Ctrl+Shift+R", "#3d3d3d"),
            ("顶", "置顶模式",   "Ctrl+T",       "#3d3d3d"),
            ("色", "主题切换",   "Ctrl+M",       "#3d3d3d"),
            ("控", "设置仪表盘", "Ctrl+K",       "#3d3d3d"),
            ("X",  "退出程序",   "—",            "#2a2a2a"),
            ("⋮⋮", "拖动仪表盘", "",             "#ff8800"),
        ]

        for symbol, name, shortcut, bg_color in btn_info:
            row = tk.Frame(gf2)
            row.pack(fill="x", pady=2)
            preview = tk.Label(row, text=symbol, bg=bg_color, fg="#ffffff", width=4,
                               font=("Microsoft YaHei UI", 9, "bold"), relief="flat")
            preview.pack(side="left", padx=(0, 8))
            ttk.Label(row, text=name, width=12, anchor="w").pack(side="left", padx=(0, 8))
            ttk.Label(row, text=shortcut, foreground="#888888").pack(side="left")

    def _build_tab_about(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="关于软件")

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(self.icon_path)
                img = img.resize((64, 64), Image.LANCZOS)
                self._about_icon = ImageTk.PhotoImage(img)
                tk.Label(f, image=self._about_icon).pack(pady=(12, 4))
            except Exception:
                ttk.Label(f, text="[S]", font=("Microsoft YaHei UI", 24)).pack(pady=(12, 4))
        else:
            ttk.Label(f, text="[S]", font=("Microsoft YaHei UI", 24, "bold")).pack(pady=(12, 4))

        ttk.Label(f, text=f"{APP_NAME} {VERSION}", font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(4, 4))
        ttk.Label(f, text=f"作者：{AUTHOR}").pack(pady=2)
        ttk.Label(f, text=f"邮箱：{CONTACT_EMAIL}").pack(pady=2)
        ttk.Label(f, text="\n完全透明的记事本工具").pack(pady=(8, 4))
        ttk.Label(f, text="支持多种透明度设置、反色显示、易读模式等功能").pack(pady=2)

    def _apply_settings(self):
        self.cfg = copy.deepcopy(self._preview_cfg)
        self._apply_window_style()
        self._apply_text_appearance()
        self._apply_stealth_state()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._set_taskbar_visible(self.cfg['show_taskbar'])
        self._save_config_debounced()

    def _ok_settings(self):
        self._apply_settings()
        self._settings_win.destroy()

    # -------------------------------------------------------------------------
    # 系统托盘
    # -------------------------------------------------------------------------

    def _init_tray(self):
        """初始化系统托盘（在独立线程中运行）"""
        try:
            import pystray
            from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem as TrayItem
            print("[托盘] pystray导入成功")
        except Exception as e:
            print(f"[托盘] pystray导入失败: {e}")
            self.tray_icon = None
            return

        try:
            def on_tray_clicked(icon, item):
                action = str(item)
                if action == "显示/隐藏":
                    self.root.after(0, self._tray_toggle)
                elif action == "打开文件":
                    self.root.after(0, self.file_open)
                elif action == "保存文件":
                    self.root.after(0, self.file_save)
                elif action == "设置":
                    self.root.after(0, self.show_settings)
                elif action == "退出":
                    self.root.after(0, self.exit_app)

            menu = TrayMenu(
                TrayItem("显示/隐藏", on_tray_clicked, default=True),
                TrayItem("打开文件", on_tray_clicked),
                TrayItem("保存文件", on_tray_clicked),
                TrayItem("设置", on_tray_clicked),
                TrayItem("退出", on_tray_clicked)
            )

            icon_image = self._load_tray_icon()

            self.tray_icon = TrayIcon(APP_NAME, icon_image, APP_NAME, menu)
            print("[托盘] TrayIcon创建成功")

            def _tray_run():
                try:
                    print("[托盘] 开始运行")
                    self.tray_icon.run()
                    print("[托盘] 运行结束")
                except Exception as e:
                    print(f"[托盘] 运行异常: {e}")
                    import traceback
                    traceback.print_exc()

            tray_thread = threading.Thread(target=_tray_run, daemon=True)
            tray_thread.start()
            print("[托盘] 线程已启动")

        except Exception as e:
            print(f"[托盘] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.tray_icon = None

    def _load_tray_icon(self):
        """加载托盘图标，失败则生成默认图标"""
        try:
            from PIL import Image
            if self.icon_path and os.path.exists(self.icon_path):
                try:
                    img = Image.open(self.icon_path)
                    print(f"[托盘] 从文件加载图标: {self.icon_path}")
                    return img
                except Exception as e:
                    print(f"[托盘] 图标文件加载失败: {e}")

            size = 64
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            cx, cy = size // 2, size // 2
            r = size // 2 - 4
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=(45, 45, 45, 255),
                         outline=(255, 255, 255, 255), width=2)
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", 36)
            except Exception:
                font = ImageFont.load_default()
            draw.text((cx, cy), "S", fill=(255, 255, 255, 255), font=font, anchor="mm")
            print("[托盘] 使用生成的默认图标")
            return img
        except Exception as e:
            print(f"[托盘] 生成默认图标失败: {e}")
            return None

    def _tray_toggle(self):
        """托盘点击切换：显示在最前台 / 最小化隐藏"""
        if self._window_visible:
            self._hide_window()
        else:
            self._show_window()

    # -------------------------------------------------------------------------
    # 关于 / 退出
    # -------------------------------------------------------------------------

    def _show_about(self):
        messagebox.showinfo(f"{APP_NAME} {VERSION}",
                            f"{APP_NAME} {VERSION}\n\n作者：{AUTHOR}\n邮箱：{CONTACT_EMAIL}\n\n完全透明的记事本工具")

    def exit_app(self):
        if self._check_save_before_close():
            return
        try:
            if self._window_visible:
                self.cfg['window_width'] = self.root.winfo_width()
                self.cfg['window_height'] = self.root.winfo_height()
                self.cfg['window_x'] = self.root.winfo_x()
                self.cfg['window_y'] = self.root.winfo_y()
            self._do_save_config()
        except Exception:
            pass
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def _on_close(self):
        if self.cfg['show_taskbar']:
            self.exit_app()
        else:
            self._tray_toggle()


if __name__ == "__main__":
    app = StealthNoteApp()
    app.root.mainloop()

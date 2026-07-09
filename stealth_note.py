# -*- coding: utf-8 -*-
# =============================================================================
# Stealth Note v1.4.0
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
import threading

# =============================================================================
# 常量定义
# =============================================================================

APP_NAME = "Stealth Note"
VERSION = "v1.4.0"
AUTHOR = "Magicxh & TRAE"
CONTACT_EMAIL = "17296509@qq.com"

# Windows API 常量
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

# 消息常量
WM_ACTIVATE = 0x0006
WM_ACTIVATEAPP = 0x001C
WM_SHOWWINDOW = 0x0018
SW_RESTORE = 9

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 透明色键 - 品红色，用于移除根窗口背景
COLORKEY = "#FF00FF"
COLORKEY_INT = 0x00FF00FF  # BGR格式

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
MIN_HANDLE_SIZE = 16
MAX_HANDLE_SIZE = 64
MIN_WINDOW_W = 300
MIN_WINDOW_H = 200
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 48

# === UI 尺寸常量 ===
TEXT_PAD_X = 24
TEXT_PAD_Y = 20
SCROLLBAR_WIDTH = 3
SCROLLBAR_PAD_RIGHT = 4
CORNER_MARGIN = 4
HANDLE_WIN_PADDING = 12
PANEL_WIDTH = 380
PANEL_HEIGHT = 60
PANEL_BTN_W = 34
PANEL_BTN_H = 40

# === 配置防抖 ===
CONFIG_SAVE_DEBOUNCE_MS = 500

# 配置文件路径
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
    "opacity": 0.90,
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
    "corner_size": 40,
    "corner_line_width": 2,
    "corner_color": "#000000",
    "corner_opacity": 0.80,
    "handle_size": 28,
    "show_scrollbar": True,
    "show_panel": True,
    "panel_opacity": 0.85,
    "panel_bg_color": "#2c2c2c",
    "panel_x": None,
    "panel_y": None,
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
    _clamp("opacity", MIN_WINDOW_OPACITY, 1.0)
    _clamp("bg_opacity", 0.0, 1.0)
    _clamp("text_opacity", MIN_TEXT_OPACITY, 1.0)
    _clamp("text_size", MIN_FONT_SIZE, MAX_FONT_SIZE)
    _clamp("read_bg_opacity", MIN_READ_BG_OPACITY, 1.0)
    _clamp("corner_size", MIN_CORNER_LEN, MAX_CORNER_LEN)
    _clamp("corner_line_width", MIN_CORNER_LINE, MAX_CORNER_LINE)
    _clamp("corner_opacity", MIN_CORNER_OPACITY, 1.0)
    _clamp("handle_size", MIN_HANDLE_SIZE, MAX_HANDLE_SIZE)
    _clamp("panel_opacity", MIN_PANEL_OPACITY, 1.0)

    for k in ["topmost", "show_taskbar", "show_titlebar", "show_statusbar",
              "read_mode", "invert_mode", "show_scrollbar", "show_panel"]:
        if k in result and not isinstance(result[k], bool):
            result[k] = DEFAULT_CONFIG[k]

    for k in ["bg_color", "text_color", "read_bg_color", "corner_color", "panel_bg_color"]:
        if k in result:
            v = result[k]
            if not isinstance(v, str) or not v.startswith('#') or len(v) != 7:
                result[k] = DEFAULT_CONFIG[k]

    if "text_font" not in result or not isinstance(result["text_font"], str):
        result["text_font"] = DEFAULT_CONFIG["text_font"]

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


def set_layered_transparent(hwnd, alpha=255, colorkey=False, show_taskbar=True):
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
        if colorkey:
            flags |= LWA_COLORKEY

        user32.SetLayeredWindowAttributes(hwnd, COLORKEY_INT if colorkey else 0, int(alpha), flags)
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
        bbox = draw.textbbox((0, 0), "S", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2 - bbox[0], cy - th // 2 - bbox[1]),
                  "S", fill=(255, 255, 255, 255), font=font)
        img.save(ICON_FILE, format='ICO',
                 sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return ICON_FILE
    except Exception as e:
        print(f"[图标] 生成失败: {e}")
        return None


def check_single_instance():
    mutex_name = "StealthNote_SingleInstance_Mutex_v140"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.kernel32.CloseHandle(mutex)
        return None
    return mutex

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

        self._save_after_id = None

        self._root_hwnd = None
        self._handle_hwnd = None
        self._panel_hwnd = None

        self._corner_dirty = True
        self._window_visible = True

        self.icon_path = create_app_icon()

        self._create_root()

        self._init_bg_layer()
        self._init_text_editor()
        self._init_corners()
        self._init_handle()
        self._init_panel()
        self._init_tray()
        self._init_shortcuts()

        self._apply_window_opacity()
        self._apply_text_appearance()
        self.root.after(100, self._layout_all)

        if not os.path.exists(CONFIG_FILE):
            self._save_config_debounced()

        self.root.deiconify()
        self.root.lift()
        self.root.after(200, self._focus_text)

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

    # -------------------------------------------------------------------------
    # 窗口初始化
    # -------------------------------------------------------------------------

    def _create_root(self):
        self.root = tk.Tk()
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

        # 根窗口使用COLORKEY作为背景色，这样LWA_COLORKEY会把根窗口背景完全移除
        # 实际内容放在content_frame上，使用用户设置的背景色
        self.root.configure(bg=COLORKEY, bd=0, highlightthickness=0)

        self.root.update_idletasks()
        self._root_hwnd = self.root.winfo_id()

        # 同时使用LWA_COLORKEY和LWA_ALPHA
        # COLORKEY用于移除根窗口背景，ALPHA用于控制整体透明度
        alpha = int(self.cfg['opacity'] * 255)
        set_layered_transparent(self._root_hwnd, alpha, colorkey=True,
                                show_taskbar=self.cfg['show_taskbar'])

        if self.cfg['show_taskbar']:
            self.root.after(100, self._ensure_taskbar_icon)

        if self.cfg['topmost']:
            self.root.attributes("-topmost", True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 绑定任务栏点击激活事件
        self._setup_taskbar_activation()

    def _ensure_taskbar_icon(self):
        try:
            hwnd = self.root.winfo_id()
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_APPWINDOW
            ex_style &= ~WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
            self.root.deiconify()
            self.root.lift()
        except Exception as e:
            print(f"[任务栏] 设置失败: {e}")

    def _setup_taskbar_activation(self):
        """设置任务栏点击激活窗口"""
        try:
            self._old_window_proc = ctypes.CFUNCTYPE(
                ctypes.c_long, ctypes.c_long, ctypes.c_uint,
                ctypes.c_long, ctypes.c_long
            )(self._window_proc)

            user32.SetWindowLongW.restype = ctypes.c_long
            user32.SetWindowLongW.argtypes = [ctypes.c_long, ctypes.c_int, ctypes.c_long]

            user32.CallWindowProcW.restype = ctypes.c_long
            user32.CallWindowProcW.argtypes = [
                ctypes.c_long, ctypes.c_long, ctypes.c_uint,
                ctypes.c_long, ctypes.c_long
            ]

            user32.SetWindowLongW(self._root_hwnd, -4, ctypes.c_long(
                ctypes.addressof(self._old_window_proc)
            ))
        except Exception as e:
            print(f"[任务栏] 钩子设置失败: {e}")

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """自定义窗口消息处理"""
        if msg == WM_SHOWWINDOW and wparam == 1:
            self.root.after(0, self._on_taskbar_click)
        elif msg == WM_ACTIVATE and wparam == 1:
            self.root.after(0, self._on_window_activated)

        return user32.CallWindowProcW(
            self._old_window_proc, hwnd, msg, wparam, lparam
        )

    def _on_taskbar_click(self):
        """点击任务栏时激活窗口"""
        if not self._window_visible:
            self._show_window()
        else:
            self.root.lift()
            self.root.focus_force()
            self.text.focus_set()

    def _on_window_activated(self):
        """窗口被激活时"""
        self._lift_all()

    def _show_window(self):
        """显示窗口"""
        self.root.deiconify()
        self.root.lift()
        self.handle_win.deiconify()
        self.handle_win.lift()
        if self.cfg['show_panel']:
            self.panel.deiconify()
            self.panel.lift()
        self._window_visible = True
        self._on_focus_change()

    def _hide_window(self):
        """隐藏窗口"""
        self.root.withdraw()
        self.handle_win.withdraw()
        if self.cfg['show_panel']:
            self.panel.withdraw()
        self._window_visible = False

    # -------------------------------------------------------------------------
    # 背景层
    # -------------------------------------------------------------------------

    def _init_bg_layer(self):
        """初始化内容层，使用用户设置的背景色"""
        self.content_frame = tk.Frame(self.root, bg=self.cfg['bg_color'], bd=0, highlightthickness=0)
        self.content_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self._current_bg = self.cfg['bg_color']
        self._bg_color_pure = self.cfg['bg_color']

    def _update_bg_color(self):
        """更新背景色"""
        if self.cfg['read_mode']:
            bg = self.cfg['read_bg_color']
            bg_op = self.cfg['read_bg_opacity']
        else:
            bg = self.cfg['bg_color']
            bg_op = self.cfg['bg_opacity']

        if self.cfg['invert_mode']:
            bg = invert_color(bg)

        self._bg_color_pure = bg
        self._current_bg = bg

        # 直接设置内容层背景色
        self.content_frame.configure(bg=bg)

    # -------------------------------------------------------------------------
    # 文本编辑器 + 滚动条
    # -------------------------------------------------------------------------

    def _init_text_editor(self):
        bg = self._current_bg
        self.text_container = tk.Frame(self.content_frame, bg=bg, bd=0, highlightthickness=0)
        self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)

        self.text = tk.Text(
            self.text_container,
            bg=bg,
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            selectbackground="#666666",
            selectforeground="#FFFFFF",
            font=("Microsoft YaHei UI", 12),
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=6,
            pady=6,
            undo=True,
            maxundo=100,
        )
        self.text.pack(side="left", fill="both", expand=True)

        self.sb_container = tk.Frame(self.content_frame, bg=bg, bd=0, highlightthickness=0,
                                     width=SCROLLBAR_WIDTH + SCROLLBAR_PAD_RIGHT * 2)
        self.sb_container.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0, relheight=1.0)

        self._sb_canvas = tk.Canvas(self.sb_container, bg=bg, highlightthickness=0, bd=0,
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
        self._create_context_menu()

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
        self.text.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        try:
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

    def _update_title(self):
        if self.current_file:
            name = os.path.basename(self.current_file)
            mark = "*" if self._modified else ""
            self.root.title(f"{mark}{name} - {APP_NAME} [{self.current_encoding}]")
        else:
            mark = "*" if self._modified else ""
            self.root.title(f"{mark}未命名 - {APP_NAME}")

    def _focus_text(self):
        try:
            self.text.focus_set()
        except Exception:
            pass

    def text_select_all(self):
        try:
            self.text.tag_add("sel", "1.0", "end-1c")
            self.text.mark_set("insert", "end-1c")
            self.text.see("insert")
        except Exception:
            pass

    def _apply_text_appearance(self):
        self._update_bg_color()

        tc = self.cfg['text_color']
        if self.cfg['invert_mode']:
            tc = invert_color(tc)

        bg_for_mix = self._bg_color_pure if hasattr(self, '_bg_color_pure') else "#000000"
        fg_color = mix_color(tc, self.cfg['text_opacity'], bg_for_mix)

        text_bg = self._current_bg

        self.text.configure(
            bg=text_bg,
            fg=fg_color,
            insertbackground=fg_color,
            font=(self.cfg['text_font'], self.cfg['text_size'])
        )

        if self.cfg['read_mode']:
            self._apply_read_mode_bg()
        else:
            try:
                self.text.tag_remove("read_bg", "1.0", "end")
            except Exception:
                pass

        if self._sb_visible:
            self._redraw_scrollbar()

    def _apply_read_mode_bg(self):
        try:
            self.text.tag_remove("read_bg", "1.0", "end")
            bg = self.cfg['read_bg_color']
            if self.cfg['invert_mode']:
                bg = invert_color(bg)
            self.text.tag_configure("read_bg", background=bg)
            count = int(self.text.index("end-1c").split(".")[0])
            for i in range(1, count + 1):
                line_start = f"{i}.0"
                line_end = f"{i}.end"
                text = self.text.get(line_start, line_end)
                if text.strip():
                    self.text.tag_add("read_bg", line_start, line_end)
        except Exception:
            pass

    def _apply_window_opacity(self):
        if not self._root_hwnd:
            self._root_hwnd = self.root.winfo_id()
        alpha = int(max(MIN_WINDOW_OPACITY, self.cfg['opacity']) * 255)
        set_layered_transparent(self._root_hwnd, alpha, colorkey=True,
                                show_taskbar=self.cfg['show_taskbar'])

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
    # 角部边框
    # -------------------------------------------------------------------------

    def _init_corners(self):
        self._corner_frames = {}
        self._corner_canvases = {}

        corners = [
            ("nw", "top_left_corner"),
            ("ne", "top_right_corner"),
            ("sw", "bottom_left_corner"),
            ("se", "bottom_right_corner"),
        ]

        for name, cursor in corners:
            frame = tk.Frame(self.content_frame, bg=self.cfg['bg_color'], width=1, height=1)
            canvas = tk.Canvas(frame, bg=self.cfg['bg_color'], highlightthickness=0, bd=0, cursor=cursor)
            canvas.pack(fill="both", expand=True)
            canvas.bind("<ButtonPress-1>", lambda e, n=name: self._on_resize_start(e, n))
            canvas.bind("<B1-Motion>", self._on_resize)
            canvas.bind("<ButtonRelease-1>", self._on_resize_end)
            self._corner_frames[name] = frame
            self._corner_canvases[name] = canvas

    def _layout_all(self):
        self._update_bg_color()
        self._layout_corners()
        self._layout_handle()
        self._update_handle()
        self._update_panel_button_states()
        if self._sb_visible:
            self._redraw_scrollbar()

    def _layout_corners(self):
        cs = max(MIN_CORNER_LEN, int(self.cfg['corner_size']))
        lw = max(MIN_CORNER_LINE, int(self.cfg['corner_line_width']))

        positions = {
            "nw": (CORNER_MARGIN, CORNER_MARGIN, "nw"),
            "ne": (CORNER_MARGIN, CORNER_MARGIN, "ne"),
            "sw": (CORNER_MARGIN, CORNER_MARGIN, "sw"),
            "se": (CORNER_MARGIN, CORNER_MARGIN, "se"),
        }

        for name, (px, py, anchor) in positions.items():
            frame = self._corner_frames[name]
            frame.configure(width=cs, height=cs)
            relx = 1.0 if 'e' in name else 0.0
            rely = 1.0 if 's' in name else 0.0
            x_offset = px if 'w' in name else -px
            y_offset = py if 'n' in name else -py
            frame.place(relx=relx, rely=rely, anchor=anchor, x=x_offset, y=y_offset)
            self._corner_canvases[name].configure(width=cs, height=cs)
            self._corner_dirty = True

        if self._corner_dirty:
            self._draw_all_corners()
            self._corner_dirty = False

        for name in self._corner_frames:
            self._corner_frames[name].lift()

    def _draw_all_corners(self):
        for name in self._corner_canvases:
            self._draw_corner(name)

    def _draw_corner(self, name):
        canvas = self._corner_canvases.get(name)
        if not canvas:
            return
        canvas.delete("all")
        size = max(MIN_CORNER_LEN, int(self.cfg['corner_size']))
        lw = max(MIN_CORNER_LINE, int(self.cfg['corner_line_width']))

        color = self.cfg['corner_color']
        if self.cfg['invert_mode']:
            color = invert_color(color)
        color = mix_color(color, self.cfg['corner_opacity'], "#000000")

        half = lw / 2.0

        def L(x1, y1, x2, y2):
            canvas.create_line(x1, y1, x2, y2, fill=color, width=lw)

        if name == "nw":
            L(half, half, size - half, half)
            L(half, half, half, size - half)
        elif name == "ne":
            L(half, half, size - half, half)
            L(size - half, half, size - half, size - half)
        elif name == "sw":
            L(half, size - half, size - half, size - half)
            L(half, half, half, size - half)
        elif name == "se":
            L(half, size - half, size - half, size - half)
            L(size - half, half, size - half, size - half)

    def _update_corners(self):
        self._corner_dirty = True
        self._layout_corners()

    def _on_resize_start(self, event, edge):
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

        self.root.update_idletasks()
        self._update_bg_color()
        self.content_frame.update_idletasks()
        if self._sb_visible:
            self._redraw_scrollbar()

    def _on_resize_end(self, event):
        if self._resize_edge:
            self.cfg['window_width'] = self.root.winfo_width()
            self.cfg['window_height'] = self.root.winfo_height()
            self.cfg['window_x'] = self.root.winfo_x()
            self.cfg['window_y'] = self.root.winfo_y()
            self._save_config_debounced()
            self._resize_edge = None
            self._layout_handle()

    # -------------------------------------------------------------------------
    # 圆形手柄
    # -------------------------------------------------------------------------

    def _init_handle(self):
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        self.handle_win = tk.Toplevel(self.root)
        self.handle_win.withdraw()
        self.handle_win.overrideredirect(True)

        # 手柄窗口使用COLORKEY背景，通过LWA_COLORKEY实现透明
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
        set_layered_transparent(
            self._handle_hwnd, int(self.cfg['opacity'] * 255), colorkey=True, show_taskbar=False)

        self.root.after(200, self._show_handle)

        self.handle_canvas.bind("<Enter>", lambda e: self._on_handle_hover(True))
        self.handle_canvas.bind("<Leave>", lambda e: self._on_handle_hover(False))
        self.handle_canvas.bind("<ButtonPress-1>", self._on_handle_press)
        self.handle_canvas.bind("<B1-Motion>", self._on_handle_drag)
        self.handle_canvas.bind("<ButtonRelease-1>", self._on_handle_release)
        self.handle_canvas.bind("<MouseWheel>", self._on_handle_wheel)
        self.handle_canvas.bind("<Button-3>", self._show_handle_menu)

        self.handle_menu = tk.Menu(self.root, tearoff=0)
        self.handle_menu.add_command(label="显示/隐藏主窗口", command=self._tray_toggle)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="打开文件", command=self.file_open)
        self.handle_menu.add_command(label="保存文件", command=self.file_save)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="反色显示", command=self.toggle_invert)
        self.handle_menu.add_command(label="易读模式", command=self.toggle_read)
        self.handle_menu.add_command(label="置顶模式", command=self.toggle_topmost)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="设置面板", command=self.show_settings)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="关于", command=self._show_about)
        self.handle_menu.add_command(label="退出", command=self.exit_app)

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
        hsize = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        hx = wx - hsize // 2
        hy = wy - hsize // 2 - 40

        if hy < 0:
            hy = 0

        self.handle_win.geometry(f"+{hx}+{hy}")
        self.handle_win.lift()

    def _update_handle(self):
        self.handle_canvas.delete("all")
        size = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        color = self.cfg['corner_color']
        if self.cfg['invert_mode']:
            color = invert_color(color)
        color = mix_color(color, self.cfg['corner_opacity'], "#000000")

        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        cx, cy = hs // 2, hs // 2
        r = size // 2

        focused = (self.root.focus_get() == self.text)

        if focused:
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=color, outline=color, width=2)
        else:
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color, width=2, fill="")
            self.handle_canvas.create_oval(
                cx - 3, cy - 3, cx + 3, cy + 3,
                fill=color, outline="")

    def _on_handle_hover(self, entering):
        self._update_handle()

    def _show_handle_menu(self, event):
        try:
            self.handle_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.handle_menu.grab_release()

    def _on_handle_press(self, event):
        self._drag_active = True
        self._drag_dx = event.x_root - self.root.winfo_x()
        self._drag_dy = event.y_root - self.root.winfo_y()
        self._lift_all()
        self.text.focus_set()
        self._update_handle()

    def _lift_all(self):
        self.root.lift()
        self.handle_win.lift()
        if self.cfg['show_panel']:
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

    def _on_handle_wheel(self, event):
        delta = 1 if event.delta > 0 else -1
        new_op = max(MIN_WINDOW_OPACITY, min(1.0, self.cfg['opacity'] + delta * 0.05))
        self.cfg['opacity'] = round(new_op, 2)
        self._apply_window_opacity()
        if not self._handle_hwnd:
            self._handle_hwnd = self.handle_win.winfo_id()
        set_layered_transparent(
            self._handle_hwnd, int(self.cfg['opacity'] * 255), colorkey=True, show_taskbar=False)
        self._save_config_debounced()

    # -------------------------------------------------------------------------
    # 操作面板
    # -------------------------------------------------------------------------

    def _init_panel(self):
        self.panel = tk.Toplevel(self.root)
        self.panel.overrideredirect(True)

        # 面板窗口使用COLORKEY背景，通过LWA_COLORKEY实现透明
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
            colorkey=True,
            show_taskbar=False)

        self.panel_outer = tk.Frame(self.panel, bg="#444444", bd=0)
        self.panel_outer.pack(fill="both", expand=True, padx=2, pady=2)

        self.panel_inner = tk.Frame(self.panel_outer, bg=self.cfg['panel_bg_color'])
        self.panel_inner.pack(fill="both", expand=True, padx=1, pady=1)

        btn_color_14 = "#333333"
        btn_color_58 = "#3d3d3d"
        btn_color_x = "#2a2a2a"

        buttons = [
            ("O",   "打开文件\nCtrl+O",       self.file_open,     btn_color_14, False),
            ("S",   "保存文件\nCtrl+S",       self.file_save,     btn_color_14, False),
            ("A",   "全选\nCtrl+A",           self.text_select_all, btn_color_14, False),
            ("SN",  "另存为\nCtrl+Shift+S",   self.file_save_as,  btn_color_14, False),
            ("反",  "反色显示\nCtrl+F",       self.toggle_invert, btn_color_58, "invert_mode"),
            ("易",  "易读模式\nCtrl+Shift+R", self.toggle_read,   btn_color_58, "read_mode"),
            ("顶",  "置顶模式\nCtrl+T",       self.toggle_topmost, btn_color_58, "topmost"),
            ("控",  "设置面板\nCtrl+K",       self.show_settings, btn_color_58, False),
            ("X",   "退出程序",               self.exit_app,      btn_color_x,  False),
        ]

        self.panel_buttons = {}
        self.panel_button_dots = {}
        for i, (text, tip, cmd, bg, state_key) in enumerate(buttons):
            container = tk.Frame(self.panel_inner, bg=bg, width=PANEL_BTN_W, height=PANEL_BTN_H)
            container.pack_propagate(False)
            container.grid(row=0, column=i, padx=1, pady=1)

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
            btn.pack(fill="both", expand=True, padx=0, pady=0)

            if state_key:
                dot_canvas = tk.Canvas(container, bg=bg, width=8, height=8,
                                       highlightthickness=0, bd=0)
                dot_canvas.place(x=PANEL_BTN_W - 9, y=3)
                if self.cfg.get(state_key, False):
                    dot_canvas.create_oval(
                        2, 2, 7, 7,
                        fill="#ff3333", outline="")
                self.panel_button_dots[text] = dot_canvas
            else:
                self.panel_button_dots[text] = None

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

    def _update_panel_button_states(self):
        dot_map = {
            "反": "invert_mode",
            "易": "read_mode",
            "顶": "topmost",
        }
        for text, key in dot_map.items():
            canvas = self.panel_button_dots.get(text)
            if canvas:
                canvas.delete("all")
                if self.cfg.get(key, False):
                    canvas.create_oval(
                        2, 2, 7, 7,
                        fill="#ff3333", outline="")

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
        self._apply_text_appearance()
        self._update_panel_button_states()
        self._save_config_debounced()

    def toggle_topmost(self):
        self.cfg['topmost'] = not self.cfg['topmost']
        self.root.attributes("-topmost", self.cfg['topmost'])
        self._update_panel_button_states()
        self._save_config_debounced()

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
        ]
        for seq, func in binds:
            self.root.bind(seq, func)
            self.text.bind(seq, func)

        self.text.bind("<FocusIn>", lambda e: self._on_focus_change())
        self.text.bind("<FocusOut>", lambda e: self._update_handle())

        self.root.bind("<ButtonPress-1>", lambda e: self._on_focus_change())
        self.root.bind("<Configure>", self._on_window_configure)

    def _on_window_configure(self, event):
        if event.widget == self.root:
            if hasattr(self, '_sb_visible') and self._sb_visible:
                self.root.after(10, self._redraw_scrollbar)

    def _on_focus_change(self):
        self.root.lift()
        self.handle_win.lift()
        if self.cfg['show_panel']:
            self.panel.lift()
        self._update_handle()

    # -------------------------------------------------------------------------
    # 设置面板
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

    def _opacity_scale(self, parent, var, from_=0.0, to=1.0, on_change=None):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)

        tk.Label(frame, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 4))

        scale = ttk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal",
                          command=lambda v, vv=var, oc=on_change: self._on_scale_change(vv, oc))
        scale.pack(side="left", fill="x", expand=True)

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

        scale = ttk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal",
                          command=lambda v, vv=var, oc=on_change: self._on_scale_change(vv, oc))
        scale.pack(side="left", fill="x", expand=True)

        return frame

    def _refresh_preview(self):
        old_cfg = self.cfg
        self.cfg = self._preview_cfg
        try:
            self._apply_window_opacity()
            self._apply_text_appearance()
            self._corner_dirty = True
            self._update_corners()
            self._update_handle()
            self._update_panel_button_states()

            self.panel_inner.configure(bg=self._preview_cfg['panel_bg_color'])
            if not self._panel_hwnd:
                self._panel_hwnd = self.panel.winfo_id()
            alpha = int(max(MIN_PANEL_OPACITY, self._preview_cfg['panel_opacity']) * 255)
            set_layered_transparent(self._panel_hwnd, alpha, colorkey=True, show_taskbar=False)

            if not self._handle_hwnd:
                self._handle_hwnd = self.handle_win.winfo_id()
            set_layered_transparent(
                self._handle_hwnd, int(self._preview_cfg['opacity'] * 255), colorkey=True, show_taskbar=False)

            self.root.attributes("-topmost", self._preview_cfg['topmost'])

            if self._preview_cfg['show_scrollbar']:
                self.text.see("1.0")
            else:
                self._set_scrollbar_visible(False)

            if self._preview_cfg['show_panel']:
                self.panel.deiconify()
            else:
                self.panel.withdraw()

            self._layout_handle()
        finally:
            self.cfg = old_cfg

    def _build_tab_system(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="系统设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="显示设置", padding=8)
        gf1.pack(fill="x", pady=6)

        v_invert = tk.BooleanVar(value=cfg['invert_mode'])
        v_read = tk.BooleanVar(value=cfg['read_mode'])
        v_top = tk.BooleanVar(value=cfg['topmost'])

        def update_display():
            cfg['invert_mode'] = v_invert.get()
            cfg['read_mode'] = v_read.get()
            cfg['topmost'] = v_top.get()
            self._refresh_preview()

        ttk.Checkbutton(gf1, text="反色显示", variable=v_invert, command=update_display).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="易读模式", variable=v_read, command=update_display).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="置顶模式", variable=v_top, command=update_display).pack(anchor="w", pady=2)

        gf2 = ttk.LabelFrame(f, text="运行设置", padding=8)
        gf2.pack(fill="x", pady=6)

        v_taskbar = tk.BooleanVar(value=cfg['show_taskbar'])
        v_show_panel = tk.BooleanVar(value=cfg['show_panel'])
        v_opacity = tk.DoubleVar(value=cfg['opacity'])

        def update_runtime():
            cfg['show_taskbar'] = v_taskbar.get()
            cfg['show_panel'] = v_show_panel.get()
            cfg['opacity'] = round(clamp(v_opacity.get(), MIN_WINDOW_OPACITY, 1.0), 2)
            self._refresh_preview()

        ttk.Checkbutton(gf2, text="显示任务栏窗口", variable=v_taskbar, command=update_runtime).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf2, text="显示操作面板", variable=v_show_panel, command=update_runtime).pack(anchor="w", pady=2)

        ttk.Label(gf2, text="窗口整体透明度：").pack(anchor="w", pady=(8, 2))
        self._opacity_scale(gf2, v_opacity, from_=MIN_WINDOW_OPACITY, to=1.0, on_change=update_runtime)

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
            ttk.Scale(row, from_=min_op, to=1.0, variable=opacity_var, orient="horizontal",
                      command=lambda v: on_change()).pack(side="left", fill="x", expand=True)
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
        ttk.Scale(row_corner, from_=MIN_CORNER_LEN, to=MAX_CORNER_LEN, variable=v_corner_sz, orient="horizontal",
                  command=lambda v: update_corner_dims()).pack(side="left", fill="x", expand=True)

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
        ttk.Scale(row_size, from_=MIN_FONT_SIZE, to=MAX_FONT_SIZE, variable=v_size, orient="horizontal",
                  command=lambda v: update_text_style()).pack(side="left", fill="x", expand=True)

        gf4 = ttk.LabelFrame(f, text="控制手柄", padding=8)
        gf4.pack(fill="x", pady=6)

        v_handle_size = tk.IntVar(value=cfg['handle_size'])

        def update_handle():
            cfg['handle_size'] = clamp(v_handle_size.get(), MIN_HANDLE_SIZE, MAX_HANDLE_SIZE)
            self._refresh_preview()

        row_handle = tk.Frame(gf4)
        row_handle.pack(fill="x", pady=3)
        ttk.Label(row_handle, text="手柄尺寸：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Spinbox(row_handle, from_=MIN_HANDLE_SIZE, to=MAX_HANDLE_SIZE, textvariable=v_handle_size,
                    width=4, command=update_handle).pack(side="left", padx=(0, 8))
        ttk.Scale(row_handle, from_=MIN_HANDLE_SIZE, to=MAX_HANDLE_SIZE, variable=v_handle_size, orient="horizontal",
                  command=lambda v: update_handle()).pack(side="left", fill="x", expand=True)

        ttk.Label(gf4, text="手柄样式（待开发）", foreground="#999999").pack(anchor="w", pady=(8, 2))

    def _build_tab_panel(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="操作面板设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="面板外观", padding=8)
        gf1.pack(fill="x", pady=6)

        v_panel_bg = tk.StringVar(value=cfg['panel_bg_color'])
        v_panel_opacity = tk.DoubleVar(value=cfg['panel_opacity'])

        def update_panel():
            cfg['panel_bg_color'] = v_panel_bg.get()
            cfg['panel_opacity'] = round(clamp(v_panel_opacity.get(), MIN_PANEL_OPACITY, 1.0), 2)
            self._refresh_preview()

        row1 = tk.Frame(gf1)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="面板颜色：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        self._color_button(row1, v_panel_bg, on_change=update_panel).pack(side="left", padx=(0, 8))
        tk.Label(row1, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
        ttk.Scale(row1, from_=MIN_PANEL_OPACITY, to=1.0, variable=v_panel_opacity, orient="horizontal",
                  command=lambda v: update_panel()).pack(side="left", fill="x", expand=True)
        tk.Label(row1, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
        pct = tk.Label(row1, text=f"{int(v_panel_opacity.get()*100)}%", width=5, anchor="w")
        pct.pack(side="left")
        v_panel_opacity.trace_add("write", lambda *a: pct.config(text=f"{int(v_panel_opacity.get()*100)}%"))

        gf2 = ttk.LabelFrame(f, text="按钮说明", padding=8)
        gf2.pack(fill="both", expand=True, pady=6)

        btn_info = [
            ("O",  "打开文件",   "Ctrl+O",       "#333333"),
            ("S",  "保存文件",   "Ctrl+S",       "#333333"),
            ("A",  "全选",       "Ctrl+A",       "#333333"),
            ("SN", "另存为",     "Ctrl+Shift+S", "#333333"),
            ("反", "反色显示",   "Ctrl+F",       "#3d3d3d"),
            ("易", "易读模式",   "Ctrl+Shift+R", "#3d3d3d"),
            ("顶", "置顶模式",   "Ctrl+T",       "#3d3d3d"),
            ("控", "设置面板",   "Ctrl+K",       "#3d3d3d"),
            ("X",  "退出程序",   "—",            "#2a2a2a"),
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
                ttk.Label(f, text="[图标]", font=("Microsoft YaHei UI", 24)).pack(pady=(12, 4))
        else:
            ttk.Label(f, text="[S]", font=("Microsoft YaHei UI", 24, "bold")).pack(pady=(12, 4))

        ttk.Label(f, text=f"{APP_NAME} {VERSION}", font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(4, 4))
        ttk.Label(f, text="作者：Magicxh & TRAE").pack(pady=2)
        ttk.Label(f, text=f"邮箱：{CONTACT_EMAIL}").pack(pady=2)
        ttk.Label(f, text="\n完全透明的记事本工具").pack(pady=(8, 4))
        ttk.Label(f, text="支持多种透明度设置、反色显示、易读模式等功能").pack(pady=2)

    def _apply_settings(self):
        self.cfg = copy.deepcopy(self._preview_cfg)
        self._apply_window_opacity()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._save_config_debounced()

    def _ok_settings(self):
        self._apply_settings()
        self._settings_win.destroy()

    # -------------------------------------------------------------------------
    # 系统托盘
    # -------------------------------------------------------------------------

    def _init_tray(self):
        try:
            import pystray
            from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem as TrayItem

            def on_tray_click(icon, item):
                if str(item) == "显示/隐藏":
                    self.root.after(0, self._tray_toggle)
                elif str(item) == "打开文件":
                    self.root.after(0, self.file_open)
                elif str(item) == "保存文件":
                    self.root.after(0, self.file_save)
                elif str(item) == "设置":
                    self.root.after(0, self.show_settings)
                elif str(item) == "退出":
                    self.root.after(0, self.exit_app)

            def on_tray_clicked(icon):
                self.root.after(0, self._tray_toggle)

            menu = TrayMenu(
                TrayItem("显示/隐藏", on_tray_click),
                TrayItem("打开文件", on_tray_click),
                TrayItem("保存文件", on_tray_click),
                TrayItem("设置", on_tray_click),
                TrayItem("退出", on_tray_click)
            )

            icon_image = None
            if self.icon_path and os.path.exists(self.icon_path):
                try:
                    from PIL import Image
                    icon_image = Image.open(self.icon_path)
                except Exception:
                    pass

            if icon_image:
                self.tray_icon = TrayIcon(APP_NAME, icon_image, APP_NAME, menu)
            else:
                self.tray_icon = TrayIcon(APP_NAME, None, APP_NAME, menu)

            self.tray_icon.run(clicked=on_tray_clicked)
        except Exception as e:
            print(f"[托盘] 初始化失败: {e}")
            self.tray_icon = None

    def _tray_toggle(self):
        if self._window_visible:
            self._hide_window()
        else:
            self._show_window()

    def _show_about(self):
        messagebox.showinfo(f"{APP_NAME} {VERSION}",
                            f"{APP_NAME} {VERSION}\n\n作者：Magicxh & TRAE\n邮箱：{CONTACT_EMAIL}\n\n完全透明的记事本工具")

    def exit_app(self):
        if self._check_save_before_close():
            return
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def _on_close(self):
        if self.cfg['show_taskbar']:
            self.exit_app()
        else:
            self._tray_toggle()


if __name__ == "__main__":
    app = StealthNoteApp()
    app.root.mainloop()
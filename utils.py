# -*- coding: utf-8 -*-
"""Stealth Note - 工具函数模块"""

import os
import copy
import shutil
import json
from constants import (
    COLORKEY, COLORKEY_INT, GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TOOLWINDOW,
    WS_EX_APPWINDOW, LWA_ALPHA, LWA_COLORKEY, SWP_NOMOVE, SWP_NOSIZE,
    SWP_NOZORDER, SWP_FRAMECHANGED, user32, kernel32,
    CONFIG_FILE, ICON_FILE)


def invert_color(hex_color):
    """反色"""
    try:
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return f"#{255 - r:02x}{255 - g:02x}{255 - b:02x}"
    except Exception:
        return "#000000" if hex_color.lower() == "#ffffff" else "#FFFFFF"


def mix_color(fg_hex, opacity, bg_hex="#000000"):
    """按透明度混合前景色和背景色"""
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
    """限制值在范围内"""
    return max(min_val, min(max_val, value))


def detect_encoding(file_path):
    """检测文件编码"""
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
    """读取文本文件"""
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
    """写入文本文件"""
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


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
    """创建应用图标，如果文件不存在则用PIL动态生成"""
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
    """检查单实例运行"""
    mutex_name = "StealthNote_SingleInstance_Mutex_v280"
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(mutex)
        return None
    return mutex
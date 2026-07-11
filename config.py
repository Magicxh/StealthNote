# -*- coding: utf-8 -*-
"""Stealth Note - 配置管理模块"""

import os
import sys
import json
import copy
import shutil
from constants import CONFIG_FILE, MIN_TEXT_OPACITY, MIN_WINDOW_OPACITY, MIN_PANEL_OPACITY, MIN_FONT_SIZE, MAX_FONT_SIZE, MIN_CORNER_LEN, MAX_CORNER_LEN, MIN_CORNER_LINE, MAX_CORNER_LINE, MIN_HANDLE_SIZE, MAX_HANDLE_SIZE, MIN_READ_BG_OPACITY, MIN_CORNER_OPACITY, MIN_WINDOW_W, MIN_WINDOW_H
from utils import clamp

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
    "theme_mode": "dark",
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


def validate_config(cfg):
    """验证并修正配置"""
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
    """加载配置"""
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
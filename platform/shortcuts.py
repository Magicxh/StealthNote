# -*- coding: utf-8 -*-
"""Stealth Note - 快捷键模块"""

from constants import *


class Shortcuts:
    """快捷键管理类"""
    
    DEFAULT_BINDS = [
        ("<Control-o>",       "file_open"),
        ("<Control-s>",       "file_save"),
        ("<Control-a>",       "text_select_all"),
        ("<Control-Shift-s>", "file_save_as"),
        ("<Control-f>",       "toggle_invert"),
        ("<Control-Shift-r>", "toggle_read"),
        ("<Control-t>",       "toggle_topmost"),
        ("<Control-k>",       "show_settings"),
        ("<Control-m>",       "toggle_theme"),
    ]
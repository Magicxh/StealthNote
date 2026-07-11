# -*- coding: utf-8 -*-
"""Stealth Note v2.8.4 - 入口"""

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


def main():
    app = StealthNoteApp()
    app.run()


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""Stealth Note - 任务栏代理窗口模块"""
import os
import tkinter as tk
from constants import (
    APP_NAME, GWL_EXSTYLE, WS_EX_LAYERED, LWA_ALPHA, user32,
)
from utils import set_layered_transparent


class TaskbarHost:
    """任务栏代理窗口：在任务栏显示图标和标题，点击时激活主窗口"""

    def __init__(self, app):
        self.app = app
        self.host_win = None
        self._host_hwnd = None
        self._host_minimizing = False
        self._host_restoring = False
        self._create()

    def _create(self):
        """创建任务栏代理窗口（透明正常窗口，确保任务栏图标显示且点击有效）"""
        self.host_win = tk.Toplevel(self.app.root)
        self.host_win.title(APP_NAME)
        if self.app.icon_path and os.path.exists(self.app.icon_path):
            try:
                self.host_win.iconbitmap(self.app.icon_path)
            except Exception as e:
                print(f"[任务栏] 设置图标失败: {e}")

        self.host_win.geometry("1x1+-10000+-10000")
        self.host_win.update_idletasks()
        self._host_hwnd = self.host_win.winfo_id()

        ex_style = user32.GetWindowLongW(self._host_hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_LAYERED
        user32.SetWindowLongW(self._host_hwnd, GWL_EXSTYLE, ex_style)
        user32.SetLayeredWindowAttributes(self._host_hwnd, 0, 0, LWA_ALPHA)

        self.host_win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.host_win.bind("<Unmap>", self._on_unmap)
        self.host_win.bind("<Map>", self._on_map)
        self.host_win.bind("<FocusIn>", self._on_focus)

    def _on_close(self):
        """任务栏窗口关闭：退出程序"""
        self.app.exit_app()

    def _on_unmap(self, event=None):
        """任务栏窗口被最小化：同步隐藏主窗口"""
        if self._host_restoring:
            return
        self._host_minimizing = True
        if self.app._window_visible:
            self.app._hide_window()
        self.host_win.after(50, lambda: setattr(self, '_host_minimizing', False))

    def _on_map(self, event=None):
        """任务栏窗口被恢复：同步显示主窗口"""
        if self._host_minimizing:
            return
        self._host_restoring = True
        if not self.app._window_visible:
            self.app._show_window()
        self.host_win.after(50, lambda: setattr(self, '_host_restoring', False))

    def _on_focus(self, event=None):
        """任务栏窗口获得焦点：将主窗口带到前台"""
        if self.app._window_visible:
            self.app._force_foreground()

    def sync(self):
        """同步任务栏代理窗口与主窗口的显示状态"""
        if not self.host_win or not self.host_win.winfo_exists():
            return
        if not self.app.cfg['show_taskbar']:
            self.host_win.withdraw()
            return

        if self.app._window_visible:
            self.host_win.deiconify()
            self.host_win.lower()
        else:
            self.host_win.iconify()

    def set_visible(self, visible):
        """设置任务栏可见性"""
        if visible:
            self.host_win.deiconify()
        else:
            self.host_win.withdraw()

    def set_title(self, title):
        """设置任务栏标题"""
        self.host_win.title(title)
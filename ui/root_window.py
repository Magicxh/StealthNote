# -*- coding: utf-8 -*-
"""Stealth Note - 窗口管理模块（RootWindowMixin）"""
import tkinter as tk
from constants import *
from utils import set_layered_transparent

class RootWindowMixin:
    """窗口管理 Mixin：创建、样式、同步、任务栏"""

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

        # B18: 立即设置 WS_EX_TOOLWINDOW，避免 root 窗口在首次 _apply_window_style 前出现在任务栏
        try:
            ex_style = user32.GetWindowLongW(self._root_hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(self._root_hwnd, GWL_EXSTYLE, ex_style)
        except Exception:
            pass

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 绑定窗口事件（根窗口 + 内容窗口双保险，确保四角缩放可命中）
        self.root.bind("<ButtonPress-1>", self._on_root_button_press)
        self.root.bind("<B1-Motion>", self._on_root_resize)
        self.root.bind("<ButtonRelease-1>", self._on_root_resize_end)
        self.root.bind("<Motion>", self._on_root_motion)
        self.root.bind("<MouseWheel>", self._on_root_wheel)
        self.root.bind("<Configure>", self._on_window_configure)

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

            if hasattr(self, '_taskbar_host') and self._taskbar_host:
                self._taskbar_host.sync()
        except Exception as e:
            print(f"[窗口样式] 设置失败: {e}")

    def _set_taskbar_visible(self, visible):
        """设置任务栏是否显示"""
        self.cfg['show_taskbar'] = visible
        self._apply_window_style()
        if hasattr(self, '_taskbar_host') and self._taskbar_host:
            if visible:
                self._taskbar_host.set_visible(True)
            else:
                self._taskbar_host.set_visible(False)

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
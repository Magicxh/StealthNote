# -*- coding: utf-8 -*-
"""Stealth Note v2.9.0 - 主应用类"""

import os
import sys
import json
import copy
import tkinter as tk
from tkinter import messagebox, filedialog

from constants import *
from utils import (
    read_text_file, write_text_file, mix_color, clamp,
    create_app_icon, check_single_instance
)
from config import DEFAULT_CONFIG, load_config, validate_config

# UI Mixins
from ui.root_window import RootWindowMixin
from ui.text_cluster import TextClusterMixin
from ui.stealth_cluster import StealthClusterMixin
from ui.handle import HandleMixin
from ui.panel import PanelMixin
from ui.corners import CornersMixin
from ui.settings import SettingsMixin

# Platform
from platform.taskbar import TaskbarHost
from platform.tray import TrayIcon


class StealthNoteApp(
    RootWindowMixin,
    TextClusterMixin,
    StealthClusterMixin,
    HandleMixin,
    PanelMixin,
    CornersMixin,
    SettingsMixin,
):
    """Stealth Note 主应用类"""

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
        self._stealth_wheel_acc = 0
        self._preview_after_id = None

        self._root_hwnd = None
        self._handle_hwnd = None
        self._panel_hwnd = None

        self.icon_path = create_app_icon()

        # 1. 创建主窗口
        self._create_root()
        # 2. 创建任务栏代理
        self._taskbar_host = TaskbarHost(self)
        # 3. 初始化所有UI组件
        self._init_content()
        self._init_corners()
        self._init_handle()
        self._init_panel()
        self._init_shortcuts()

        # 应用初始样式
        self.root.deiconify()
        self._apply_window_style()
        self._apply_text_appearance()
        self.root.after(100, self._layout_all)

        self.root.lift()
        self._window_visible = True

        if not os.path.exists(CONFIG_FILE):
            self._save_config_debounced()

        # 延迟初始化托盘
        self.root.after(300, self._init_tray)
        self.root.after(200, self._focus_text)
        if self.cfg.get('stealth_mode'):
            self.root.after(250, self._apply_stealth_state)

    # -------------------------------------------------------------------------
    # 单实例消息
    # -------------------------------------------------------------------------

    def _show_single_instance_msg(self):
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(APP_NAME, f"{APP_NAME} 已经在运行中。\n\n请查看系统托盘或任务栏。")
            root.destroy()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 配置保存
    # -------------------------------------------------------------------------

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

    def text_select_all(self):
        widget = self._get_active_text_widget()
        widget.tag_add("sel", "1.0", "end")
        return "break"

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
        self.root.deiconify()
        if hasattr(self, 'bg_win') and self.bg_win:
            self.bg_win.deiconify()
            self.bg_win.lower()
        self.content_win.deiconify()
        self.handle_win.deiconify()
        if self.cfg['show_panel']:
            self.panel.deiconify()
        self._window_visible = True
        # B29: deiconify 后重新设置窗口样式，防止 WS_EX_TOOLWINDOW 被重置导致任务栏双窗口
        self._apply_window_style()
        # B26: 如果书写框被双击隐藏，恢复时保持隐藏
        if getattr(self, '_text_hidden', False):
            self.root.withdraw()
            if hasattr(self, 'bg_win') and self.bg_win:
                self.bg_win.withdraw()
            self.content_win.withdraw()
        else:
            self._sync_content_window()
            self._force_foreground()
            if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
                self.stealth_text.focus_set()
            else:
                self.text.focus_set()
        self._taskbar_host.sync()

    def _hide_window(self):
        self.root.withdraw()
        if hasattr(self, 'bg_win') and self.bg_win:
            self.bg_win.withdraw()
        self.content_win.withdraw()
        self.handle_win.withdraw()
        if self.cfg['show_panel']:
            self.panel.withdraw()
        self._window_visible = False
        self._taskbar_host.sync()

    # -------------------------------------------------------------------------
    # 托盘
    # -------------------------------------------------------------------------

    def _init_tray(self):
        self._tray = TrayIcon(self)

    # -------------------------------------------------------------------------
    # 退出
    # -------------------------------------------------------------------------

    def _tray_toggle(self):
        """切换窗口显示/隐藏（托盘和手柄菜单共用）"""
        if self._window_visible:
            self._hide_window()
        else:
            self._show_window()

    def _show_about(self):
        messagebox.showinfo(f"{APP_NAME} {VERSION}",
                            f"{APP_NAME} {VERSION}\n\n作者：{AUTHOR}\n邮箱：{CONTACT_EMAIL}\n\n完全透明的记事本工具")

    def _on_close(self):
        """窗口关闭事件"""
        if self.cfg.get('show_taskbar', True):
            self.exit_app()
        else:
            self._tray_toggle()

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
            if hasattr(self, '_tray') and self._tray:
                self._tray.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.exit_app()
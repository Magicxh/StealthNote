# -*- coding: utf-8 -*-
"""Stealth Note v2.9.7 - 主应用类"""

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
from ui.titlebar import TitlebarMixin
from ui.statusbar import StatusbarMixin

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
    TitlebarMixin,
    StatusbarMixin,
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

        # 暂存模式状态
        self._autosave_mode = False        # 是否处于暂存模式
        self._autosave_dirty = False       # 暂存模式下是否有未自动保存的改动
        self._autosave_timer_id = None     # 自动暂存计时器

        self._root_hwnd = None
        self._panel_hwnd = None

        self.icon_path = create_app_icon()

        # v2.9.7 修正初始化顺序：host_win 先创建，所有子窗口立即设置 GWLP_HWNDPARENT
        # 确保 Windows 从一开始就知道只有 host_win 是任务栏窗口，彻底杜绝双窗口

        # 1. 创建 root（Tk），立即 withdraw，不显示
        self._create_root()
        # 2. 创建任务栏代理（host_win）
        self._taskbar_host = TaskbarHost(self)
        self._host_hwnd = self._taskbar_host.get_hwnd()
        # 3. 设置 root 的所有者（在 root 第一次显示之前！）
        self._set_window_owner(self._root_hwnd, self._host_hwnd)
        # 4. 初始化所有 UI 组件（每个组件创建窗口后立即设所有者）
        self._init_content()
        self._init_corners()
        self._init_handle()
        self._init_panel()
        self._init_titlebar()
        self._init_statusbar()
        self._init_shortcuts()

        # 应用初始样式
        self.root.deiconify()
        self._apply_window_style()
        self._apply_text_appearance()
        self._refresh_titlebar()
        self._refresh_statusbar()
        self.root.after(100, self._layout_all)

        self.root.lift()
        self._window_visible = True

        # 启动时：如果上次以暂存模式关闭，自动读取暂存内容
        self._check_autosave_on_startup()

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
    # 暂存模式管理
    # -------------------------------------------------------------------------

    def _is_autosave_mode(self):
        """是否处于暂存模式"""
        return self._autosave_mode

    def _check_autosave_on_startup(self):
        """启动时检查是否需要自动读取暂存内容。
        如果上次以暂存模式关闭且 Autosave.txt 有内容，自动读取并进入暂存模式。
        """
        if not self.cfg.get('last_autosave_closed', False):
            return
        if not os.path.exists(AUTOSAVE_FILE):
            return
        try:
            with open(AUTOSAVE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.strip():
                self.text.delete("1.0", "end")
                self.text.insert("1.0", content)
                self.text.edit_reset()
                self._modified = False
                self._enter_autosave_mode()
                self._update_title()
                if self.cfg['read_mode']:
                    self.root.after(50, self._apply_read_mode_bg)
        except Exception as e:
            print(f"[暂存] 启动读取失败: {e}")

    def _enter_autosave_mode(self):
        """进入暂存模式：启动自动保存计时器"""
        if self._autosave_mode:
            return
        self._autosave_mode = True
        self._autosave_dirty = True
        self._start_autosave_timer()
        if hasattr(self, '_refresh_titlebar'):
            self._refresh_titlebar()

    def _exit_autosave_mode(self):
        """退出暂存模式：取消计时器，重置状态"""
        if not self._autosave_mode:
            return
        self._autosave_mode = False
        self._autosave_dirty = False
        if self._autosave_timer_id is not None:
            try:
                self.root.after_cancel(self._autosave_timer_id)
            except Exception:
                pass
            self._autosave_timer_id = None
        if hasattr(self, '_refresh_titlebar'):
            self._refresh_titlebar()

    def _start_autosave_timer(self):
        """启动/重置自动暂存计时器"""
        if self._autosave_timer_id is not None:
            try:
                self.root.after_cancel(self._autosave_timer_id)
            except Exception:
                pass
        self._autosave_timer_id = self.root.after(AUTOSAVE_INTERVAL_MS, self._autosave_timer_tick)

    def _autosave_timer_tick(self):
        """自动暂存计时器回调"""
        self._autosave_timer_id = None
        if self._autosave_mode and self._autosave_dirty:
            self._autosave_save()
        if self._autosave_mode:
            self._start_autosave_timer()

    def _autosave_save(self):
        """保存暂存内容到 Autosave.txt"""
        try:
            content = self.text.get("1.0", "end-1c")
            with open(AUTOSAVE_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            self._autosave_dirty = False
            if hasattr(self, '_refresh_titlebar'):
                self._refresh_titlebar()
        except Exception as e:
            print(f"[暂存] 保存失败: {e}")

    def _load_autosave(self):
        """读取暂存文件到文本框，进入暂存模式"""
        if not os.path.exists(AUTOSAVE_FILE):
            messagebox.showinfo("读取暂存", "没有暂存内容。")
            return
        try:
            with open(AUTOSAVE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.text.edit_reset()
            self.current_file = None
            self.current_encoding = 'utf-8'
            self._modified = False
            self._enter_autosave_mode()
            self._update_title()
            if self.cfg['read_mode']:
                self.root.after(50, self._apply_read_mode_bg)
        except Exception as e:
            messagebox.showerror("读取暂存失败", str(e))

    def _check_autosave_before_new(self):
        """新建/打开文件前检查暂存模式，返回 True 表示中断操作。

        暂存模式下提示用户是否另存为新文件：
        - 是：执行另存为，成功后退出暂存模式
        - 否：保留 Autosave.txt（已自动保存），退出暂存模式
        - 取消：中断操作
        """
        if not self._autosave_mode:
            # 非暂存模式，走原有未保存检查
            return self._check_save_before_close()
        # 暂存模式：先保存当前暂存
        self._autosave_save()
        result = messagebox.askyesnocancel("暂存内容", "当前处于暂存模式，是否将暂存内容另存为新文件？")
        if result is None:
            return True  # 取消
        if result:
            # 是：执行另存为
            if not self.file_save_as():
                return True  # 另存为失败或取消，中断操作
        # 否或另存为成功：退出暂存模式
        self._exit_autosave_mode()
        return False

    # -------------------------------------------------------------------------
    # 文件操作
    # -------------------------------------------------------------------------

    def file_new(self):
        """新建文件：检查未保存内容后清空文本框"""
        if self._check_autosave_before_new():
            return
        self.text.delete("1.0", "end")
        self.text.edit_reset()
        self.current_file = None
        self.current_encoding = 'utf-8'
        self._modified = False
        self._update_title()

    def file_open(self):
        if self._check_autosave_before_new():
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
            self._exit_autosave_mode()
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
            # 暂存模式下另存为新文件成功：清空 Autosave.txt，退出暂存模式
            if self._autosave_mode:
                try:
                    with open(AUTOSAVE_FILE, 'w', encoding='utf-8') as f:
                        f.write("")
                except Exception:
                    pass
                self._exit_autosave_mode()
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
            ("<Control-n>",      lambda e: (self.file_new(), "break")[1]),
            ("<Control-N>",      lambda e: (self.file_new(), "break")[1]),
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
        self.content_win.deiconify()
        if self.cfg['show_panel']:
            self.panel.deiconify()
        self._window_visible = True
        # deiconify 后重新设置窗口样式，防止 WS_EX_TOOLWINDOW 被重置导致任务栏双窗口
        self._apply_window_style()
        self._sync_content_window()
        self._layout_handle()
        # 标题栏同步显示
        if hasattr(self, '_refresh_titlebar'):
            self._refresh_titlebar()
        # 状态栏同步显示
        if hasattr(self, '_refresh_statusbar'):
            self._refresh_statusbar()
        self._force_foreground()
        if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
            self.stealth_text.focus_set()
        else:
            self.text.focus_set()
        self._taskbar_host.sync()

    def _hide_window(self):
        self.root.withdraw()
        self.content_win.withdraw()
        if self.cfg['show_panel']:
            self.panel.withdraw()
        # 标题栏同步隐藏
        if hasattr(self, 'titlebar_win') and self.titlebar_win and self.titlebar_win.winfo_exists():
            self.titlebar_win.withdraw()
            self._titlebar_visible = False
        # 状态栏同步隐藏
        if hasattr(self, 'statusbar_win') and self.statusbar_win and self.statusbar_win.winfo_exists():
            self.statusbar_win.withdraw()
            self._statusbar_visible = False
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
        # 若设置面板处于预览状态（self.cfg 指向 _preview_cfg），先恢复原始配置，避免保存预览值
        if hasattr(self, '_original_cfg') and self._original_cfg is not None:
            self.cfg = self._original_cfg
            self._original_cfg = None
        # 暂存模式下退出：自动保存暂存内容，不弹窗询问，记录关闭状态
        if self._autosave_mode:
            self._autosave_save()
            self.cfg['last_autosave_closed'] = True
        else:
            self.cfg['last_autosave_closed'] = False
            if self._check_save_before_close():
                return
        try:
            if self._window_visible:
                self.cfg['window_width'] = self.content_win.winfo_width()
                self.cfg['window_height'] = self.content_win.winfo_height()
                self.cfg['window_x'] = self.content_win.winfo_x()
                self.cfg['window_y'] = self.content_win.winfo_y()
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
# -*- coding: utf-8 -*-
"""Stealth Note - 窗口管理模块（RootWindowMixin）"""
import tkinter as tk
from constants import *
from utils import set_layered_transparent

class RootWindowMixin:
    """窗口管理 Mixin：创建、样式、同步、任务栏

    v2.9.7+ 架构：
    - host_win 是唯一的任务栏窗口（所有者窗口）
    - root / content_win / panel 等所有可见窗口都通过 GWLP_HWNDPARENT 归属到 host_win
    - 注意：winfo_id() 返回的是 Tk 内部 TkChild 窗口句柄，
      真正与 Windows 窗口管理器交互的是 TkTopLevel 窗口。
      必须用 _get_real_hwnd() 获取真正的顶层窗口句柄。
    """

    def _get_real_hwnd(self, hwnd):
        """获取 Tkinter 窗口对应的真正顶层 HWND（TkTopLevel 而非 TkChild）。

        Tkinter winfo_id() 返回的是内部 TkChild 窗口句柄，
        而 Windows 任务栏/窗口管理器交互的是外层的 TkTopLevel 窗口。
        必须对真正的 TkTopLevel 窗口设置样式才能生效。

        使用 GA_ROOT 而非 GA_ROOTOWNER：GA_ROOT 找到该窗口所属的顶层窗口（TkTopLevel），
        GA_ROOTOWNER 会追溯所有者链，导致不同 Toplevel 返回同一个 HWND。
        """
        if not hwnd:
            return 0
        try:
            return user32.GetAncestor(hwnd, GA_ROOT)
        except Exception:
            return hwnd

    def _set_window_owner(self, child_hwnd, owner_hwnd):
        """设置窗口所有者（GWLP_HWNDPARENT）。

        必须在子窗口第一次显示 / 第一次调用 SetWindowPos 之前调用，
        否则 Windows 可能已经将其注册到任务栏。

        注意：使用 _get_real_hwnd() 获取真正的 TkTopLevel 窗口。
        """
        if not child_hwnd or not owner_hwnd:
            return
        try:
            real_child = self._get_real_hwnd(child_hwnd)
            real_owner = self._get_real_hwnd(owner_hwnd)
            SetWindowLongPtrW(real_child, GWLP_HWNDPARENT, real_owner)
        except Exception as e:
            print(f"[窗口] 设置所有者失败: {e}")

    def _force_foreground(self):
        """强制将所有窗口带到最前台。

        v2.9.7.3: 简化 topmost 处理，只在需要时切换一次，避免连续触发 <Configure>。
        """
        try:
            if hasattr(self, '_host_hwnd') and self._host_hwnd:
                real_host = self._get_real_hwnd(self._host_hwnd)
                user32.SetForegroundWindow(real_host)
            real_root = self._get_real_hwnd(self._root_hwnd)
            user32.SetForegroundWindow(real_root)
            user32.BringWindowToTop(real_root)
        except Exception:
            pass
        # 只在非 topmost 模式下临时置顶，避免不必要的 topmost 切换触发 Configure
        if not self.cfg.get('topmost', False):
            self.root.attributes("-topmost", True)
            self.content_win.attributes("-topmost", True)
            if hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
                self.panel.attributes("-topmost", True)
        self.root.lift()
        self.content_win.lift()
        if hasattr(self, 'handle_canvas') and self.handle_canvas:
            self.handle_canvas.tk.call('raise', self.handle_canvas._w)
        if self.cfg.get('show_panel') and hasattr(self, 'panel') and self.panel:
            self.panel.lift()
        # 只在非 topmost 模式下需要恢复
        if not self.cfg.get('topmost', False):
            self.root.after(100, lambda: (
                self.root.attributes("-topmost", False),
                self.content_win.attributes("-topmost", False),
                self.panel.attributes("-topmost", False)
                if hasattr(self, 'panel') and self.panel and self.panel.winfo_exists() else None
            ))

    # -------------------------------------------------------------------------
    # 主窗口
    # -------------------------------------------------------------------------

    def _create_root(self):
        """创建根窗口（完全透明，仅作容器，content_win 负责实际显示。

        v2.9.7: root 窗口向左扩展以容纳手柄 Canvas，彻底消除任务栏双窗口问题。
        """
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

        # v2.9.7: 计算手柄偏移量，root 向左扩展
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        handle_cs = hs + HANDLE_WIN_PADDING * 2
        handle_offset = handle_cs // 2 + HANDLE_REF_R + 20
        # root 向上扩展以完整容纳手柄 Canvas（防止 Canvas 上方被裁剪）
        handle_root_y_offset = max(0, handle_cs // 2 - HANDLE_REF_R)

        root_x = x - handle_offset
        root_y = y - handle_root_y_offset
        root_w = w + handle_offset
        root_h = h + handle_root_y_offset

        self.root.geometry(f"{root_w}x{root_h}+{root_x}+{root_y}")

        # root 完全透明（COLORKEY），content_win 负责实际显示
        self.root.configure(bg=COLORKEY, bd=0, highlightthickness=0)
        self.bg_frame = tk.Frame(self.root, bg=COLORKEY, bd=0, highlightthickness=0)
        self.bg_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.root.update_idletasks()
        self._root_hwnd = self.root.winfo_id()

        # B18: 立即设置 WS_EX_TOOLWINDOW，避免 root 窗口在首次 _apply_window_style 前出现在任务栏
        # v2.9.7: 对真正的 TkTopLevel 窗口设置，而非 TkChild
        try:
            real_hwnd = self._get_real_hwnd(self._root_hwnd)
            ex_style = user32.GetWindowLongW(real_hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(real_hwnd, GWL_EXSTYLE, ex_style)
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
        """应用窗口透明样式（v2.7.3 双层架构）。

        - root: LWA_COLORKEY only，crKey=COLORKEY(#010101)，alpha=255 → COLORKEY 区域穿透
        - content_win: LWA_ALPHA | LWA_COLORKEY，crKey=COLORKEY，alpha=bg_op*255 → 整体半透明
        - 易读模式下 content_win alpha=0（完全透明），由 Text tag 显示行背景
        - Text bg=raw_bg 实色，原生交互顺滑，抗锯齿相对于 raw_bg 无毛边

        v2.9.7.4: 移除 SetWindowPos(SWP_FRAMECHANGED) 调用。
        SetLayeredWindowAttributes 无需 SetWindowPos 即可立即生效；
        WS_EX_LAYERED/WS_EX_TOOLWINDOW 已在初始化时设置，重复设置无需 SWP_FRAMECHANGED。
        SWP_FRAMECHANGED 会触发 Win32 级别重绘，覆盖仪表盘小红点 Canvas 的 lift() 操作。
        """
        try:
            bg_op = max(0.05, self.cfg['bg_opacity'])

            # 计算实际背景色（含反色）
            raw_bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                raw_bg = invert_color(raw_bg)

            # ===== root 窗口：LWA_COLORKEY only =====
            self.root.attributes("-transparentcolor", COLORKEY)
            # v2.9.7: 任务栏样式对真正的 TkTopLevel 设置（幂等操作，无需 SWP_FRAMECHANGED）
            real_root = self._get_real_hwnd(self._root_hwnd)
            ex_style = user32.GetWindowLongW(real_root, GWL_EXSTYLE)
            ex_style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(real_root, GWL_EXSTYLE, ex_style)
            # 透明度属性对 TkChild 设置（内容窗口）
            user32.SetLayeredWindowAttributes(self._root_hwnd, COLORKEY_INT, 255, LWA_COLORKEY)

            # ===== content_win 内容窗口：LWA_ALPHA | LWA_COLORKEY =====
            if not hasattr(self, '_content_hwnd') or not self._content_hwnd:
                self._content_hwnd = self.content_win.winfo_id()
            # v2.9.7: 任务栏样式对真正的 TkTopLevel 设置（幂等操作）
            real_content = self._get_real_hwnd(self._content_hwnd)
            ex2 = user32.GetWindowLongW(real_content, GWL_EXSTYLE)
            ex2 |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
            ex2 &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(real_content, GWL_EXSTYLE, ex2)
            # 易读模式：LWA_ALPHA | LWA_COLORKEY，alpha = read_bg_opacity * 255
            # COLORKEY 区域（空行）全透明，有文字行通过 read_bg tag 显示半透明背景
            if self.cfg['read_mode']:
                read_alpha = int(max(0.0, self.cfg['read_bg_opacity']) * 255)
                user32.SetLayeredWindowAttributes(
                    self._content_hwnd, COLORKEY_INT, read_alpha,
                    LWA_ALPHA | LWA_COLORKEY)
            else:
                # LWA_ALPHA | LWA_COLORKEY：alpha 控制整体半透明，COLORKEY(#010101) 穿透
                user32.SetLayeredWindowAttributes(
                    self._content_hwnd, COLORKEY_INT, int(max(0.0, bg_op) * 255),
                    LWA_ALPHA | LWA_COLORKEY)

            # ===== topmost 设置（仅在配置变化时切换，避免冗余 z-order 重排）=====
            new_topmost = bool(self.cfg['topmost'])
            if bool(self.root.attributes('-topmost')) != new_topmost:
                self.root.attributes("-topmost", new_topmost)
                self.content_win.attributes("-topmost", new_topmost)
                if hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
                    self.panel.attributes("-topmost", new_topmost)
                # 标题栏同步 topmost
                if hasattr(self, 'titlebar_win') and self.titlebar_win and self.titlebar_win.winfo_exists():
                    self.titlebar_win.attributes("-topmost", new_topmost)
                # 状态栏同步 topmost
                if hasattr(self, 'statusbar_win') and self.statusbar_win and self.statusbar_win.winfo_exists():
                    self.statusbar_win.attributes("-topmost", new_topmost)

            # 标题栏外观同步（透明度/颜色）
            if hasattr(self, '_update_titlebar_appearance'):
                self._update_titlebar_appearance()
            # 状态栏外观同步（透明度/颜色）
            if hasattr(self, '_update_statusbar_appearance'):
                self._update_statusbar_appearance()

            if hasattr(self, '_taskbar_host') and self._taskbar_host:
                self._taskbar_host.sync()
        except Exception as e:
            print(f"[窗口样式] 设置失败: {e}")

    def _set_taskbar_visible(self, visible):
        """设置任务栏是否显示（不影响主窗口显示状态）"""
        self.cfg['show_taskbar'] = visible
        if hasattr(self, '_taskbar_host') and self._taskbar_host:
            self._taskbar_host.set_visible(visible)

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
        """同步内容窗口与根窗口的位置和大小。

        v2.9.7: content_win 位于 root 右侧（文本区），
        偏移量为手柄区域宽度（_get_handle_offset）。
        root 向上扩展了 root_y_offset，content_win 的 y 需要加上该偏移。

        v2.9.7.13: 隐写模式下高度由行数决定，不受 MIN_WINDOW_H 限制。
        """
        try:
            if hasattr(self, 'content_win') and self.content_win and self.content_win.winfo_exists():
                offset = self._get_handle_offset() if hasattr(self, '_get_handle_offset') else 0
                root_y_offset = self._get_handle_root_y_offset() if hasattr(self, '_get_handle_root_y_offset') else 0
                x = self.root.winfo_x() + offset
                y = self.root.winfo_y() + root_y_offset
                w = self.root.winfo_width() - offset
                h = self.root.winfo_height() - root_y_offset
                if w < MIN_WINDOW_W:
                    w = MIN_WINDOW_W
                # 隐写模式下高度由行数决定，不受 MIN_WINDOW_H 限制
                if not self.cfg.get('stealth_mode') and h < MIN_WINDOW_H:
                    h = MIN_WINDOW_H
                self.content_win.geometry(f"{w}x{h}+{x}+{y}")
                # 同步标题栏位置（跟随 content_win 移动）
                if hasattr(self, '_layout_titlebar'):
                    self._layout_titlebar()
                # 同步状态栏位置（跟随标题栏移动）
                if hasattr(self, '_layout_statusbar'):
                    self._layout_statusbar()
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
            offset = self._get_handle_offset() if hasattr(self, '_get_handle_offset') else 0
            root_y_offset = self._get_handle_root_y_offset() if hasattr(self, '_get_handle_root_y_offset') else 0
            self.cfg['window_width'] = self.root.winfo_width() - offset
            self.cfg['window_x'] = self.root.winfo_x() + offset
            self.cfg['window_y'] = self.root.winfo_y() + root_y_offset
            if not self.cfg.get('stealth_mode'):
                self.cfg['window_height'] = self.root.winfo_height() - root_y_offset
            self._save_config_debounced()

    def _on_focus_change(self):
        self._lift_all()
        self._update_handle()
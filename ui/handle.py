# -*- coding: utf-8 -*-
"""Stealth Note - 控制手柄模块（HandleMixin）"""
import tkinter as tk
from constants import *
from utils import mix_color, set_layered_transparent, invert_color


class HandleMixin:
    """控制手柄 Mixin：创建、渲染、热点、拖动、滚轮"""

    def _init_handle(self):
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        # 使用无父窗口的 Toplevel（parent=None），避免 root 的 COLORKEY 透明属性影响子窗口渲染
        self.handle_win = tk.Toplevel()
        self.handle_win.withdraw()
        self.handle_win.overrideredirect(True)
        self.handle_win.attributes("-topmost", True)

        # 手柄窗口使用 COLORKEY 色键透明 + SetWindowRgn 实现圆形
        # 非 COLORKEY 区域（绘制的圆环/实心圆）可见，COLORKEY 区域透明
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

        # 使用 LWA_COLORKEY 色键透明，alpha=255（完全不透明）
        # 手柄不透明度通过绘制颜色本身控制，不通过 LWA_ALPHA（避免黑底）
        set_layered_transparent(
            self._handle_hwnd, 255,
            use_colorkey=True, show_taskbar=False)

        self._set_handle_region(hs)

        self.root.after(200, self._show_handle)

        self.handle_canvas.bind("<Enter>", lambda e: self._on_handle_hover(True))
        self.handle_canvas.bind("<Leave>", lambda e: self._on_handle_hover(False))
        self.handle_canvas.bind("<ButtonPress-1>", self._on_handle_press)
        self.handle_canvas.bind("<B1-Motion>", self._on_handle_drag)
        self.handle_canvas.bind("<ButtonRelease-1>", self._on_handle_release)
        self.handle_canvas.bind("<MouseWheel>", self._on_handle_wheel)
        self.handle_canvas.bind("<Button-3>", self._show_handle_menu)
        self.handle_canvas.bind("<Button-2>", lambda e: self.toggle_stealth())

        self.handle_menu = tk.Menu(self.root, tearoff=0)
        self.handle_menu.add_command(label="显示/隐藏主窗口", command=self._tray_toggle)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="打开文件", command=self.file_open)
        self.handle_menu.add_command(label="保存文件", command=self.file_save)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(
            label="隐写模式" if not self.cfg.get('stealth_mode') else "退出隐写模式",
            command=self.toggle_stealth)
        self.handle_menu.add_separator()
        # 隐写行数选择：radiobutton 自带选中指示器，无需额外图标
        for lines, label in [(1, "一行模式"), (2, "两行模式"), (3, "三行模式")]:
            self.handle_menu.add_radiobutton(
                label=label,
                value=lines,
                variable=self._stealth_lines_var,
                command=lambda n=lines: self._set_stealth_lines(n))
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="反色显示", command=self.toggle_invert)
        self.handle_menu.add_command(label="易读模式", command=self.toggle_read)
        self.handle_menu.add_command(label="置顶模式", command=self.toggle_topmost)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="设置仪表盘", command=self.show_settings)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="关于", command=self._show_about)
        self.handle_menu.add_command(label="退出", command=self.exit_app)

    def _set_handle_region(self, hs=None):
        """设置手柄窗口为圆形区域。

        hs 参数直接传入窗口尺寸，避免读取 stale winfo_width/height
        导致裁剪圆心与绘制圆心错位。
        """
        try:
            if hs is None:
                hs = self.handle_win.winfo_width()
            if hs > 0:
                rgn = gdi32.CreateEllipticRgn(0, 0, hs, hs)
                user32.SetWindowRgn(self._handle_hwnd, rgn, True)
        except Exception as e:
            print(f"[手柄] 区域设置失败: {e}")

    def _show_handle(self):
        try:
            self.handle_win.deiconify()
            self.handle_win.lift()
            self._layout_handle()
            self._update_handle()
        except Exception as e:
            print(f"[手柄] 显示失败: {e}")

    def _layout_handle(self):
        # 取消之前的延迟布局，实现防抖（拖动期间避免频繁 winfo 调用）
        if hasattr(self, '_layout_handle_after_id') and self._layout_handle_after_id:
            try:
                self.root.after_cancel(self._layout_handle_after_id)
            except Exception:
                pass
        self._layout_handle_after_id = self.root.after(30, self._do_layout_handle)

    def _do_layout_handle(self):
        self._layout_handle_after_id = None
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        self.handle_win.geometry(f"{hs}x{hs}")
        self.handle_canvas.configure(width=hs, height=hs)

        wx = self.root.winfo_x()
        wy = self.root.winfo_y()
        size = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        r = size // 2

        # 手柄位于文本框/隐写框左侧，圆心固定（使用 HANDLE_REF_R 不随尺寸变化），X 方向间距 20px
        hx = wx - hs // 2 - HANDLE_REF_R - 20
        hy = wy + HANDLE_REF_R - hs // 2

        if hx < 0:
            hx = 0
        if hy < 0:
            hy = 0

        self.handle_win.geometry(f"+{hx}+{hy}")
        # 等待 geometry 生效后再设置圆形区域，避免 stale 尺寸导致圆心错位
        self.handle_win.update_idletasks()
        self.handle_win.lift()
        self._set_handle_region(hs)

    def _update_handle(self):
        self.handle_canvas.delete("all")
        size = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        color = self.cfg.get('handle_color', self.cfg['corner_color'])
        if self.cfg['invert_mode']:
            color = invert_color(color)

        # 不与 ROOT_BG 预乘，直接使用原始颜色。
        # handle_win 使用 LWA_COLORKEY 透明，COLORKEY 区域透明，
        # 非 COLORKEY 区域（绘制内容）完全不透明，无黑底。
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size'])) + HANDLE_WIN_PADDING * 2
        cx, cy = hs // 2, hs // 2
        r = size // 2

        focused = self.root.focus_get() in (self.text, self.stealth_text)

        if focused:
            # 获得焦点：实心圆 + 内部高亮细环 + 黑色外环
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=color, outline=color, width=2)
            self.handle_canvas.create_oval(
                cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4,
                outline=mix_color("#FFFFFF", 0.5, color), width=2)
            # 黑色外环：同圆心，半径比白色圆环大2px，便于在白色背景上识别
            self.handle_canvas.create_oval(
                cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                outline="#000000", width=1)
        else:
            # 未获得焦点：圆环 + 中心不可见填充（捕获鼠标事件）
            # 中心 fill="#010102" 仅比 COLORKEY(#010101) 多1位蓝色，
            # 肉眼不可辨，但非 COLORKEY 不会被 LWA_COLORKEY 透明化，能捕获鼠标事件。
            ring_w = 3
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color, width=ring_w, fill="")
            # 中心填充：用比 COLORKEY 多1位的颜色，视觉透明但捕获事件
            inner_r = max(1, r - ring_w)
            self.handle_canvas.create_oval(
                cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                fill="#010102", outline="")
            # 黑色外环：同圆心，半径比白色圆环大2px，便于在白色背景上识别
            self.handle_canvas.create_oval(
                cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                outline="#000000", width=1)

    def _on_handle_hover(self, entering):
        self._update_handle()

    def _show_handle_menu(self, event):
        try:
            label = "退出隐写模式" if self.cfg.get('stealth_mode') else "隐写模式"
            try:
                self.handle_menu.entryconfigure("隐写模式", label=label)
                self.handle_menu.entryconfigure("退出隐写模式", label=label)
            except Exception:
                pass
            self.handle_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.handle_menu.grab_release()

    def _on_handle_press(self, event):
        self._drag_active = True
        self._drag_dx = event.x_root - self.root.winfo_x()
        self._drag_dy = event.y_root - self.root.winfo_y()
        self._lift_all()
        if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
            self.stealth_text.focus_set()
        else:
            self.text.focus_set()
        self._update_handle()

    def _lift_all(self):
        """将所有窗口提到最上层"""
        try:
            user32.SetForegroundWindow(self._root_hwnd)
        except Exception:
            pass
        self.root.attributes("-topmost", True)
        self.content_win.attributes("-topmost", True)
        self.root.after(50, lambda: (
            self.root.attributes("-topmost", self.cfg['topmost']),
            self.content_win.attributes("-topmost", self.cfg['topmost'])
        ))
        self.root.lift()
        self.content_win.lift()
        self.handle_win.lift()
        if self.cfg['show_panel']:
            self.panel.attributes("-topmost", True)
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

    def _is_left_button_held(self):
        """检测鼠标左键是否按下"""
        try:
            return (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
        except Exception:
            return False

    def _is_ctrl_held(self):
        """检测 Ctrl 键是否按下"""
        try:
            return (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        except Exception:
            return False

    def _on_handle_wheel(self, event):
        """手柄滚轮：左键+滚轮→底色透明度，Ctrl+滚轮→底色透明度，直接滚轮→文字透明度"""
        delta = 1 if event.delta > 0 else -1
        if self._is_left_button_held() or self._is_ctrl_held():
            # 左键或Ctrl按下：仅调整底色透明度
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['bg_opacity']) > 0.001:
                self.cfg['bg_opacity'] = round(new_op, 2)
                self._apply_window_style()
                self._save_config_debounced()
        else:
            # 无修饰键：调整文字透明度
            new_op = max(0.1, min(1.0, self.cfg['text_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['text_opacity']) > 0.001:
                self.cfg['text_opacity'] = round(new_op, 2)
                self._apply_text_appearance()
                self._save_config_debounced()
        return "break"
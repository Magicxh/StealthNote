# -*- coding: utf-8 -*-
"""Stealth Note - 控制手柄模块（HandleMixin）"""
import tkinter as tk
from constants import *
from utils import mix_color, invert_color


class HandleMixin:
    """控制手柄 Mixin：创建、渲染、热点、拖动、滚轮

    v2.9.7 重构：手柄从独立 Toplevel 窗口改为 root 上的 Canvas 控件，
    彻底消除任务栏双窗口问题。root 窗口向左扩展以容纳手柄区域。
    """

    # -------------------------------------------------------------------------
    # 手柄尺寸计算
    # -------------------------------------------------------------------------

    def _get_handle_canvas_size(self):
        """计算手柄 Canvas 的边长（含 padding）"""
        hs = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        return hs + HANDLE_WIN_PADDING * 2

    def _get_handle_offset(self):
        """计算手柄区域宽度（root 左边缘到文本区左边缘的距离）"""
        return self._get_handle_canvas_size() // 2 + HANDLE_REF_R + 20

    def _get_handle_canvas_y(self):
        """计算手柄 Canvas 在 root 内的 Y 坐标（圆心对齐 HANDLE_REF_R）"""
        return HANDLE_REF_R - self._get_handle_canvas_size() // 2

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def _init_handle(self):
        """在 root 窗口上创建手柄 Canvas 控件"""
        cs = self._get_handle_canvas_size()

        self.handle_canvas = tk.Canvas(
            self.root, bg=COLORKEY, highlightthickness=0, bd=0,
            width=cs, height=cs, cursor="fleur")
        # 初始放在 root 左上角，_layout_handle 会调整位置
        self.handle_canvas.place(x=0, y=0)

        self.root.after(200, self._show_handle)

        self.handle_canvas.bind("<Enter>", lambda e: self._on_handle_hover(True))
        self.handle_canvas.bind("<Leave>", lambda e: self._on_handle_hover(False))
        self.handle_canvas.bind("<ButtonPress-1>", self._on_handle_press)
        self.handle_canvas.bind("<B1-Motion>", self._on_handle_drag)
        self.handle_canvas.bind("<ButtonRelease-1>", self._on_handle_release)
        self.handle_canvas.bind("<Double-Button-1>", self._on_handle_double_click)
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

    # -------------------------------------------------------------------------
    # 显示/布局
    # -------------------------------------------------------------------------

    def _show_handle(self):
        """显示手柄并布局"""
        try:
            self._layout_handle()
            self._update_handle()
        except Exception as e:
            print(f"[手柄] 显示失败: {e}")

    def _layout_handle(self):
        """布局手柄 Canvas 在 root 内的位置，并调整 root 窗口大小以容纳手柄区域"""
        if hasattr(self, '_layout_handle_after_id') and self._layout_handle_after_id:
            try:
                self.root.after_cancel(self._layout_handle_after_id)
            except Exception:
                pass
        self._layout_handle_after_id = self.root.after(30, self._do_layout_handle)

    def _do_layout_handle(self):
        self._layout_handle_after_id = None
        cs = self._get_handle_canvas_size()
        offset = self._get_handle_offset()
        canvas_y = self._get_handle_canvas_y()

        # 更新 Canvas 尺寸
        self.handle_canvas.configure(width=cs, height=cs)

        # 获取文本区位置和大小
        if getattr(self, '_text_hidden', False) and self._hidden_window_geo:
            text_x = self._hidden_window_geo[0]
            text_y = self._hidden_window_geo[1]
            text_w = self._hidden_window_geo[2]
        else:
            try:
                text_x = self.content_win.winfo_x()
                text_y = self.content_win.winfo_y()
                text_w = self.content_win.winfo_width()
            except Exception:
                return

        # root 位置和大小（文本区向左扩展 handle_offset）
        root_x = text_x - offset
        root_y = text_y
        root_w = max(text_w + offset, MIN_WINDOW_W + offset)
        root_h = self.root.winfo_height()

        if root_x < 0:
            root_x = 0
        if root_y < 0:
            root_y = 0

        self.root.geometry(f"{root_w}x{root_h}+{root_x}+{root_y}")

        # 手柄 Canvas 在 root 内的位置
        self.handle_canvas.place(x=0, y=canvas_y)

        self.root.update_idletasks()
        self._sync_content_window()
        self.handle_canvas.tk.call('raise', self.handle_canvas._w)
        self._update_handle()

    def _update_handle(self):
        """绘制手柄圆形"""
        self.handle_canvas.delete("all")
        size = max(MIN_HANDLE_SIZE, int(self.cfg['handle_size']))
        color = self.cfg.get('handle_color', self.cfg['corner_color'])
        if self.cfg['invert_mode']:
            color = invert_color(color)

        cs = self._get_handle_canvas_size()
        cx, cy = cs // 2, cs // 2
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
            self.handle_canvas.create_oval(
                cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                outline="#000000", width=1)
        else:
            # 未获得焦点：圆环 + 中心不可见填充（捕获鼠标事件）
            ring_w = 3
            self.handle_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color, width=ring_w, fill="")
            inner_r = max(1, r - ring_w)
            self.handle_canvas.create_oval(
                cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                fill="#010102", outline="")
            self.handle_canvas.create_oval(
                cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2,
                outline="#000000", width=1)

    def _on_handle_hover(self, entering):
        self._update_handle()

    # -------------------------------------------------------------------------
    # 右键菜单
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # 拖动
    # -------------------------------------------------------------------------

    def _on_handle_press(self, event):
        self._drag_active = True
        offset = self._get_handle_offset()
        self._drag_dx = event.x_root - (self.root.winfo_x() + offset)
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
        self.handle_canvas.tk.call('raise', self.handle_canvas._w)
        if self.cfg.get('show_panel') and hasattr(self, 'panel') and self.panel:
            self.panel.lift()

    def _on_handle_drag(self, event):
        if not self._drag_active:
            return
        offset = self._get_handle_offset()
        x = event.x_root - self._drag_dx  # 文本区 x
        y = event.y_root - self._drag_dy  # 文本区 y

        if getattr(self, '_text_hidden', False):
            # 更新隐藏窗口位置记录
            if hasattr(self, '_hidden_window_geo') and self._hidden_window_geo:
                w, h = self._hidden_window_geo[2], self._hidden_window_geo[3]
                self._hidden_window_geo = (x, y, w, h)
            # 移动仅手柄的 root 窗口
            cs = self._get_handle_canvas_size()
            handle_center_x = x - HANDLE_REF_R - 20
            handle_center_y = y + HANDLE_REF_R
            self.root.geometry(f"{cs}x{cs}+{handle_center_x - cs // 2}+{handle_center_y - cs // 2}")
        else:
            root_x = x - offset
            root_y = y
            self.root.geometry(f"+{root_x}+{root_y}")
            self._sync_content_window()

    def _on_handle_release(self, event):
        if self._drag_active:
            if getattr(self, '_text_hidden', False) and self._hidden_window_geo:
                self.cfg['window_x'] = self._hidden_window_geo[0]
                self.cfg['window_y'] = self._hidden_window_geo[1]
            else:
                offset = self._get_handle_offset()
                self.cfg['window_x'] = self.root.winfo_x() + offset
                self.cfg['window_y'] = self.root.winfo_y()
            self._save_config_debounced()
            self._drag_active = False

    def _on_handle_double_click(self, event):
        """双击手柄切换书写框隐藏/显示"""
        self._toggle_text_hidden()

    def _toggle_text_hidden(self):
        """切换书写框的隐藏/显示状态"""
        if not hasattr(self, '_text_hidden'):
            self._text_hidden = False
            self._hidden_window_geo = None

        if not self._text_hidden:
            offset = self._get_handle_offset()
            self._hidden_window_geo = (
                self.root.winfo_x() + offset,
                self.root.winfo_y(),
                self.content_win.winfo_width(),
                self.content_win.winfo_height()
            )
            self.root.withdraw()
            self.content_win.withdraw()
            self._text_hidden = True
            # 手柄是 root 的子控件，root.withdraw() 会隐藏手柄，需要重新显示 root
            # 但只显示手柄区域（缩小 root 到仅手柄大小）
            cs = self._get_handle_canvas_size()
            handle_center_x = self._hidden_window_geo[0] - HANDLE_REF_R - 20
            handle_center_y = self._hidden_window_geo[1] + HANDLE_REF_R
            self.root.geometry(f"{cs}x{cs}+{handle_center_x - cs // 2}+{handle_center_y - cs // 2}")
            self.handle_canvas.place(x=0, y=0)
            self.root.deiconify()
        else:
            offset = self._get_handle_offset()
            self.root.deiconify()
            self.content_win.deiconify()

            if self._hidden_window_geo:
                x, y, w, h = self._hidden_window_geo
                root_x = x - offset
                root_y = y
                root_w = w + offset
                root_h = h
                self.root.geometry(f"{root_w}x{root_h}+{root_x}+{root_y}")
                self.content_win.geometry(f"{w}x{h}+{x}+{y}")

            # 重新布局手柄
            canvas_y = self._get_handle_canvas_y()
            self.handle_canvas.place(x=0, y=canvas_y)

            self._sync_content_window()
            self._text_hidden = False
            self._force_foreground()
            self._focus_text()

    # -------------------------------------------------------------------------
    # 辅助
    # -------------------------------------------------------------------------

    def _is_left_button_held(self):
        try:
            return (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
        except Exception:
            return False

    def _is_ctrl_held(self):
        try:
            return (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        except Exception:
            return False

    def _on_handle_wheel(self, event):
        """手柄滚轮：左键+滚轮→底色透明度，Ctrl+滚轮→底色透明度，直接滚轮→文字透明度"""
        delta = 1 if event.delta > 0 else -1
        if self._is_left_button_held() or self._is_ctrl_held():
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['bg_opacity']) > 0.001:
                self.cfg['bg_opacity'] = round(new_op, 2)
                self._apply_window_style()
                self._save_config_debounced()
        else:
            new_op = max(0.1, min(1.0, self.cfg['text_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['text_opacity']) > 0.001:
                self.cfg['text_opacity'] = round(new_op, 2)
                self._apply_text_appearance()
                self._save_config_debounced()
        return "break"
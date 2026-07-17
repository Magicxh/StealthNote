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
        """计算手柄 Canvas 在 root 内的 Y 坐标（非负，确保 Canvas 完全在 root 内）"""
        return max(0, HANDLE_REF_R - self._get_handle_canvas_size() // 2)

    def _get_handle_root_y_offset(self):
        """root 窗口顶部需要向上扩展的高度（使圆心对齐文本区顶部+HANDLE_REF_R）"""
        return max(0, self._get_handle_canvas_size() // 2 - HANDLE_REF_R)

    # -------------------------------------------------------------------------
    # 初始化
    # -------------------------------------------------------------------------

    def _init_handle(self):
        """在 root 窗口上创建手柄 Canvas 控件"""
        # v2.9.8.4: 菜单复选框状态变量
        self._menu_panel_locked_var = tk.IntVar(value=1 if self.cfg.get('panel_locked', True) else 0)
        self._menu_adapt_bg_var = tk.IntVar(value=1 if self.cfg.get('adapt_bg', False) else 0)
        self._menu_light_mode_var = tk.IntVar(value=1 if self.cfg.get('theme_mode', 'dark') == 'light' else 0)

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
        # 双击手柄：仅在适配背景模式开启时绑定（toggle_adapt_bg 中动态控制）
        self.handle_canvas.bind("<MouseWheel>", self._on_handle_wheel)
        self.handle_canvas.bind("<Button-3>", self._on_handle_right_press)
        self.handle_canvas.bind("<ButtonRelease-3>", self._on_handle_right_release)
        self.handle_canvas.bind("<Button-2>", lambda e: self.toggle_stealth())

        self.handle_menu = tk.Menu(self.root, tearoff=0)
        self.handle_menu.add_command(label="显示/隐藏主窗口", command=self._tray_toggle)
        # v2.9.8.4: 锁定仪表板相对位置开关
        self.handle_menu.add_checkbutton(
            label="锁定仪表板相对位置",
            command=self._toggle_panel_locked,
            variable=self._menu_panel_locked_var)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="打开文件", command=self.file_open)
        self.handle_menu.add_command(label="保存文件", command=self.file_save)
        self.handle_menu.add_command(label="读取暂存", command=self._load_autosave)
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
        # v2.9.8.4: 适配背景开关（在反色显示上方）
        self.handle_menu.add_checkbutton(
            label="双击适配背景",
            command=self.toggle_adapt_bg,
            variable=self._menu_adapt_bg_var)
        self.handle_menu.add_separator()
        # v2.9.8.4: 深色/浅色模式切换（在反色显示上方）
        self.handle_menu.add_checkbutton(
            label="切换深色/浅色模式",
            command=self._toggle_theme_menu,
            variable=self._menu_light_mode_var)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="反色显示", command=self.toggle_invert)
        self.handle_menu.add_command(label="易读模式", command=self.toggle_read)
        self.handle_menu.add_command(label="置顶模式", command=self.toggle_topmost)
        self.handle_menu.add_separator()
        self.handle_menu.add_command(label="设置", command=self.show_settings)
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
        root_y_offset = self._get_handle_root_y_offset()

        # 更新 Canvas 尺寸
        self.handle_canvas.configure(width=cs, height=cs)

        # 获取文本区位置和大小
        try:
            text_x = self.content_win.winfo_x()
            text_y = self.content_win.winfo_y()
            text_w = self.content_win.winfo_width()
        except Exception:
            return

        # root 位置和大小（文本区向左扩展 handle_offset，向上扩展 root_y_offset）
        root_x = text_x - offset
        root_y = text_y - root_y_offset
        root_w = max(text_w + offset, MIN_WINDOW_W + offset)
        # 隐写模式下高度由行数决定，不能从 winfo_height 读旧值覆盖
        if self.cfg.get('stealth_mode'):
            try:
                root_h = self.content_win.winfo_height() + root_y_offset
            except Exception:
                root_h = self.root.winfo_height()
        else:
            root_h = self.root.winfo_height()

        if root_x < 0:
            root_x = 0
        if root_y < 0:
            root_y = 0

        # v2.9.7.3: geometry 去重 + 2px 容差，避免像素级抖动反复触发 geometry() → <Configure> 循环
        cur_x = self.root.winfo_x()
        cur_y = self.root.winfo_y()
        cur_w = self.root.winfo_width()
        cur_h = self.root.winfo_height()
        if (abs(cur_x - root_x) > 2 or abs(cur_y - root_y) > 2 or
                abs(cur_w - root_w) > 2 or abs(cur_h - root_h) > 2):
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
        # 应用 handle_opacity：与四角框线透明度处理方式一致
        raw_bg = self.cfg['bg_color']
        if self.cfg['invert_mode']:
            raw_bg = invert_color(raw_bg)
        color = mix_color(color, self.cfg.get('handle_opacity', 0.8), raw_bg)

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
            # 同步动态菜单项状态
            label = "退出隐写模式" if self.cfg.get('stealth_mode') else "隐写模式"
            try:
                self.handle_menu.entryconfigure("隐写模式", label=label)
                self.handle_menu.entryconfigure("退出隐写模式", label=label)
            except Exception:
                pass
            # v2.9.8.4: 同步复选框状态
            self._menu_panel_locked_var.set(1 if self.cfg.get('panel_locked', True) else 0)
            self._menu_adapt_bg_var.set(1 if self.cfg.get('adapt_bg', False) else 0)
            self._menu_light_mode_var.set(1 if self.cfg.get('theme_mode', 'dark') == 'light' else 0)
            self.handle_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.handle_menu.grab_release()

    # v2.9.8.4: 菜单切换相对位置锁定
    def _toggle_panel_locked(self):
        self.cfg['panel_locked'] = not self.cfg.get('panel_locked', True)
        self._menu_panel_locked_var.set(1 if self.cfg['panel_locked'] else 0)
        self._save_config_debounced()

    # v2.9.8.4: 菜单切换深色/浅色模式
    def _toggle_theme_menu(self):
        new_mode = "light" if self.cfg.get('theme_mode', 'dark') == 'dark' else 'dark'
        self.apply_theme(new_mode)
        self._menu_light_mode_var.set(1 if new_mode == 'light' else 0)

    # -------------------------------------------------------------------------
    # 拖动
    # -------------------------------------------------------------------------

    def _on_handle_press(self, event):
        self._drag_active = True
        offset = self._get_handle_offset()
        root_y_offset = self._get_handle_root_y_offset()
        self._drag_dx = event.x_root - (self.root.winfo_x() + offset)
        self._drag_dy = event.y_root - (self.root.winfo_y() + root_y_offset)
        # v2.9.8.3: 相对位置锁定时记录仪表盘与 root 的偏移，联动移动
        if self.cfg.get('panel_locked') and hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
            self._panel_drag_dx_handle = self.panel.winfo_x() - self.root.winfo_x()
            self._panel_drag_dy_handle = self.panel.winfo_y() - self.root.winfo_y()
        else:
            self._panel_drag_dx_handle = None
            self._panel_drag_dy_handle = None
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
        # 50ms后恢复topmost到配置值，避免永久置顶
        self.root.after(50, lambda: (
            self.root.attributes("-topmost", self.cfg.get('topmost')),
            self.content_win.attributes("-topmost", self.cfg.get('topmost'))
        ))
        self.root.lift()
        self.content_win.lift()
        self.handle_canvas.tk.call('raise', self.handle_canvas._w)
        if self.cfg.get('show_panel') and hasattr(self, 'panel') and self.panel:
            self.panel.lift()
        # 标题栏同步提升
        if hasattr(self, 'titlebar_win') and self.titlebar_win and self.titlebar_win.winfo_exists():
            self.titlebar_win.lift()
        # 状态栏同步提升
        if hasattr(self, 'statusbar_win') and self.statusbar_win and self.statusbar_win.winfo_exists():
            self.statusbar_win.lift()

    def _on_handle_drag(self, event):
        if not self._drag_active:
            return
        offset = self._get_handle_offset()
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        root_x = x - offset
        root_y = y - self._get_handle_root_y_offset()
        self.root.geometry(f"+{root_x}+{root_y}")
        self._sync_content_window()
        # v2.9.8.3: 相对位置锁定时联动移动仪表盘
        if (self.cfg.get('panel_locked') and hasattr(self, 'panel')
                and self.panel and self.panel.winfo_exists()
                and self._panel_drag_dx_handle is not None):
            new_px = root_x + self._panel_drag_dx_handle
            new_py = root_y + self._panel_drag_dy_handle
            self.panel.geometry(f"+{new_px}+{new_py}")

    def _on_handle_release(self, event):
        if self._drag_active:
            offset = self._get_handle_offset()
            root_y_offset = self._get_handle_root_y_offset()
            self.cfg['window_x'] = self.root.winfo_x() + offset
            self.cfg['window_y'] = self.root.winfo_y() + root_y_offset
            # v2.9.8.3: 相对位置锁定时同步保存仪表盘位置
            if self.cfg.get('panel_locked') and hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
                self.cfg['panel_x'] = self.panel.winfo_x()
                self.cfg['panel_y'] = self.panel.winfo_y()
            self._save_config_debounced()
            self._drag_active = False

    def _on_handle_double_click(self, event):
        """双击手柄：仅在适配背景模式开启时触发取色并自适应文本背景/文字颜色。

        关键：立即重置 _drag_active=False，防止双击序列中的 press 状态
        与后续拖动事件冲突导致假死。用 after() 延迟执行取色，让待处理的
        release 事件先完成。
        """
        self._drag_active = False
        self.root.after(10, self._do_adapt_bg_perform)

    def _do_adapt_bg_perform(self):
        """延迟执行取色，避免与双击事件序列冲突"""
        if not self.cfg.get('adapt_bg', False):
            return
        if hasattr(self, '_adapt_bg_perform'):
            self._adapt_bg_perform()

    # -------------------------------------------------------------------------
    # 辅助
    # -------------------------------------------------------------------------

    def _apply_window_style_debounced(self):
        """防抖调用 _apply_window_style，避免滚轮快速调节时闪烁"""
        if hasattr(self, '_apply_style_after_id') and self._apply_style_after_id:
            try:
                self.root.after_cancel(self._apply_style_after_id)
            except Exception:
                pass
        self._apply_style_after_id = self.root.after(30, self._do_apply_window_style)

    def _do_apply_window_style(self):
        self._apply_style_after_id = None
        self._apply_window_style()

    def _apply_text_appearance_debounced(self):
        """防抖调用 _apply_text_appearance，避免滚轮快速调节时闪烁"""
        if hasattr(self, '_apply_text_after_id') and self._apply_text_after_id:
            try:
                self.root.after_cancel(self._apply_text_after_id)
            except Exception:
                pass
        self._apply_text_after_id = self.root.after(30, self._do_apply_text_appearance)

    def _do_apply_text_appearance(self):
        self._apply_text_after_id = None
        self._apply_text_appearance()

    def _is_left_button_held(self):
        try:
            return (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
        except Exception:
            return False

    def _is_right_button_held(self):
        try:
            return (user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000) != 0
        except Exception:
            return False

    def _is_ctrl_held(self):
        try:
            return (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        except Exception:
            return False

    def _on_handle_right_press(self, event):
        """右键按下：记录状态，不立即弹菜单（等待释放时决定）"""
        self._right_button_wheel_used = False

    def _on_handle_right_release(self, event):
        """右键释放：如果期间没有滚轮操作，弹出菜单"""
        if not getattr(self, '_right_button_wheel_used', False):
            self._show_handle_menu(event)

    def _on_handle_wheel(self, event):
        """手柄滚轮：右键+滚轮→底色透明度，Ctrl+滚轮→底色透明度，直接滚轮→文字透明度，左键+滚轮→屏蔽"""
        # 左键按下时屏蔽滚轮（左键用于拖动手柄，滚轮不应干扰）
        if self._is_left_button_held():
            return "break"
        delta = 1 if event.delta > 0 else -1
        if self._is_right_button_held() or self._is_ctrl_held():
            self._right_button_wheel_used = True
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['bg_opacity']) > 0.001:
                self.cfg['bg_opacity'] = round(new_op, 2)
                self._apply_window_style_debounced()
                self._save_config_debounced()
        else:
            new_op = max(0.1, min(1.0, self.cfg['text_opacity'] + delta * 0.08))
            if abs(new_op - self.cfg['text_opacity']) > 0.001:
                self.cfg['text_opacity'] = round(new_op, 2)
                self._apply_text_appearance_debounced()
                # 同步标题栏/状态栏文字颜色
                if hasattr(self, '_update_titlebar_appearance'):
                    self._update_titlebar_appearance()
                if hasattr(self, '_update_statusbar_appearance'):
                    self._update_statusbar_appearance()
                self._save_config_debounced()
        return "break"
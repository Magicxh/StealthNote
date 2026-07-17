# -*- coding: utf-8 -*-
"""Stealth Note - 仪表盘模块（PanelMixin）"""
import tkinter as tk
import os
from constants import *
from utils import mix_color, invert_color, set_layered_transparent

class PanelMixin:
    """仪表盘 Mixin：按钮、小红点、面板拖动、样式"""
    
    def _init_panel(self):
        self.panel = tk.Toplevel(self.root)
        self.panel.withdraw()
        self.panel.overrideredirect(True)

        # 仪表盘使用色键 #010101 实现透明区域
        self.panel.configure(bg=COLORKEY)

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.panel.iconbitmap(self.icon_path)
            except Exception:
                pass

        if self.cfg['panel_x'] is None or self.cfg['panel_y'] is None:
            # v2.9.8.3: 首次启动位置——与标题栏保持相同间距 TITLEBAR_GAP，
            # 左边缘与文本框左边缘对齐（避免与标题栏/状态栏重叠）
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            # 文本框居中位置
            text_x = (sw - max(MIN_WINDOW_W, int(self.cfg['window_width']))) // 2
            text_y = (sh - max(MIN_WINDOW_H, int(self.cfg['window_height']))) // 2
            # 标题栏顶部 y = 文本框 y - TITLEBAR_HEIGHT - TITLEBAR_GAP
            titlebar_top_y = text_y - TITLEBAR_HEIGHT - TITLEBAR_GAP
            # 仪表盘顶部 y = 标题栏顶部 y - PANEL_HEIGHT - TITLEBAR_GAP（与标题栏同间距）
            py = titlebar_top_y - PANEL_HEIGHT - TITLEBAR_GAP
            # 仪表盘左边缘与文本框左边缘对齐
            px = text_x
            if py < 0:
                py = 0
        else:
            px = int(self.cfg['panel_x'])
            py = int(self.cfg['panel_y'])

        self.panel.geometry(f"{PANEL_WIDTH}x{PANEL_HEIGHT}+{px}+{py}")
        self.panel.update_idletasks()
        self._panel_hwnd = self.panel.winfo_id()

        # v2.9.7: 在 set_layered_transparent（调用SetWindowPos）之前设置所有者
        self._set_window_owner(self._panel_hwnd, self._host_hwnd)

        set_layered_transparent(
            self._panel_hwnd,
            int(max(MIN_PANEL_OPACITY, self.cfg['panel_opacity']) * 255),
            use_colorkey=True,
            show_taskbar=False)

        self.panel_outer = tk.Frame(self.panel, bg="#444444", bd=0)
        self.panel_outer.pack(fill="both", expand=True, padx=PANEL_PADDING, pady=PANEL_PADDING)

        self.panel_inner = tk.Frame(self.panel_outer, bg=self.cfg['panel_bg_color'])
        self.panel_inner.pack(fill="both", expand=True)

        btn_color_14 = "#333333"
        btn_color_58 = "#3d3d3d"
        btn_color_x = "#2a2a2a"
        btn_color_drag = "#ff8800"

        buttons = [
            ("N",   "新建文件\nCtrl+N",       self.file_new,       btn_color_14, False),
            ("O",   "打开文件\nCtrl+O",       self.file_open,      btn_color_14, False),
            ("S",   "保存文件\nCtrl+S",       self.file_save,      btn_color_14, False),
            ("SN",  "另存为\nCtrl+Shift+S",   self.file_save_as,   btn_color_14, False),
            ("隐",  "隐写模式\n中键切换",     self.toggle_stealth, btn_color_58, "stealth_mode"),
            ("适",  "适配背景",               self.toggle_adapt_bg, btn_color_58, "adapt_bg"),
            ("反",  "反色显示\nCtrl+F",       self.toggle_invert,  btn_color_58, "invert_mode"),
            ("易",  "易读模式\nCtrl+Shift+R", self.toggle_read,    btn_color_58, "read_mode"),
            ("顶",  "置顶模式\nCtrl+T",       self.toggle_topmost, btn_color_58, "topmost"),
            ("色",  "主题切换\nCtrl+M",       self.toggle_theme,   btn_color_58, "theme_light"),
            ("控",  "设置仪表盘\nCtrl+K",     self.show_settings,  btn_color_58, False),
            ("X",   "退出程序",               self.exit_app,       btn_color_x,  False),
        ]

        self.panel_buttons = {}
        self.panel_button_containers = {}
        self.panel_button_dots = {}
        # 按钮正式名称映射（用于tooltip，取tip第一行去掉快捷键部分）
        self._panel_btn_names = {}
        self._tip_after_id = None
        self._tip_window = None
        for i, (text, tip, cmd, bg, state_key) in enumerate(buttons):
            container = tk.Frame(self.panel_inner, bg=bg, width=PANEL_BTN_SIZE, height=PANEL_BTN_SIZE)
            container.pack_propagate(False)
            container.grid(row=0, column=i, padx=PANEL_BTN_GAP//2, pady=0)
            self.panel_button_containers[text] = container
            # 提取正式名称（tip第一行，去掉换行后的快捷键部分）
            formal_name = tip.split('\n')[0].strip()
            self._panel_btn_names[text] = formal_name

            if text == "色":
                # "色"按钮用 Canvas 绘制黑白对角三角形图案
                btn = tk.Canvas(
                    container,
                    bg=bg,
                    highlightthickness=0,
                    bd=0,
                    cursor="hand2"
                )
                btn.pack(fill="both", expand=True)
                self._draw_theme_icon(btn, bg)
                btn.bind("<Button-1>", lambda e, c=cmd: c())
                btn.bind("<Enter>", lambda e, w=btn, b=bg, t=text: self._on_btn_enter(w, b, t))
                btn.bind("<Leave>", lambda e, w=btn, b=bg, t=text: self._on_btn_leave(w, b, t))
            elif text == "适":
                # "适"按钮用 Canvas 绘制圆形框线+十字图案（黑底白线）
                btn = tk.Canvas(
                    container,
                    bg=bg,
                    highlightthickness=0,
                    bd=0,
                    cursor="hand2"
                )
                btn.pack(fill="both", expand=True)
                self._draw_adapt_icon(btn, bg)
                btn.bind("<Button-1>", lambda e, c=cmd: c())
                btn.bind("<Enter>", lambda e, w=btn, b=bg, t=text: self._on_btn_enter(w, b, t))
                btn.bind("<Leave>", lambda e, w=btn, b=bg, t=text: self._on_btn_leave(w, b, t))
            else:
                btn = tk.Button(
                    container,
                    text=text,
                    command=cmd,
                    bg=bg,
                    fg="#ffffff",
                    font=("Microsoft YaHei UI", 9, "bold"),
                    bd=0,
                    relief="flat",
                    activebackground="#555555",
                    activeforeground="#ffffff",
                    cursor="hand2"
                )
                btn.pack(fill="both", expand=True)
                btn.bind("<Enter>", lambda e, w=btn, t=text: self._schedule_show_tip(w, t))
                btn.bind("<Leave>", lambda e: self._hide_tip())
            self.panel_buttons[text] = btn

        # 仪表盘开关小红点：Label+text="●"+fg="#ff3333"
        # Label 作为 container 子控件，place 定位到按钮右上角
        for text, key in [("隐", "stealth_mode"), ("适", "adapt_bg"),
                          ("反", "invert_mode"), ("易", "read_mode"),
                          ("顶", "topmost"), ("色", "theme_light")]:
            container = self.panel_button_containers[text]
            container_bg = container.cget("bg")
            dot_label = tk.Label(container, text="●", fg="#ff3333", bg=container_bg,
                                 font=("Microsoft YaHei UI", 7, "bold"),
                                 highlightthickness=0, bd=0)
            dot_label.bind("<Button-1>", lambda e, t=text: self.panel_buttons[t].invoke())
            dot_label.place_forget()
            self.panel_button_dots[text] = dot_label

        # 拖动按钮
        drag_container = tk.Frame(self.panel_inner, bg=btn_color_drag,
                                  width=PANEL_BTN_SIZE, height=PANEL_BTN_SIZE)
        drag_container.pack_propagate(False)
        drag_container.grid(row=0, column=len(buttons), padx=PANEL_BTN_GAP//2, pady=0)
        drag_btn = tk.Label(drag_container, text="⋮⋮", bg=btn_color_drag, fg="#ffffff",
                            font=("Microsoft YaHei UI", 9, "bold"), cursor="fleur")
        drag_btn.pack(fill="both", expand=True)
        drag_btn.bind("<ButtonPress-1>", self._on_panel_press)
        drag_btn.bind("<B1-Motion>", self._on_panel_drag)
        drag_btn.bind("<ButtonRelease-1>", self._on_panel_release)
        drag_btn.bind("<Enter>", lambda e, w=drag_btn: self._schedule_show_tip(w, "⋮⋮"))
        drag_btn.bind("<Leave>", lambda e: self._hide_tip())
        self._panel_btn_names["⋮⋮"] = "拖动仪表盘"

        # 整体拖动
        self.panel_outer.bind("<ButtonPress-1>", self._on_panel_press)
        self.panel_outer.bind("<B1-Motion>", self._on_panel_drag)
        self.panel_outer.bind("<ButtonRelease-1>", self._on_panel_release)
        self.panel_inner.bind("<ButtonPress-1>", self._on_panel_press)
        self.panel_inner.bind("<B1-Motion>", self._on_panel_drag)
        self.panel_inner.bind("<ButtonRelease-1>", self._on_panel_release)

        if self.cfg['show_panel']:
            self.panel.deiconify()
        else:
            self.panel.withdraw()

        # 初始化小红点状态：根据当前 cfg 显示/隐藏各开关指示灯
        self._update_panel_button_states()

    def _update_panel_button_states(self):
        """统一刷新仪表盘开关小红点，状态与 cfg 严格对应。

        _apply_window_style() 的 Win32 API 调用会触发异步窗口重绘，
        需要多次延迟 lift 确保红点始终在按钮之上。
        """
        dot_map = {
            "隐": "stealth_mode",
            "反": "invert_mode",
            "易": "read_mode",
            "顶": "topmost",
            "色": "theme_light",
            "适": "adapt_bg",
        }
        pending_lift = []
        for text, key in dot_map.items():
            if key == "theme_light":
                enabled = self.cfg.get('theme_mode', 'dark') == 'light'
            else:
                enabled = bool(self.cfg.get(key, False))
            dot = self.panel_button_dots.get(text)
            if dot and dot.winfo_exists():
                if enabled:
                    dot.place(x=PANEL_BTN_SIZE - 4, y=1, anchor="ne")
                    pending_lift.append(dot)
                else:
                    dot.place_forget()
        try:
            self.panel.update_idletasks()
        except Exception:
            pass
        # 多次延迟 lift，覆盖 Win32 异步重绘
        for dot in pending_lift:
            try:
                dot.lift()
            except Exception:
                pass
        if pending_lift:
            self.root.after(30, lambda: self._lift_dots(pending_lift))
            self.root.after(100, lambda: self._lift_dots(pending_lift))

    def _lift_dots(self, dots):
        """延迟 lift 小红点，覆盖 Win32 异步重绘"""
        for dot in dots:
            try:
                if dot.winfo_exists():
                    dot.lift()
            except Exception:
                pass

    def _on_panel_press(self, event):
        # v2.9.8.5: panel 销毁后不执行
        if not (hasattr(self, 'panel') and self.panel and self.panel.winfo_exists()):
            return
        try:
            self._panel_drag_active = True
            self._panel_drag_dx = event.x_root - self.panel.winfo_x()
            self._panel_drag_dy = event.y_root - self.panel.winfo_y()
            # v2.9.8.3: 相对位置锁定时记录 root 与 panel 的偏移，联动移动
            if self.cfg.get('panel_locked') and hasattr(self, 'root') and self.root:
                self._root_drag_dx_panel = self.root.winfo_x() - self.panel.winfo_x()
                self._root_drag_dy_panel = self.root.winfo_y() - self.panel.winfo_y()
            else:
                self._root_drag_dx_panel = None
                self._root_drag_dy_panel = None
            self.panel.lift()
        except Exception as e:
            print(f"[仪表盘] 拖动开始失败: {e}")
            self._panel_drag_active = False

    def _on_panel_drag(self, event):
        if not self._panel_drag_active:
            return
        # v2.9.8.5: panel/root 销毁后不执行
        if not (hasattr(self, 'panel') and self.panel and self.panel.winfo_exists()):
            self._panel_drag_active = False
            return
        try:
            x = event.x_root - self._panel_drag_dx
            y = event.y_root - self._panel_drag_dy
            self.panel.geometry(f"+{x}+{y}")
            # v2.9.8.3: 相对位置锁定时联动移动 root（会自动同步 content_win/标题栏/状态栏）
            if (self.cfg.get('panel_locked') and hasattr(self, 'root') and self.root
                    and self.root.winfo_exists() and self._root_drag_dx_panel is not None):
                new_rx = x + self._root_drag_dx_panel
                new_ry = y + self._root_drag_dy_panel
                self.root.geometry(f"+{new_rx}+{new_ry}")
                self._sync_content_window()
        except Exception as e:
            print(f"[仪表盘] 拖动失败: {e}")
            self._panel_drag_active = False

    def _on_panel_release(self, event):
        if self._panel_drag_active:
            try:
                # v2.9.8.5: panel 销毁后不读取坐标
                if not (hasattr(self, 'panel') and self.panel and self.panel.winfo_exists()):
                    self._panel_drag_active = False
                    return
                self.cfg['panel_x'] = self.panel.winfo_x()
                self.cfg['panel_y'] = self.panel.winfo_y()
                # v2.9.8.3: 相对位置锁定时同步保存 root 位置（window_x/y 为文本框坐标）
                if self.cfg.get('panel_locked') and hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    offset = self._get_handle_offset() if hasattr(self, '_get_handle_offset') else 0
                    root_y_offset = self._get_handle_root_y_offset() if hasattr(self, '_get_handle_root_y_offset') else 0
                    self.cfg['window_x'] = self.root.winfo_x() + offset
                    self.cfg['window_y'] = self.root.winfo_y() + root_y_offset
                self._save_config_debounced()
            except Exception as e:
                print(f"[仪表盘] 拖动结束失败: {e}")
            finally:
                self._panel_drag_active = False

    # -------------------------------------------------------------------------
    # 按钮悬停 Tooltip
    # -------------------------------------------------------------------------

    def _on_btn_enter(self, widget, bg_color, btn_text):
        """Canvas按钮（色/适）的Enter事件：高亮背景+调度tooltip"""
        widget.configure(bg="#555555")
        self._schedule_show_tip(widget, btn_text)

    def _on_btn_leave(self, widget, bg_color, btn_text):
        """Canvas按钮（色/适）的Leave事件：恢复图案+隐藏tooltip"""
        if btn_text == "色":
            self._draw_theme_icon(widget, bg_color)
        elif btn_text == "适":
            self._draw_adapt_icon(widget, bg_color)
        else:
            widget.configure(bg=bg_color)
        self._hide_tip()

    def _schedule_show_tip(self, widget, btn_text):
        """调度0.5秒后显示tooltip，若期间离开则取消"""
        self._cancel_tip_schedule()
        name = self._panel_btn_names.get(btn_text, btn_text)
        self._tip_after_id = self.panel.after(500, lambda: self._show_tip(widget, name))

    def _cancel_tip_schedule(self):
        """取消待显示的tooltip调度"""
        if self._tip_after_id is not None:
            try:
                self.panel.after_cancel(self._tip_after_id)
            except Exception:
                pass
            self._tip_after_id = None

    def _show_tip(self, widget, text):
        """显示tooltip窗口，定位到按钮上方"""
        self._tip_after_id = None
        self._hide_tip()
        if not hasattr(self, 'panel') or not self.panel or not self.panel.winfo_exists():
            return
        if not widget or not widget.winfo_exists():
            return
        try:
            tip = tk.Toplevel(self.panel)
            tip.overrideredirect(True)
            tip.configure(bg="#ffffe0")
            label = tk.Label(tip, text=text, bg="#ffffe0", fg="#000000",
                             font=("Microsoft YaHei UI", 9), padx=6, pady=2)
            label.pack()
            tip.update_idletasks()
            tw = tip.winfo_width()
            th = tip.winfo_height()
            # 定位到按钮上方居中
            bx = widget.winfo_rootx()
            by = widget.winfo_rooty()
            bw = widget.winfo_width()
            mx = bx + (bw - tw) // 2
            my = by - th - 4
            # 边界保护：上方空间不足时改为显示在按钮下方
            if my < 0:
                my = by + widget.winfo_height() + 4
            sw = tip.winfo_screenwidth()
            if mx + tw > sw:
                mx = sw - tw - 4
            if mx < 0:
                mx = 0
            tip.geometry(f"+{mx}+{my}")
            self._tip_window = tip
        except Exception:
            self._tip_window = None

    def _hide_tip(self):
        """隐藏并销毁tooltip窗口，取消调度"""
        self._cancel_tip_schedule()
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None

    def toggle_panel(self):
        self.cfg['show_panel'] = not self.cfg['show_panel']
        if self.cfg['show_panel']:
            self.panel.deiconify()
            self.panel.lift()
        else:
            self._hide_tip()
            self.panel.withdraw()
        self._save_config_debounced()

    def toggle_invert(self):
        self.cfg['invert_mode'] = not self.cfg['invert_mode']
        self._apply_window_style()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        if hasattr(self, '_refresh_titlebar'):
            self._refresh_titlebar()
        if hasattr(self, '_refresh_statusbar'):
            self._refresh_statusbar()
        self._save_config_debounced()

    def toggle_read(self):
        self.cfg['read_mode'] = not self.cfg['read_mode']
        self._apply_window_style()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        if hasattr(self, '_refresh_titlebar'):
            self._refresh_titlebar()
        if hasattr(self, '_refresh_statusbar'):
            self._refresh_statusbar()
        self._save_config_debounced()

    def toggle_topmost(self):
        self.cfg['topmost'] = not self.cfg['topmost']
        self.root.attributes("-topmost", self.cfg['topmost'])
        self.content_win.attributes("-topmost", self.cfg['topmost'])
        if hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
            self.panel.attributes("-topmost", self.cfg['topmost'])
        if self.cfg['topmost']:
            self.root.lift()
            self.content_win.lift()
            if hasattr(self, 'panel') and self.panel and self.cfg.get('show_panel'):
                self.panel.lift()
        self._update_panel_button_states()
        self._save_config_debounced()

    def apply_theme(self, mode):
        """切换深色/浅色模式，应用预设配色并刷新界面。

        通过让控件颜色与背景颜色保持一致（深底白字 / 白底黑字），
        减少文字抗锯齿在不同背景上产生的彩色/亮色毛边。
        主题模式目前与反色模式独立，未来可按指令替代反色模式。
        """
        mode = mode if mode in THEME_PALETTES else "dark"
        self.cfg['theme_mode'] = mode
        palette = THEME_PALETTES[mode]
        for key, value in palette.items():
            self.cfg[key] = value

        self._apply_window_style()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        # v2.9.8.4: 同步菜单主题复选框状态
        if hasattr(self, '_menu_light_mode_var'):
            self._menu_light_mode_var.set(1 if self.cfg.get('theme_mode', 'dark') == 'light' else 0)
        self._save_config_debounced()

    def _apply_panel_style(self):
        """应用仪表盘外观（背景色 + 透明度）。"""
        try:
            if hasattr(self, 'panel_inner') and self.panel_inner:
                self.panel_inner.configure(bg=self.cfg['panel_bg_color'])
            if hasattr(self, 'panel') and self.panel and self.panel.winfo_exists():
                if not hasattr(self, '_panel_hwnd') or not self._panel_hwnd:
                    self._panel_hwnd = self.panel.winfo_id()
                alpha = int(max(MIN_PANEL_OPACITY, self.cfg['panel_opacity']) * 255)
                set_layered_transparent(self._panel_hwnd, alpha, use_colorkey=True, show_taskbar=False)
        except Exception as e:
            print(f"[仪表盘样式] 应用失败: {e}")

    def toggle_theme(self):
        """仪表盘按钮：在深色/浅色模式间切换。"""
        new_mode = "light" if self.cfg.get('theme_mode', 'dark') == 'dark' else 'dark'
        self.apply_theme(new_mode)

    def _draw_theme_icon(self, canvas, bg_color):
        """在"色"按钮 Canvas 上绘制黑白对角三角形图案。

        正方形线框 + 左下到右上的对角线，左上三角形填充白色，右下三角形填充黑色。
        图案高度与 9pt 文字等高（约 12px）。
        """
        canvas.delete("all")
        canvas.configure(bg=bg_color)
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = PANEL_BTN_SIZE
        if h <= 1:
            h = PANEL_BTN_SIZE
        # 图案尺寸：与文字等高，居中
        icon_size = 14
        cx = w // 2
        cy = h // 2
        x0 = cx - icon_size // 2
        y0 = cy - icon_size // 2
        x1 = cx + icon_size // 2
        y1 = cy + icon_size // 2
        # 左上三角形（白色填充）：左上角、右上角、左下角
        canvas.create_polygon(x0, y0, x1, y0, x0, y1, fill="#ffffff", outline="#ffffff")
        # 右下三角形（黑色填充）：右上角、右下角、左下角
        canvas.create_polygon(x1, y0, x1, y1, x0, y1, fill="#000000", outline="#000000")
        # 正方形线框
        canvas.create_rectangle(x0, y0, x1, y1, outline="#888888", width=1)

    def _draw_adapt_icon(self, canvas, bg_color):
        """在"适"按钮 Canvas 上绘制圆形框线+十字图案（黑底白线）。

        图案：黑色填充圆 + 白色圆框 + 白色十字（水平线+垂直线）。
        图案高度与 9pt 文字等高（约 14px）。
        """
        canvas.delete("all")
        canvas.configure(bg=bg_color)
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = PANEL_BTN_SIZE
        if h <= 1:
            h = PANEL_BTN_SIZE
        icon_size = 14
        cx = w // 2
        cy = h // 2
        r = icon_size // 2
        x0 = cx - r
        y0 = cy - r
        x1 = cx + r
        y1 = cy + r
        # 黑色填充圆（圆形底色）
        canvas.create_oval(x0, y0, x1, y1, fill="#000000", outline="#ffffff", width=1)
        # 白色十字：水平线 + 垂直线
        canvas.create_line(x0 + 2, cy, x1 - 2, cy, fill="#ffffff", width=1)
        canvas.create_line(cx, y0 + 2, cx, y1 - 2, fill="#ffffff", width=1)

    def toggle_adapt_bg(self):
        """切换适配背景模式。

        开启时：
        1. 记忆当前颜色/透明度值（_adapt_bg_saved）
        2. 绑定双击手柄事件
        3. 若存在上次适配状态（_adapt_bg_last），恢复到该状态
        4. 否则等待双击手柄取色

        关闭时：
        1. 解绑双击手柄事件（彻底消除双击检测延迟）
        2. 恢复到开启前记忆的状态（_adapt_bg_saved）
        3. 保留 _adapt_bg_last 供下次开启恢复
        """
        self.cfg['adapt_bg'] = not self.cfg.get('adapt_bg', False)
        if self.cfg['adapt_bg']:
            # 开启：记忆当前状态
            self._adapt_bg_saved = {
                'bg_color': self.cfg['bg_color'],
                'text_color': self.cfg['text_color'],
                'bg_opacity': self.cfg['bg_opacity'],
            }
            # 绑定双击事件
            self.handle_canvas.bind("<Double-Button-1>", self._on_handle_double_click)
            # 若有上次适配状态，恢复
            if hasattr(self, '_adapt_bg_last') and self._adapt_bg_last:
                last = self._adapt_bg_last
                self.cfg['bg_color'] = last['bg_color']
                self.cfg['text_color'] = last['text_color']
                self.cfg['bg_opacity'] = last['bg_opacity']
                self._apply_window_style()
                self._apply_text_appearance()
        else:
            # 关闭：解绑双击事件（彻底消除双击检测延迟）
            self.handle_canvas.unbind("<Double-Button-1>")
            # 恢复到开启前状态
            if hasattr(self, '_adapt_bg_saved') and self._adapt_bg_saved:
                saved = self._adapt_bg_saved
                self.cfg['bg_color'] = saved['bg_color']
                self.cfg['text_color'] = saved['text_color']
                self.cfg['bg_opacity'] = saved['bg_opacity']
                self._apply_window_style()
                self._apply_text_appearance()
        self._update_panel_button_states()
        # v2.9.8.4: 同步菜单复选框状态
        if hasattr(self, '_menu_adapt_bg_var'):
            self._menu_adapt_bg_var.set(1 if self.cfg.get('adapt_bg', False) else 0)
        self._save_config_debounced()

    def _adapt_bg_perform(self):
        """双击手柄触发的取色与自适应（仅在 adapt_bg 开启时调用）。

        分两步执行以避免取到手柄自身颜色：
        Step 1: 临时隐藏手柄 Canvas，记录屏幕坐标，用 after(30) 等待屏幕重绘
        Step 2: 取色 → 计算文字颜色 → 应用 → 恢复手柄
        """
        if not self.cfg.get('adapt_bg', False):
            return
        # 重入保护：防止快速多次双击导致多次取色
        if getattr(self, '_adapt_bg_in_progress', False):
            return
        self._adapt_bg_in_progress = True
        try:
            # 记录手柄中心在屏幕上的坐标
            handle_cs = self._get_handle_canvas_size()
            self._adapt_sample_cx = self.root.winfo_x() + handle_cs // 2
            self._adapt_sample_cy = self.root.winfo_y() + self._get_handle_canvas_y() + handle_cs // 2
            # 临时隐藏手柄 Canvas，避免取到手柄自身颜色
            self.handle_canvas.place_forget()
            self.root.update_idletasks()
            # 等待屏幕重绘后取色
            self.root.after(30, self._adapt_bg_sample_and_apply)
        except Exception as e:
            print(f"[适配背景] 取色启动失败: {e}")
            # 出错时恢复手柄
            self._adapt_bg_in_progress = False
            self._restore_handle_canvas()

    def _adapt_bg_sample_and_apply(self):
        """Step 2: 取色并应用颜色，然后恢复手柄"""
        try:
            cx = self._adapt_sample_cx
            cy = self._adapt_sample_cy
            # HDC 释放移入 try/finally 避免泄漏
            hdc = user32.GetDC(0)
            try:
                color = gdi32.GetPixel(hdc, cx, cy)
            finally:
                user32.ReleaseDC(0, hdc)
            r = color & 0xFF
            g = (color >> 8) & 0xFF
            b = (color >> 16) & 0xFF
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            # 灰度计算（标准亮度公式，0=黑，255=白）
            gray = int(0.299 * r + 0.587 * g + 0.114 * b)
            # 黑度百分比：0%=白，100%=黑
            blackness = (255 - gray) / 255 * 100
            # 偏白（黑度≤50%）→黑字；偏黑（黑度>50%）→白字
            if blackness <= 50:
                text_color = "#000000"
            else:
                text_color = "#FFFFFF"

            # 应用颜色
            self.cfg['bg_color'] = hex_color
            self.cfg['text_color'] = text_color
            self.cfg['bg_opacity'] = 1.0
            self._apply_window_style()
            self._apply_text_appearance()

            # 记忆为最后一次适配状态
            self._adapt_bg_last = {
                'bg_color': hex_color,
                'text_color': text_color,
                'bg_opacity': 1.0,
            }
            self._save_config_debounced()
        except Exception as e:
            print(f"[适配背景] 取色失败: {e}")
        finally:
            # 恢复手柄 Canvas 并清除重入标志
            self._adapt_bg_in_progress = False
            self._restore_handle_canvas()

    def _restore_handle_canvas(self):
        """恢复手柄 Canvas 显示"""
        try:
            canvas_y = self._get_handle_canvas_y()
            self.handle_canvas.place(x=0, y=canvas_y)
            self.handle_canvas.tk.call('raise', self.handle_canvas._w)
            self._update_handle()
        except Exception:
            pass
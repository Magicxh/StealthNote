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
        self.panel.overrideredirect(True)

        # 仪表盘使用色键 #010101 实现透明区域
        self.panel.configure(bg=COLORKEY)

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.panel.iconbitmap(self.icon_path)
            except Exception:
                pass

        if self.cfg['panel_x'] is None or self.cfg['panel_y'] is None:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            px = (sw - PANEL_WIDTH) // 2
            py = (sh - PANEL_HEIGHT) // 3
        else:
            px = int(self.cfg['panel_x'])
            py = int(self.cfg['panel_y'])

        self.panel.geometry(f"{PANEL_WIDTH}x{PANEL_HEIGHT}+{px}+{py}")

        self._panel_hwnd = self.panel.winfo_id()
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
            ("O",   "打开文件\nCtrl+O",       self.file_open,      btn_color_14, False),
            ("S",   "保存文件\nCtrl+S",       self.file_save,      btn_color_14, False),
            ("SN",  "另存为\nCtrl+Shift+S",   self.file_save_as,   btn_color_14, False),
            ("隐",  "隐写模式\n中键切换",     self.toggle_stealth, btn_color_58, "stealth_mode"),
            ("反",  "反色显示\nCtrl+F",       self.toggle_invert,  btn_color_58, "invert_mode"),
            ("易",  "易读模式\nCtrl+Shift+R", self.toggle_read,    btn_color_58, "read_mode"),
            ("顶",  "置顶模式\nCtrl+T",       self.toggle_topmost, btn_color_58, "topmost"),
            ("色",  "主题切换\nCtrl+M",       self.toggle_theme,   btn_color_58, False),
            ("控",  "设置仪表盘\nCtrl+K",     self.show_settings,  btn_color_58, False),
            ("X",   "退出程序",               self.exit_app,       btn_color_x,  False),
        ]

        self.panel_buttons = {}
        self.panel_button_containers = {}
        self.panel_button_dots = {}
        for i, (text, tip, cmd, bg, state_key) in enumerate(buttons):
            container = tk.Frame(self.panel_inner, bg=bg, width=PANEL_BTN_SIZE, height=PANEL_BTN_SIZE)
            container.pack_propagate(False)
            container.grid(row=0, column=i, padx=PANEL_BTN_GAP//2, pady=0)
            self.panel_button_containers[text] = container

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
            self.panel_buttons[text] = btn

        # 统一创建仪表盘小红点：作为按钮容器的直接子控件，固定坐标定位。
        # 容器 pack_propagate(False) 保证尺寸固定，坐标不受布局时序影响。
        # dot canvas bg 与按钮容器 bg 一致，避免 COLORKEY 在子控件中不透明产生黑块。
        dot_size = 8
        for text, key in [("隐", "stealth_mode"), ("反", "invert_mode"),
                          ("易", "read_mode"), ("顶", "topmost")]:
            container = self.panel_button_containers[text]
            container_bg = container.cget("bg")
            dot_canvas = tk.Canvas(container, bg=container_bg, width=dot_size, height=dot_size,
                                   highlightthickness=0, bd=0)
            # 6x6 红色实心圆点，无描边
            dot_canvas.create_oval(1, 1, 7, 7, fill="#ff3333", outline="")
            # 点击穿透到按钮，避免红点拦截按钮点击
            dot_canvas.bind("<Button-1>", lambda e, t=text: self.panel_buttons[t].invoke())
            dot_canvas.place_forget()
            self.panel_button_dots[text] = dot_canvas

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
        小红点是按钮容器的子控件，固定坐标 place，不受布局时序影响。"""
        dot_map = {
            "隐": "stealth_mode",
            "反": "invert_mode",
            "易": "read_mode",
            "顶": "topmost",
        }
        for text, key in dot_map.items():
            canvas = self.panel_button_dots.get(text)
            if not canvas or not canvas.winfo_exists():
                continue
            enabled = bool(self.cfg.get(key, False))
            if enabled:
                canvas.place(x=PANEL_BTN_SIZE - 8 - 1, y=3)
                canvas.tk.call('raise', canvas._w)
            else:
                canvas.place_forget()

    def _on_panel_press(self, event):
        self._panel_drag_active = True
        self._panel_drag_dx = event.x_root - self.panel.winfo_x()
        self._panel_drag_dy = event.y_root - self.panel.winfo_y()
        self.panel.lift()

    def _on_panel_drag(self, event):
        if not self._panel_drag_active:
            return
        x = event.x_root - self._panel_drag_dx
        y = event.y_root - self._panel_drag_dy
        self.panel.geometry(f"+{x}+{y}")

    def _on_panel_release(self, event):
        if self._panel_drag_active:
            self.cfg['panel_x'] = self.panel.winfo_x()
            self.cfg['panel_y'] = self.panel.winfo_y()
            self._save_config_debounced()
            self._panel_drag_active = False

    def toggle_panel(self):
        self.cfg['show_panel'] = not self.cfg['show_panel']
        if self.cfg['show_panel']:
            self.panel.deiconify()
            self.panel.lift()
        else:
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
        self._save_config_debounced()

    def toggle_read(self):
        self.cfg['read_mode'] = not self.cfg['read_mode']
        self._apply_window_style()
        self._apply_text_appearance()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._save_config_debounced()

    def toggle_topmost(self):
        self.cfg['topmost'] = not self.cfg['topmost']
        self.root.attributes("-topmost", self.cfg['topmost'])
        self.content_win.attributes("-topmost", self.cfg['topmost'])
        self.handle_win.attributes("-topmost", self.cfg['topmost'])
        if self.cfg['topmost']:
            self.root.lift()
            self.content_win.lift()
            self.handle_win.lift()
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
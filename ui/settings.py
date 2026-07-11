# -*- coding: utf-8 -*-
"""Stealth Note - 设置面板模块（SettingsMixin）"""
import os
import copy
import json
import configparser
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from constants import (
    APP_NAME, VERSION, AUTHOR, CONTACT_EMAIL,
    THEME_PALETTES,
    MIN_TEXT_OPACITY, MIN_READ_BG_OPACITY, MIN_CORNER_OPACITY,
    MIN_CORNER_LINE, MIN_CORNER_LEN, MAX_CORNER_LEN, MAX_CORNER_LINE,
    MIN_HANDLE_SIZE, MAX_HANDLE_SIZE, MIN_FONT_SIZE, MAX_FONT_SIZE,
    MIN_PANEL_OPACITY,
)
from config import DEFAULT_CONFIG, validate_config
from utils import clamp, set_layered_transparent


class SettingsMixin:
    """设置面板 Mixin：Tabs构建、实时预览、应用/确定"""

    def show_settings(self):
        if (hasattr(self, '_settings_win') and self._settings_win
                and self._settings_win.winfo_exists()):
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        self._settings_win = tk.Toplevel(self.root)
        self._settings_win.title("设置 - Stealth Note")
        self._settings_win.geometry("680x820")
        self._settings_win.resizable(True, True)
        self._settings_win.minsize(600, 700)

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self._settings_win.iconbitmap(self.icon_path)
            except Exception:
                pass

        main = ttk.Frame(self._settings_win, padding=12)
        main.pack(fill="both", expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True)

        self._preview_cfg = copy.deepcopy(self.cfg)

        self._build_tab_system(nb)
        self._build_tab_textbox(nb)
        self._build_tab_panel(nb)
        self._build_tab_about(nb)

        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=10)
        ttk.Button(btns, text="取消", command=self._settings_win.destroy).pack(side="right")
        ttk.Button(btns, text="应用", command=self._apply_settings).pack(side="right", padx=4)
        ttk.Button(btns, text="确定", command=self._ok_settings).pack(side="right", padx=4)

        self._settings_win.transient(self.root)
        self._settings_win.lift()
        self._settings_win.focus_force()

    def _color_button(self, parent, var, on_change=None):
        btn = tk.Button(parent, width=6, height=1, bg=var.get(),
                        fg="#ffffff", bd=1, relief="solid", cursor="hand2",
                        command=lambda: self._pick_color_for(var, btn, on_change))
        return btn

    def _pick_color_for(self, var, btn, on_change):
        color = colorchooser.askcolor(title="选择颜色", initialcolor=var.get())[1]
        if color:
            var.set(color)
            btn.configure(bg=color)
            if on_change:
                on_change()

    def _make_scale_clickable(self, scale, var, from_, to, resolution, on_change=None):
        """完全接管Scale鼠标行为：点击轨道精确定位+平滑拖动"""
        scale.bindtags((str(scale),))
        slider_len = scale.cget("sliderlength")
        try:
            slider_len = int(slider_len)
        except Exception:
            slider_len = 14
        pad = slider_len // 2

        def set_from_event(event):
            try:
                w = scale.winfo_width()
                if w <= pad * 2 + 2:
                    return
                x = max(pad, min(w - pad, event.x))
                rel = (x - pad) / (w - pad * 2)
                val = from_ + rel * (to - from_)
                if resolution and resolution > 0:
                    val = round(val / resolution) * resolution
                val = max(from_, min(to, val))
                if var.get() != val:
                    var.set(val)
                    if on_change:
                        on_change()
            except Exception as e:
                print(f"[滑块] 事件处理失败: {e}")

        scale.bind("<Button-1>", set_from_event)
        scale.bind("<B1-Motion>", set_from_event)
        scale.bind("<ButtonRelease-1>", lambda e: None)
        return scale

    def _opacity_scale(self, parent, var, from_=0.0, to=1.0, on_change=None):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)

        tk.Label(frame, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 4))

        scale = tk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal",
                         command=lambda v, vv=var, oc=on_change: self._on_scale_change(vv, oc),
                         troughcolor="#444444", sliderlength=14, width=8,
                         resolution=0.01, showvalue=False, bigincrement=0.1)
        scale.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale, var, from_, to, 0.01, on_change)

        tk.Label(frame, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(4, 4))

        pct_label = tk.Label(frame, text=f"{int(var.get()*100)}%", width=5, anchor="w")
        pct_label.pack(side="left")

        def update_pct(*args):
            pct_label.config(text=f"{int(var.get()*100)}%")
        var.trace_add("write", update_pct)

        return frame

    def _on_scale_change(self, var, on_change):
        if on_change:
            on_change()

    def _spin_scale(self, parent, var, from_, to, on_change=None):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)

        spin = ttk.Spinbox(frame, from_=from_, to=to, textvariable=var, width=6)
        spin.pack(side="left", padx=(0, 8))

        scale = tk.Scale(frame, from_=from_, to=to, variable=var, orient="horizontal",
                         command=lambda v, vv=var, oc=on_change: self._on_scale_change(vv, oc),
                         troughcolor="#444444", sliderlength=14, width=8,
                         resolution=1, showvalue=False, bigincrement=5)
        scale.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale, var, from_, to, 1, on_change)

        return frame

    def _refresh_preview(self):
        """实时预览设置效果（30ms 防抖，避免滑块拖动时闪烁）"""
        if hasattr(self, '_preview_after_id') and self._preview_after_id:
            self.root.after_cancel(self._preview_after_id)
        self._preview_after_id = self.root.after(30, self._do_refresh_preview)

    def _do_refresh_preview(self):
        """实际执行预览刷新"""
        self._preview_after_id = None
        old_cfg = self.cfg
        self.cfg = self._preview_cfg
        try:
            self._apply_window_style()
            self._apply_text_appearance()
            self._apply_stealth_state()
            self._corner_dirty = True
            self._update_corners()
            self._update_handle()
            self._update_panel_button_states()

            self.panel_inner.configure(bg=self._preview_cfg['panel_bg_color'])
            if not self._panel_hwnd:
                self._panel_hwnd = self.panel.winfo_id()
            alpha = int(max(MIN_PANEL_OPACITY, self._preview_cfg['panel_opacity']) * 255)
            set_layered_transparent(self._panel_hwnd, alpha, use_colorkey=True, show_taskbar=False)

            if not self._handle_hwnd and hasattr(self, 'handle_win') and self.handle_win and self.handle_win.winfo_exists():
                self._handle_hwnd = self.handle_win.winfo_id()
            if self._handle_hwnd:
                set_layered_transparent(
                    self._handle_hwnd, 255,
                    use_colorkey=False, show_taskbar=False)

            self.root.attributes("-topmost", self._preview_cfg['topmost'])

            if self._preview_cfg['show_scrollbar']:
                self.text.see("1.0")
            else:
                self._set_scrollbar_visible(False)

            if self._preview_cfg['show_panel']:
                self.panel.deiconify()
            else:
                self.panel.withdraw()

            self._set_taskbar_visible(self._preview_cfg['show_taskbar'])

            self._layout_handle()
        except Exception as e:
            print(f"[预览] 刷新失败: {e}")
        finally:
            self.cfg = old_cfg
            try:
                self._apply_stealth_state()
            except Exception:
                pass
            # 恢复 cfg 后必须刷新一次仪表盘小红点，避免取消/预览后状态残留
            try:
                self._update_panel_button_states()
            except Exception:
                pass

    def _build_tab_system(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="系统设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="显示设置", padding=8)
        gf1.pack(fill="x", pady=6)

        v_invert = tk.BooleanVar(value=cfg['invert_mode'])
        v_read = tk.BooleanVar(value=cfg['read_mode'])
        v_top = tk.BooleanVar(value=cfg['topmost'])
        v_theme = tk.StringVar(value=cfg.get('theme_mode', 'dark'))

        def update_display():
            cfg['invert_mode'] = v_invert.get()
            cfg['read_mode'] = v_read.get()
            cfg['topmost'] = v_top.get()
            new_theme = v_theme.get()
            if new_theme != cfg.get('theme_mode', 'dark'):
                palette = THEME_PALETTES.get(new_theme, THEME_PALETTES['dark'])
                for key, value in palette.items():
                    cfg[key] = value
                cfg['theme_mode'] = new_theme
            self._refresh_preview()

        ttk.Checkbutton(gf1, text="反色显示", variable=v_invert, command=update_display).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="易读模式", variable=v_read, command=update_display).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="置顶模式", variable=v_top, command=update_display).pack(anchor="w", pady=2)

        theme_frame = tk.Frame(gf1)
        theme_frame.pack(anchor="w", pady=2)
        ttk.Label(theme_frame, text="主题模式：").pack(side="left")
        for mode, label in [("dark", "深色"), ("light", "浅色")]:
            ttk.Radiobutton(theme_frame, text=label, variable=v_theme, value=mode,
                            command=update_display).pack(side="left", padx=(4, 0))

        gf2 = ttk.LabelFrame(f, text="运行设置", padding=8)
        gf2.pack(fill="x", pady=6)

        v_taskbar = tk.BooleanVar(value=cfg['show_taskbar'])
        v_show_panel = tk.BooleanVar(value=cfg['show_panel'])

        def update_runtime():
            cfg['show_taskbar'] = v_taskbar.get()
            cfg['show_panel'] = v_show_panel.get()
            self._refresh_preview()

        ttk.Checkbutton(gf2, text="显示任务栏窗口", variable=v_taskbar, command=update_runtime).pack(anchor="w", pady=2)
        ttk.Checkbutton(gf2, text="显示仪表盘", variable=v_show_panel, command=update_runtime).pack(anchor="w", pady=2)

        gf3 = ttk.LabelFrame(f, text="配置文件", padding=8)
        gf3.pack(fill="x", pady=6)

        btns = tk.Frame(gf3)
        btns.pack(fill="x")
        ttk.Button(btns, text="保存设置为文件...", command=self._export_config).pack(side="left", padx=2)
        ttk.Button(btns, text="读取设置文件...", command=self._import_config).pack(side="left", padx=2)

    def _export_config(self):
        path = filedialog.asksaveasfilename(
            title="保存配置", defaultextension=".ini",
            filetypes=[("配置文件", "*.ini"), ("JSON文件", "*.json")])
        if not path:
            return
        try:
            if path.lower().endswith('.json'):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self._preview_cfg, f, indent=2, ensure_ascii=False)
            else:
                cp = configparser.ConfigParser()
                cp.add_section('General')
                for k, v in self._preview_cfg.items():
                    cp.set('General', k, str(v))
                with open(path, 'w', encoding='utf-8') as f:
                    cp.write(f)
            messagebox.showinfo("成功", "配置已保存！")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def _import_config(self):
        path = filedialog.askopenfilename(
            title="读取配置",
            filetypes=[("配置文件", "*.ini;*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            if path.lower().endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                cp = configparser.ConfigParser()
                cp.read(path, encoding='utf-8')
                data = {}
                for sec in cp.sections():
                    for k, v in cp.items(sec):
                        data[k] = v

            for k, v in data.items():
                if k in DEFAULT_CONFIG:
                    def_val = DEFAULT_CONFIG[k]
                    if isinstance(def_val, bool):
                        data[k] = str(v).lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(def_val, (int, float)):
                        try:
                            data[k] = type(def_val)(v)
                        except (ValueError, TypeError):
                            pass

            for k in DEFAULT_CONFIG:
                if k not in data:
                    data[k] = DEFAULT_CONFIG[k]

            self._preview_cfg = validate_config(data)
            self._refresh_preview()
            messagebox.showinfo("成功", "配置已导入！")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def _build_tab_textbox(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="文本框设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="控件设置", padding=8)
        gf1.pack(fill="x", pady=6)

        v_show_titlebar = tk.BooleanVar(value=cfg.get('show_titlebar', False))
        v_show_statusbar = tk.BooleanVar(value=cfg.get('show_statusbar', False))
        v_show_sb = tk.BooleanVar(value=cfg['show_scrollbar'])

        ttk.Checkbutton(gf1, text="显示标题栏（待开发）", variable=v_show_titlebar, state="disabled").pack(anchor="w", pady=2)
        ttk.Checkbutton(gf1, text="显示状态栏（待开发）", variable=v_show_statusbar, state="disabled").pack(anchor="w", pady=2)

        def update_scrollbar():
            cfg['show_scrollbar'] = v_show_sb.get()
            self._refresh_preview()

        ttk.Checkbutton(gf1, text="启用滚动条", variable=v_show_sb, command=update_scrollbar).pack(anchor="w", pady=2)

        # 隐写模式设置
        v_stealth = tk.BooleanVar(value=cfg.get('stealth_mode', False))
        v_stealth_lines = tk.IntVar(value=cfg.get('stealth_lines', 3))

        def update_stealth():
            cfg['stealth_mode'] = v_stealth.get()
            cfg['stealth_lines'] = v_stealth_lines.get()
            self._refresh_preview()

        ttk.Separator(gf1, orient="horizontal").pack(fill="x", pady=8)
        ttk.Checkbutton(gf1, text="启用隐写模式", variable=v_stealth,
                        command=update_stealth).pack(anchor="w", pady=2)
        lines_frame = tk.Frame(gf1)
        lines_frame.pack(anchor="w", pady=2)
        ttk.Label(lines_frame, text="隐写行数：").pack(side="left", padx=(0, 6))
        for lines, label in [(1, "一行"), (2, "两行"), (3, "三行")]:
            ttk.Radiobutton(lines_frame, text=label, variable=v_stealth_lines,
                            value=lines, command=update_stealth).pack(side="left", padx=(0, 8))

        gf2 = ttk.LabelFrame(f, text="文本框外观", padding=8)
        gf2.pack(fill="x", pady=6)

        v_bg_color = tk.StringVar(value=cfg['bg_color'])
        v_bg_opacity = tk.DoubleVar(value=cfg['bg_opacity'])
        v_text_color = tk.StringVar(value=cfg['text_color'])
        v_text_opacity = tk.DoubleVar(value=cfg['text_opacity'])
        v_read_bg_color = tk.StringVar(value=cfg['read_bg_color'])
        v_read_bg_opacity = tk.DoubleVar(value=cfg['read_bg_opacity'])
        v_corner_color = tk.StringVar(value=cfg['corner_color'])
        v_corner_opacity = tk.DoubleVar(value=cfg['corner_opacity'])

        def update_appearance():
            cfg['bg_color'] = v_bg_color.get()
            cfg['bg_opacity'] = round(clamp(v_bg_opacity.get(), 0.0, 1.0), 2)
            cfg['text_color'] = v_text_color.get()
            cfg['text_opacity'] = round(clamp(v_text_opacity.get(), MIN_TEXT_OPACITY, 1.0), 2)
            cfg['read_bg_color'] = v_read_bg_color.get()
            cfg['read_bg_opacity'] = round(clamp(v_read_bg_opacity.get(), MIN_READ_BG_OPACITY, 1.0), 2)
            cfg['corner_color'] = v_corner_color.get()
            cfg['corner_opacity'] = round(clamp(v_corner_opacity.get(), MIN_CORNER_OPACITY, 1.0), 2)
            self._refresh_preview()

        def _color_opacity_row(parent, label_text, color_var, opacity_var, min_op, on_change):
            row = tk.Frame(parent)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label_text, width=10, anchor="e").pack(side="left", padx=(0, 6))
            self._color_button(row, color_var, on_change=on_change).pack(side="left", padx=(0, 8))
            tk.Label(row, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
            scale = tk.Scale(row, from_=min_op, to=1.0, variable=opacity_var, orient="horizontal",
                             command=lambda v: on_change(),
                             troughcolor="#444444", sliderlength=14, width=8,
                             resolution=0.01, showvalue=False, bigincrement=0.1)
            scale.pack(side="left", fill="x", expand=True)
            self._make_scale_clickable(scale, opacity_var, min_op, 1.0, 0.01, on_change)
            tk.Label(row, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
            pct = tk.Label(row, text=f"{int(opacity_var.get()*100)}%", width=5, anchor="w")
            pct.pack(side="left")
            opacity_var.trace_add("write", lambda *a: pct.config(text=f"{int(opacity_var.get()*100)}%"))

        _color_opacity_row(gf2, "文本背景：", v_bg_color, v_bg_opacity, 0.0, update_appearance)
        _color_opacity_row(gf2, "文字外观：", v_text_color, v_text_opacity, MIN_TEXT_OPACITY, update_appearance)
        _color_opacity_row(gf2, "易读模式：", v_read_bg_color, v_read_bg_opacity, MIN_READ_BG_OPACITY, update_appearance)
        _color_opacity_row(gf2, "框线颜色：", v_corner_color, v_corner_opacity, MIN_CORNER_OPACITY, update_appearance)

        ttk.Separator(gf2, orient="horizontal").pack(fill="x", pady=8)

        v_corner_lw = tk.IntVar(value=cfg['corner_line_width'])
        v_corner_sz = tk.IntVar(value=cfg['corner_size'])

        def update_corner_dims():
            cfg['corner_line_width'] = max(MIN_CORNER_LINE, v_corner_lw.get())
            cfg['corner_size'] = clamp(v_corner_sz.get(), MIN_CORNER_LEN, MAX_CORNER_LEN)
            self._refresh_preview()

        row_corner = tk.Frame(gf2)
        row_corner.pack(fill="x", pady=3)
        ttk.Label(row_corner, text="四角框线：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Label(row_corner, text="线宽").pack(side="left", padx=(0, 2))
        ttk.Spinbox(row_corner, from_=MIN_CORNER_LINE, to=MAX_CORNER_LINE, textvariable=v_corner_lw,
                    width=4, command=update_corner_dims).pack(side="left", padx=(0, 8))
        ttk.Label(row_corner, text="边长").pack(side="left", padx=(0, 2))
        ttk.Spinbox(row_corner, from_=MIN_CORNER_LEN, to=MAX_CORNER_LEN, textvariable=v_corner_sz,
                    width=4, command=update_corner_dims).pack(side="left", padx=(0, 8))
        scale_corner = tk.Scale(row_corner, from_=MIN_CORNER_LEN, to=MAX_CORNER_LEN, variable=v_corner_sz, orient="horizontal",
                                command=lambda v: update_corner_dims(),
                                troughcolor="#444444", sliderlength=14, width=8,
                                resolution=1, showvalue=False, bigincrement=5)
        scale_corner.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_corner, v_corner_sz, MIN_CORNER_LEN, MAX_CORNER_LEN, 1, update_corner_dims)

        gf3 = ttk.LabelFrame(f, text="文字样式", padding=8)
        gf3.pack(fill="x", pady=6)

        v_encoding = tk.StringVar(value=cfg['encoding'])
        v_font = tk.StringVar(value=cfg['text_font'])
        v_size = tk.IntVar(value=cfg['text_size'])

        def update_text_style():
            cfg['encoding'] = v_encoding.get()
            cfg['text_font'] = v_font.get()
            cfg['text_size'] = v_size.get()
            self._refresh_preview()

        row_enc = tk.Frame(gf3)
        row_enc.pack(fill="x", pady=3)
        ttk.Label(row_enc, text="文本编码：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Combobox(row_enc, textvariable=v_encoding, state="readonly", width=12,
                     values=["auto", "utf-8", "utf-8-sig", "gbk", "gb2312", "utf-16", "latin-1"]).pack(side="left")

        row_font = tk.Frame(gf3)
        row_font.pack(fill="x", pady=3)
        ttk.Label(row_font, text="字体：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        font_combo = ttk.Combobox(row_font, textvariable=v_font, state="readonly", width=24,
                                  values=["Microsoft YaHei UI", "SimSun", "SimHei", "KaiTi", "Arial", "Courier New", "Times New Roman"])
        font_combo.pack(side="left")
        font_combo.bind("<<ComboboxSelected>>", lambda e: update_text_style())

        row_size = tk.Frame(gf3)
        row_size.pack(fill="x", pady=3)
        ttk.Label(row_size, text="字号：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Spinbox(row_size, from_=MIN_FONT_SIZE, to=MAX_FONT_SIZE, textvariable=v_size,
                    width=4, command=update_text_style).pack(side="left", padx=(0, 8))
        scale_size = tk.Scale(row_size, from_=MIN_FONT_SIZE, to=MAX_FONT_SIZE, variable=v_size, orient="horizontal",
                              command=lambda v: update_text_style(),
                              troughcolor="#444444", sliderlength=14, width=8,
                              resolution=1, showvalue=False, bigincrement=2)
        scale_size.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_size, v_size, MIN_FONT_SIZE, MAX_FONT_SIZE, 1, update_text_style)

        gf4 = ttk.LabelFrame(f, text="控制手柄", padding=8)
        gf4.pack(fill="x", pady=6)

        v_handle_size = tk.IntVar(value=cfg['handle_size'])
        v_handle_opacity = tk.DoubleVar(value=cfg.get('handle_opacity', 0.8))

        def update_handle():
            cfg['handle_size'] = clamp(v_handle_size.get(), MIN_HANDLE_SIZE, MAX_HANDLE_SIZE)
            cfg['handle_opacity'] = round(clamp(v_handle_opacity.get(), 0.1, 1.0), 2)
            self._refresh_preview()

        row_handle = tk.Frame(gf4)
        row_handle.pack(fill="x", pady=3)
        ttk.Label(row_handle, text="手柄尺寸：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        ttk.Spinbox(row_handle, from_=MIN_HANDLE_SIZE, to=MAX_HANDLE_SIZE, textvariable=v_handle_size,
                    width=4, command=update_handle).pack(side="left", padx=(0, 8))
        scale_handle = tk.Scale(row_handle, from_=MIN_HANDLE_SIZE, to=MAX_HANDLE_SIZE, variable=v_handle_size, orient="horizontal",
                                command=lambda v: update_handle(),
                                troughcolor="#444444", sliderlength=14, width=8,
                                resolution=1, showvalue=False, bigincrement=2)
        scale_handle.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_handle, v_handle_size, MIN_HANDLE_SIZE, MAX_HANDLE_SIZE, 1, update_handle)

        row_ho = tk.Frame(gf4)
        row_ho.pack(fill="x", pady=3)
        ttk.Label(row_ho, text="手柄透明：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        tk.Label(row_ho, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
        scale_ho = tk.Scale(row_ho, from_=0.1, to=1.0, variable=v_handle_opacity, orient="horizontal",
                            command=lambda v: update_handle(),
                            troughcolor="#444444", sliderlength=14, width=8,
                            resolution=0.01, showvalue=False, bigincrement=0.1)
        scale_ho.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_ho, v_handle_opacity, 0.1, 1.0, 0.01, update_handle)
        tk.Label(row_ho, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
        pct_ho = tk.Label(row_ho, text=f"{int(v_handle_opacity.get()*100)}%", width=5, anchor="w")
        pct_ho.pack(side="left")
        v_handle_opacity.trace_add("write", lambda *a: pct_ho.config(text=f"{int(v_handle_opacity.get()*100)}%"))

        ttk.Label(gf4, text="手柄样式（待开发）", foreground="#999999").pack(anchor="w", pady=(8, 2))

    def _build_tab_panel(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="仪表盘设置")

        cfg = self._preview_cfg

        gf1 = ttk.LabelFrame(f, text="仪表盘外观", padding=8)
        gf1.pack(fill="x", pady=6)

        v_panel_bg = tk.StringVar(value=cfg['panel_bg_color'])
        v_panel_opacity = tk.DoubleVar(value=cfg['panel_opacity'])

        def update_panel():
            cfg['panel_bg_color'] = v_panel_bg.get()
            cfg['panel_opacity'] = round(clamp(v_panel_opacity.get(), MIN_PANEL_OPACITY, 1.0), 2)
            self._refresh_preview()

        row1 = tk.Frame(gf1)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="颜色：", width=10, anchor="e").pack(side="left", padx=(0, 6))
        self._color_button(row1, v_panel_bg, on_change=update_panel).pack(side="left", padx=(0, 8))
        tk.Label(row1, text="透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(0, 2))
        scale_panel = tk.Scale(row1, from_=MIN_PANEL_OPACITY, to=1.0, variable=v_panel_opacity, orient="horizontal",
                               command=lambda v: update_panel(),
                               troughcolor="#444444", sliderlength=14, width=8,
                               resolution=0.01, showvalue=False, bigincrement=0.1)
        scale_panel.pack(side="left", fill="x", expand=True)
        self._make_scale_clickable(scale_panel, v_panel_opacity, MIN_PANEL_OPACITY, 1.0, 0.01, update_panel)
        tk.Label(row1, text="不透明", font=("Microsoft YaHei UI", 8), fg="#888888").pack(side="left", padx=(2, 4))
        pct = tk.Label(row1, text=f"{int(v_panel_opacity.get()*100)}%", width=5, anchor="w")
        pct.pack(side="left")
        v_panel_opacity.trace_add("write", lambda *a: pct.config(text=f"{int(v_panel_opacity.get()*100)}%"))

        gf2 = ttk.LabelFrame(f, text="按钮说明", padding=8)
        gf2.pack(fill="both", expand=True, pady=6)

        btn_info = [
            ("O",  "打开文件",   "Ctrl+O",       "#333333"),
            ("S",  "保存文件",   "Ctrl+S",       "#333333"),
            ("隐", "隐写模式",   "中键切换",     "#333333"),
            ("SN", "另存为",     "Ctrl+Shift+S", "#333333"),
            ("反", "反色显示",   "Ctrl+F",       "#3d3d3d"),
            ("易", "易读模式",   "Ctrl+Shift+R", "#3d3d3d"),
            ("顶", "置顶模式",   "Ctrl+T",       "#3d3d3d"),
            ("色", "主题切换",   "Ctrl+M",       "#3d3d3d"),
            ("控", "设置仪表盘", "Ctrl+K",       "#3d3d3d"),
            ("X",  "退出程序",   "—",            "#2a2a2a"),
            ("⋮⋮", "拖动仪表盘", "",             "#ff8800"),
        ]

        for symbol, name, shortcut, bg_color in btn_info:
            row = tk.Frame(gf2)
            row.pack(fill="x", pady=2)
            preview = tk.Label(row, text=symbol, bg=bg_color, fg="#ffffff", width=4,
                               font=("Microsoft YaHei UI", 9, "bold"), relief="flat")
            preview.pack(side="left", padx=(0, 8))
            ttk.Label(row, text=name, width=12, anchor="w").pack(side="left", padx=(0, 8))
            ttk.Label(row, text=shortcut, foreground="#888888").pack(side="left")

    def _build_tab_about(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="关于软件")

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(self.icon_path)
                img = img.resize((64, 64), Image.LANCZOS)
                self._about_icon = ImageTk.PhotoImage(img)
                tk.Label(f, image=self._about_icon).pack(pady=(12, 4))
            except Exception:
                ttk.Label(f, text="[S]", font=("Microsoft YaHei UI", 24)).pack(pady=(12, 4))
        else:
            ttk.Label(f, text="[S]", font=("Microsoft YaHei UI", 24, "bold")).pack(pady=(12, 4))

        ttk.Label(f, text=f"{APP_NAME} {VERSION}", font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(4, 4))
        ttk.Label(f, text=f"作者：{AUTHOR}").pack(pady=2)
        ttk.Label(f, text=f"邮箱：{CONTACT_EMAIL}").pack(pady=2)
        ttk.Label(f, text="\n完全透明的记事本工具").pack(pady=(8, 4))
        ttk.Label(f, text="支持多种透明度设置、反色显示、易读模式等功能").pack(pady=2)

    def _apply_settings(self):
        self.cfg = copy.deepcopy(self._preview_cfg)
        self._apply_window_style()
        self._apply_text_appearance()
        self._apply_stealth_state()
        self._corner_dirty = True
        self._update_corners()
        self._update_handle()
        self._update_panel_button_states()
        self._set_taskbar_visible(self.cfg['show_taskbar'])
        self._save_config_debounced()

    def _ok_settings(self):
        self._apply_settings()
        self._settings_win.destroy()
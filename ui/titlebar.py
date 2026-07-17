# -*- coding: utf-8 -*-
"""Stealth Note - 标题栏模块（TitlebarMixin）

v2.9.8: 独立窗口实现的胶囊状标题栏，显示文件名或"暂存模式"。
- 位于 content_win 上方，间隔 TITLEBAR_GAP
- 背景色/透明度/文字色/文字透明度继承主文本框参数
- 跟随 content_win 移动
"""
import os
import tkinter as tk
from tkinter import font as tkfont
from constants import *
from utils import mix_color, invert_color, set_layered_transparent


class TitlebarMixin:
    """标题栏 Mixin：胶囊状文件名显示"""

    def _init_titlebar(self):
        """初始化标题栏独立窗口"""
        self.titlebar_win = tk.Toplevel(self.root)
        self.titlebar_win.withdraw()
        self.titlebar_win.overrideredirect(True)
        self.titlebar_win.configure(bg=COLORKEY, bd=0, highlightthickness=0)

        # 设置所有者为 host_win，避免任务栏注册
        self.titlebar_win.update_idletasks()
        self._titlebar_hwnd = self.titlebar_win.winfo_id()
        self._set_window_owner(self._titlebar_hwnd, self._host_hwnd)

        # 计算固定宽度：基于字号和最大字符数
        try:
            f = tkfont.Font(family=TITLEBAR_FONT, size=TITLEBAR_FONT_SIZE)
            # 用20个汉字宽度估算（汉字约等于字号像素宽）
            char_w = f.measure("汉")
            self._titlebar_width = char_w * TITLEBAR_MAX_CHARS + TITLEBAR_HEIGHT + 8  # 加两端圆形+padding
        except Exception:
            self._titlebar_width = 200

        self.titlebar_win.geometry(f"{self._titlebar_width}x{TITLEBAR_HEIGHT}+-10000+-10000")

        # 设置分层窗口样式
        try:
            ex_style = user32.GetWindowLongW(self._titlebar_hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(self._titlebar_hwnd, GWL_EXSTYLE, ex_style)
            user32.SetLayeredWindowAttributes(
                self._titlebar_hwnd, COLORKEY_INT, 255, LWA_ALPHA | LWA_COLORKEY)
        except Exception:
            pass

        # Canvas 绘制胶囊形状和文字
        self._titlebar_canvas = tk.Canvas(
            self.titlebar_win,
            bg=COLORKEY,
            highlightthickness=0,
            bd=0,
            width=self._titlebar_width,
            height=TITLEBAR_HEIGHT,
        )
        self._titlebar_canvas.pack(fill="both", expand=True)

        self._titlebar_text_id = None
        self._titlebar_visible = False

        # 初始绘制
        self._update_titlebar_appearance()
        self._update_titlebar_text()

    # -------------------------------------------------------------------------
    # 绘制
    # -------------------------------------------------------------------------

    def _draw_titlebar_capsule(self, bg_color):
        """绘制胶囊形状（两端半圆+中间矩形）"""
        c = self._titlebar_canvas
        c.delete("capsule")
        w = self._titlebar_width
        h = TITLEBAR_HEIGHT
        r = TITLEBAR_CAPSULE_R
        # 中间矩形
        c.create_rectangle(r, 0, w - r, h, fill=bg_color, outline="", tags="capsule")
        # 左端半圆
        c.create_arc(0, 0, h, h, start=90, extent=180, fill=bg_color, outline="", tags="capsule")
        # 右端半圆
        c.create_arc(w - h, 0, w, h, start=-90, extent=180, fill=bg_color, outline="", tags="capsule")

    def _update_titlebar_appearance(self):
        """更新标题栏颜色和透明度（继承主文本框参数）"""
        if not hasattr(self, 'titlebar_win') or not self.titlebar_win or not self.titlebar_win.winfo_exists():
            return
        try:
            # 计算背景色（含反色），与 content_win 一致
            raw_bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                raw_bg = invert_color(raw_bg)

            # 文字颜色：预乘 text_opacity，与主文本框一致
            tc = self.cfg['text_color']
            if self.cfg['invert_mode']:
                tc = invert_color(tc)
            fg_color = mix_color(tc, self.cfg['text_opacity'], raw_bg)

            # 重绘胶囊
            self._draw_titlebar_capsule(raw_bg)

            # 更新文字颜色，并将文字提到胶囊之上（重绘胶囊后新胶囊在顶层，会遮挡文字）
            if self._titlebar_text_id is not None:
                self._titlebar_canvas.itemconfig(self._titlebar_text_id, fill=fg_color)
                self._titlebar_canvas.tag_raise(self._titlebar_text_id)

            # 设置窗口透明度
            if self.cfg['read_mode']:
                # 易读模式：使用 read_bg_opacity 控制透明度，与 content_win 一致
                # v2.9.8.5: alpha 边界 clamp
                alpha = int(max(0.0, min(1.0, self.cfg['read_bg_opacity'])) * 255)
            else:
                alpha = int(max(0.05, min(1.0, self.cfg['bg_opacity'])) * 255)
            user32.SetLayeredWindowAttributes(
                self._titlebar_hwnd, COLORKEY_INT, alpha, LWA_ALPHA | LWA_COLORKEY)

            # topmost 同步（v2.9.8.5: 仅在变化时切换，避免冗余 z-order 重排）
            new_topmost = bool(self.cfg['topmost'])
            if bool(self.titlebar_win.attributes('-topmost')) != new_topmost:
                self.titlebar_win.attributes("-topmost", new_topmost)
        except Exception as e:
            print(f"[标题栏] 外观更新失败: {e}")

    def _update_titlebar_text(self):
        """更新标题栏显示的文字内容（靠左对齐）"""
        if not hasattr(self, 'titlebar_win') or not self.titlebar_win or not self.titlebar_win.winfo_exists():
            return
        if self._titlebar_text_id is not None:
            self._titlebar_canvas.delete(self._titlebar_text_id)
            self._titlebar_text_id = None

        # 计算显示文字
        text = self._get_titlebar_label()
        if not text:
            return

        try:
            # 文字颜色
            raw_bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                raw_bg = invert_color(raw_bg)
            tc = self.cfg['text_color']
            if self.cfg['invert_mode']:
                tc = invert_color(tc)
            fg_color = mix_color(tc, self.cfg['text_opacity'], raw_bg)

            # 文字靠左对齐：x 从左端圆形区域之后开始，anchor="w"
            text_x = TITLEBAR_CAPSULE_R + 4
            text_width = self._titlebar_width - TITLEBAR_CAPSULE_R * 2 - 8
            self._titlebar_text_id = self._titlebar_canvas.create_text(
                text_x,
                TITLEBAR_HEIGHT // 2,
                text=text,
                fill=fg_color,
                font=(TITLEBAR_FONT, TITLEBAR_FONT_SIZE),
                anchor="w",
                width=text_width,
            )
        except Exception as e:
            print(f"[标题栏] 文字更新失败: {e}")

    def _get_titlebar_label(self):
        """计算标题栏应显示的文字"""
        if self._is_autosave_mode():
            # 暂存模式：有未保存改动时加*
            mark = "*" if self._autosave_dirty else ""
            return f"{mark}暂存模式"
        elif self.current_file:
            name = os.path.basename(self.current_file)
            mark = "*" if self._modified else ""
            return f"{mark}{name}"
        else:
            # 新文件无内容：显示"未命名"
            return "未命名"

    # -------------------------------------------------------------------------
    # 位置同步
    # -------------------------------------------------------------------------

    def _layout_titlebar(self):
        """同步标题栏位置到 content_win 上方，靠左对齐"""
        if not hasattr(self, 'titlebar_win') or not self.titlebar_win or not self.titlebar_win.winfo_exists():
            return
        if not hasattr(self, 'content_win') or not self.content_win or not self.content_win.winfo_exists():
            return
        try:
            cx = self.content_win.winfo_x()
            cy = self.content_win.winfo_y()
            # 标题栏左侧与文本框左侧对齐
            tx = cx
            # 标题栏位于 content_win 上方，间隔 TITLEBAR_GAP
            ty = cy - TITLEBAR_HEIGHT - TITLEBAR_GAP
            self.titlebar_win.geometry(f"+{tx}+{ty}")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 显示/隐藏
    # -------------------------------------------------------------------------

    def _update_titlebar_visibility(self):
        """根据 show_titlebar 配置更新标题栏可见性"""
        if not hasattr(self, 'titlebar_win') or not self.titlebar_win or not self.titlebar_win.winfo_exists():
            return
        should_show = bool(self.cfg.get('show_titlebar', False))
        if should_show and not self._titlebar_visible:
            self.titlebar_win.deiconify()
            self._layout_titlebar()
            self.titlebar_win.lift()
            self._titlebar_visible = True
        elif not should_show and self._titlebar_visible:
            self.titlebar_win.withdraw()
            self._titlebar_visible = False

    def _refresh_titlebar(self):
        """刷新标题栏外观+文字+位置（统一入口）"""
        self._update_titlebar_appearance()
        self._update_titlebar_text()
        self._update_titlebar_visibility()
        if self._titlebar_visible:
            self._layout_titlebar()

    def _toggle_titlebar(self):
        """切换标题栏显示状态"""
        self.cfg['show_titlebar'] = not self.cfg.get('show_titlebar', False)
        self._refresh_titlebar()
        self._save_config_debounced()

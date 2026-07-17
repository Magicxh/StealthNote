# -*- coding: utf-8 -*-
"""Stealth Note - 状态栏模块（StatusbarMixin）

v2.9.8: 胶囊状状态栏，显示文本框字数。
- 排在标题栏后面，固定位置/大小
- 背景色/透明度/文字色/文字透明度继承主文本框参数
- 跟随标题栏移动
"""
import tkinter as tk
from constants import *
from utils import mix_color, invert_color, set_layered_transparent


class StatusbarMixin:
    """状态栏 Mixin：胶囊状字数显示"""

    def _init_statusbar(self):
        """初始化状态栏独立窗口"""
        self.statusbar_win = tk.Toplevel(self.root)
        self.statusbar_win.withdraw()
        self.statusbar_win.overrideredirect(True)
        self.statusbar_win.configure(bg=COLORKEY, bd=0, highlightthickness=0)

        self.statusbar_win.update_idletasks()
        self._statusbar_hwnd = self.statusbar_win.winfo_id()
        self._set_window_owner(self._statusbar_hwnd, self._host_hwnd)

        self._statusbar_width = STATUSBAR_DEFAULT_WIDTH
        self.statusbar_win.geometry(f"{self._statusbar_width}x{STATUSBAR_HEIGHT}+-10000+-10000")

        # 分层窗口样式
        try:
            ex_style = user32.GetWindowLongW(self._statusbar_hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(self._statusbar_hwnd, GWL_EXSTYLE, ex_style)
            user32.SetLayeredWindowAttributes(
                self._statusbar_hwnd, COLORKEY_INT, 255, LWA_ALPHA | LWA_COLORKEY)
        except Exception:
            pass

        self._statusbar_canvas = tk.Canvas(
            self.statusbar_win,
            bg=COLORKEY,
            highlightthickness=0,
            bd=0,
            width=self._statusbar_width,
            height=STATUSBAR_HEIGHT,
        )
        self._statusbar_canvas.pack(fill="both", expand=True)

        self._statusbar_text_id = None
        self._statusbar_visible = False

        self._update_statusbar_appearance()
        self._update_statusbar_text()

    # -------------------------------------------------------------------------
    # 绘制
    # -------------------------------------------------------------------------

    def _draw_statusbar_capsule(self, bg_color):
        """绘制胶囊形状"""
        c = self._statusbar_canvas
        c.delete("capsule")
        w = self._statusbar_width
        h = STATUSBAR_HEIGHT
        r = STATUSBAR_CAPSULE_R
        c.create_rectangle(r, 0, w - r, h, fill=bg_color, outline="", tags="capsule")
        c.create_arc(0, 0, h, h, start=90, extent=180, fill=bg_color, outline="", tags="capsule")
        c.create_arc(w - h, 0, w, h, start=-90, extent=180, fill=bg_color, outline="", tags="capsule")

    def _update_statusbar_appearance(self):
        """更新状态栏颜色和透明度（继承主文本框参数）"""
        if not hasattr(self, 'statusbar_win') or not self.statusbar_win or not self.statusbar_win.winfo_exists():
            return
        try:
            raw_bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                raw_bg = invert_color(raw_bg)

            tc = self.cfg['text_color']
            if self.cfg['invert_mode']:
                tc = invert_color(tc)
            fg_color = mix_color(tc, self.cfg['text_opacity'], raw_bg)

            self._draw_statusbar_capsule(raw_bg)

            if self._statusbar_text_id is not None:
                self._statusbar_canvas.itemconfig(self._statusbar_text_id, fill=fg_color)
                self._statusbar_canvas.tag_raise(self._statusbar_text_id)

            if self.cfg['read_mode']:
                # v2.9.8.5: alpha 边界 clamp
                alpha = int(max(0.0, min(1.0, self.cfg['read_bg_opacity'])) * 255)
            else:
                alpha = int(max(0.05, min(1.0, self.cfg['bg_opacity'])) * 255)
            user32.SetLayeredWindowAttributes(
                self._statusbar_hwnd, COLORKEY_INT, alpha, LWA_ALPHA | LWA_COLORKEY)

            # v2.9.8.5: topmost 仅在变化时切换，避免冗余 z-order 重排
            new_topmost = bool(self.cfg['topmost'])
            if bool(self.statusbar_win.attributes('-topmost')) != new_topmost:
                self.statusbar_win.attributes("-topmost", new_topmost)
        except Exception as e:
            print(f"[状态栏] 外观更新失败: {e}")

    def _update_statusbar_text(self):
        """更新状态栏文字（字数统计）"""
        if not hasattr(self, 'statusbar_win') or not self.statusbar_win or not self.statusbar_win.winfo_exists():
            return
        if self._statusbar_text_id is not None:
            self._statusbar_canvas.delete(self._statusbar_text_id)
            self._statusbar_text_id = None

        try:
            content = self.text.get("1.0", "end-1c")
            count = len(content)
            text = f"字数：{count}"

            raw_bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                raw_bg = invert_color(raw_bg)
            tc = self.cfg['text_color']
            if self.cfg['invert_mode']:
                tc = invert_color(tc)
            fg_color = mix_color(tc, self.cfg['text_opacity'], raw_bg)

            # 居中显示
            self._statusbar_text_id = self._statusbar_canvas.create_text(
                self._statusbar_width // 2,
                STATUSBAR_HEIGHT // 2,
                text=text,
                fill=fg_color,
                font=(STATUSBAR_FONT, STATUSBAR_FONT_SIZE),
                anchor="center",
            )
        except Exception as e:
            print(f"[状态栏] 文字更新失败: {e}")

    # -------------------------------------------------------------------------
    # 位置同步
    # -------------------------------------------------------------------------

    def _layout_statusbar(self):
        """同步状态栏位置到标题栏右侧

        v2.9.8.5: 标题栏隐藏时，状态栏改为贴 content_win 右上角上方，
        避免贴在隐藏的标题栏旁导致位置错乱。
        """
        if not hasattr(self, 'statusbar_win') or not self.statusbar_win or not self.statusbar_win.winfo_exists():
            return
        try:
            # v2.9.8.5: 标题栏不可见时，状态栏贴 content_win 上方
            if not getattr(self, '_titlebar_visible', False):
                if not hasattr(self, 'content_win') or not self.content_win or not self.content_win.winfo_exists():
                    return
                cx = self.content_win.winfo_x()
                cy = self.content_win.winfo_y()
                cw = self.content_win.winfo_width()
                # 状态栏贴 content_win 右上角上方，与标题栏同高度位置
                sx = cx + cw - self._statusbar_width
                sy = cy - STATUSBAR_HEIGHT - STATUSBAR_GAP
                self.statusbar_win.geometry(f"+{sx}+{sy}")
                return
            # 标题栏可见时，排在标题栏右侧
            if not hasattr(self, 'titlebar_win') or not self.titlebar_win or not self.titlebar_win.winfo_exists():
                return
            tx = self.titlebar_win.winfo_x()
            ty = self.titlebar_win.winfo_y()
            tw = self._titlebar_width
            # 状态栏排在标题栏右侧，间隔 STATUSBAR_GAP
            sx = tx + tw + STATUSBAR_GAP
            sy = ty
            self.statusbar_win.geometry(f"+{sx}+{sy}")
        except Exception as e:
            print(f"[状态栏] 布局失败: {e}")

    # -------------------------------------------------------------------------
    # 显示/隐藏
    # -------------------------------------------------------------------------

    def _update_statusbar_visibility(self):
        """根据 show_statusbar 配置更新可见性"""
        if not hasattr(self, 'statusbar_win') or not self.statusbar_win or not self.statusbar_win.winfo_exists():
            return
        should_show = bool(self.cfg.get('show_statusbar', False))
        if should_show and not self._statusbar_visible:
            self.statusbar_win.deiconify()
            self._layout_statusbar()
            self.statusbar_win.lift()
            self._statusbar_visible = True
        elif not should_show and self._statusbar_visible:
            self.statusbar_win.withdraw()
            self._statusbar_visible = False

    def _refresh_statusbar(self):
        """刷新状态栏外观+文字+位置（统一入口）"""
        self._update_statusbar_appearance()
        self._update_statusbar_text()
        self._update_statusbar_visibility()
        if self._statusbar_visible:
            self._layout_statusbar()

    def _toggle_statusbar(self):
        """切换状态栏显示状态"""
        self.cfg['show_statusbar'] = not self.cfg.get('show_statusbar', False)
        self._refresh_statusbar()
        self._save_config_debounced()

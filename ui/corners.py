# -*- coding: utf-8 -*-
"""Stealth Note - 四角线框和窗口缩放模块（CornersMixin）"""
import tkinter as tk
from constants import *
from utils import mix_color, clamp

class CornersMixin:
    """四角线框和缩放 Mixin：四角绘制、窗口缩放、鼠标事件转发"""
    
    def _init_corners(self):
        """初始化四角框线：角元素已在 _init_content 中创建（位于文本之下），
        此处仅完成初始布局绘制。注意：只调用 _layout_corners()，不调用 _layout_all()，
        因为 _init_handle 还未执行。"""
        self._layout_corners()

    def _layout_all(self):
        self._sync_content_window()
        self._layout_corners()
        self._layout_handle()
        self._update_handle()
        if self._sb_visible:
            self._redraw_scrollbar()

    def _layout_corners(self):
        # 隐写模式下完全隐藏四角线框与缩放热区
        if self.cfg.get('stealth_mode'):
            for name in self._corner_frames:
                self._corner_frames[name].place_forget()
                self._corner_canvases[name].place_forget()
            return

        cs = max(MIN_CORNER_LEN, int(self.cfg['corner_size']))
        lw = max(MIN_CORNER_LINE, int(self.cfg['corner_line_width']))
        hs = CORNER_HOT_SIZE
        margin = CORNER_MARGIN

        # 热区位置（14x14）
        for name in self._corner_frames:
            frame = self._corner_frames[name]
            frame.configure(width=hs, height=hs)
            relx = 1.0 if 'e' in name else 0.0
            rely = 1.0 if 's' in name else 0.0
            x_offset = margin if 'w' in name else -margin
            y_offset = margin if 'n' in name else -margin
            frame.place(relx=relx, rely=rely, anchor=name, x=x_offset, y=y_offset)

        # 视觉画布位置：以角为锚点，大小 = size，确保框线完整显示
        for name in self._corner_canvases:
            canvas = self._corner_canvases[name]
            canvas.configure(width=cs, height=cs)
            relx = 0.0 if 'w' in name else 1.0
            rely = 0.0 if 'n' in name else 1.0
            anchor = name
            x_offset = margin if 'w' in name else -margin
            y_offset = margin if 'n' in name else -margin
            canvas.place(relx=relx, rely=rely, anchor=anchor, x=x_offset, y=y_offset)

        if self._corner_dirty:
            self._draw_all_corners()
            self._corner_dirty = False

        # 四角已用 place() 布局，热区 frame 在画布之上（用于缩放交互）。
        # 由于画布和热区在 text_container 之前创建，天然位于文本之下，无需 lower()。

    def _draw_all_corners(self):
        self._draw_corners_on_bg()

    def _draw_corners_on_bg(self):
        """在四个独立视觉画布上分别绘制对应角的框线。"""
        size = max(MIN_CORNER_LEN, int(self.cfg['corner_size']))
        lw = max(MIN_CORNER_LINE, int(self.cfg['corner_line_width']))

        color = self.cfg['corner_color']
        if self.cfg['invert_mode']:
            color = invert_color(color)
        corner_op = self.cfg['corner_opacity']
        # B20: 直接预乘，无补偿法（content_win 无 LWA_ALPHA）
        raw_bg = self.cfg['bg_color']
        if self.cfg['invert_mode']:
            raw_bg = invert_color(raw_bg)
        color = mix_color(color, corner_op, raw_bg)

        # B17: 重新设计框线公式 —— 线条始终贯穿整个画布，避免小尺寸时重叠或缺失
        # half 为线宽的中心偏移，线条从画布边缘开始绘制
        half = max(0, (lw - 1) // 2)
        # 各角的水平/垂直线均从 0 到 size，确保任意 size/lw 组合下都完整显示
        def draw_corner(canvas, name):
            canvas.delete("all")
            if name == "nw":
                # 水平线（顶部）+ 垂直线（左侧）
                canvas.create_line(0, half, size, half, fill=color, width=lw)
                canvas.create_line(half, 0, half, size, fill=color, width=lw)
            elif name == "ne":
                # 水平线（顶部）+ 垂直线（右侧）
                canvas.create_line(0, half, size, half, fill=color, width=lw)
                canvas.create_line(size - 1 - half, 0, size - 1 - half, size, fill=color, width=lw)
            elif name == "sw":
                # 水平线（底部）+ 垂直线（左侧）
                canvas.create_line(0, size - 1 - half, size, size - 1 - half, fill=color, width=lw)
                canvas.create_line(half, 0, half, size, fill=color, width=lw)
            elif name == "se":
                # 水平线（底部）+ 垂直线（右侧）
                canvas.create_line(0, size - 1 - half, size, size - 1 - half, fill=color, width=lw)
                canvas.create_line(size - 1 - half, 0, size - 1 - half, size, fill=color, width=lw)

        for name in self._corner_canvases:
            draw_corner(self._corner_canvases[name], name)

    def _update_corners(self):
        self._corner_dirty = True
        self._layout_corners()

    def _on_resize_start(self, event, edge):
        # 隐写模式下禁止纵向缩放（高度由行数决定）
        if self.cfg.get('stealth_mode') and ('n' in edge or 's' in edge):
            return
        w = self.content_win.winfo_width()
        h = self.content_win.winfo_height()
        cwx = self.content_win.winfo_x()
        cwy = self.content_win.winfo_y()
        self._resize_edge = edge
        self._resize_start = (event.x_root, event.y_root, w, h, cwx, cwy)
        self._corner_dirty = True

    def _on_resize(self, event):
        if not self._resize_edge:
            return
        sx, sy, sw, sh, cwx, cwy = self._resize_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        edge = self._resize_edge

        nw, nh = sw, sh
        nx, ny = cwx, cwy

        if 'e' in edge:
            nw = sw + dx
        if 'w' in edge:
            nw = sw - dx
            nx = cwx + dx
        if 's' in edge:
            nh = sh + dy
        if 'n' in edge:
            nh = sh - dy
            ny = cwy + dy

        nw = max(MIN_WINDOW_W, nw)
        nh = max(MIN_WINDOW_H, nh)

        # v2.9.7: root 窗口 = content_win 向左扩展 handle_offset
        offset = self._get_handle_offset() if hasattr(self, '_get_handle_offset') else 0
        self.root.geometry(f"{nw + offset}x{nh}+{nx - offset}+{ny}")

    def _on_resize_end(self, event):
        if self._resize_edge:
            self.cfg['window_width'] = self.content_win.winfo_width()
            self.cfg['window_x'] = self.content_win.winfo_x()
            self.cfg['window_y'] = self.content_win.winfo_y()
            if not self.cfg.get('stealth_mode'):
                self.cfg['window_height'] = self.content_win.winfo_height()
            self._save_config_debounced()
            self._resize_edge = None
            self._layout_handle()
            self._layout_corners()

    def _get_resize_edge_at(self, x, y):
        """根据鼠标坐标判断当前是否处于四角缩放热区。
        v2.9.7: 使用 content_win 尺寸（文本区），而非 root（含手柄区域）。"""
        if self.cfg.get('stealth_mode'):
            return None
        w = self.content_win.winfo_width()
        h = self.content_win.winfo_height()
        hs = CORNER_HOT_SIZE
        if x <= hs and y <= hs:
            return "nw"
        if x >= w - hs and y <= hs:
            return "ne"
        if x <= hs and y >= h - hs:
            return "sw"
        if x >= w - hs and y >= h - hs:
            return "se"
        return None

    def _get_active_text_widget(self):
        """返回当前可见的书写框控件"""
        if self.cfg.get('stealth_mode'):
            return self.stealth_text if self._is_stealth_container_visible() else None
        return self.text

    def _root_to_widget_coords(self, widget, rx, ry):
        """将 root 窗口内坐标转换为指定控件内坐标"""
        try:
            sx = self.root.winfo_rootx() + rx
            sy = self.root.winfo_rooty() + ry
            wx = sx - widget.winfo_rootx()
            wy = sy - widget.winfo_rooty()
            return wx, wy
        except Exception:
            return rx, ry

    def _is_point_in_widget(self, widget, rx, ry):
        """判断 root 坐标是否落在指定控件几何区域内"""
        try:
            wx = widget.winfo_rootx() - self.root.winfo_rootx()
            wy = widget.winfo_rooty() - self.root.winfo_rooty()
            ww = widget.winfo_width()
            wh = widget.winfo_height()
            return wx <= rx <= wx + ww and wy <= ry <= wy + wh
        except Exception:
            return False

    def _forward_text_button1(self, widget, rx, ry):
        """将 root 的 Button-1 转发给书写框：设置焦点并定位光标"""
        try:
            widget.focus_set()
            wx, wy = self._root_to_widget_coords(widget, rx, ry)
            idx = widget.index(f"@{wx},{wy}")
            widget.mark_set("insert", idx)
            widget.see("insert")
            self._text_select_widget = widget
            self._text_select_anchor = idx
            self._text_selecting = True
            self._text_click_moved = False
        except Exception:
            pass

    def _forward_text_motion(self, widget, rx, ry):
        """将 root 的 B1-Motion 转发给书写框：模拟拖拽选区"""
        try:
            widget.focus_set()
            wx, wy = self._root_to_widget_coords(widget, rx, ry)
            idx = widget.index(f"@{wx},{wy}")
            widget.mark_set("insert", idx)
            widget.see("insert")
            if self._text_select_anchor:
                widget.tag_remove("sel", "1.0", "end")
                # Tkinter 的 tag_add 会自动处理前后顺序
                widget.tag_add("sel", self._text_select_anchor, idx)
            self._text_click_moved = True
        except Exception:
            pass

    def _forward_text_wheel(self, widget, rx, ry, delta):
        """将 root 的 MouseWheel 转发给普通文本框。隐写模式由 stealth_text 自身处理，不转发。"""
        try:
            if widget is self.stealth_text:
                return False
            if not self._is_point_in_widget(widget, rx, ry):
                return False
            # 左键按下时调整背景透明度
            if self._is_left_button_held():
                d = 1 if delta > 0 else -1
                new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + d * 0.05))
                self.cfg['bg_opacity'] = round(new_op, 2)
                self._apply_window_style()
                self._save_config_debounced()
                return True
            # 每次滚动一行
            lines = -1 if delta > 0 else 1
            widget.yview_scroll(lines, "units")
            return True
        except Exception:
            return False

    def _on_root_button_press(self, event):
        """v2.9.7: root 包含手柄区域，仅聚焦文本，缩放由 content_win 处理"""
        self._focus_text()

    def _on_root_resize(self, event):
        """根窗口拖动：仅处理缩放。"""
        if self._resize_edge:
            self._on_resize(event)

    def _on_root_resize_end(self, event):
        """根窗口释放：仅结束缩放。"""
        if self._resize_edge:
            self._on_resize_end(event)
            self._on_root_motion(event)

    def _on_root_motion(self, event):
        """根窗口移动：v2.9.7 root 包含手柄区域，不在 root 上显示缩放光标"""
        pass

    def _on_content_button_press(self, event):
        """内容窗口按下：仅处理四角缩放，其余情况聚焦文本框。
        文本框自身为实色不透明控件，事件由 Tkinter 原生处理。"""
        if event.widget in (self.text, self.stealth_text):
            return
        edge = self._get_resize_edge_at(event.x, event.y)
        if edge:
            self._on_resize_start(event, edge)
            return
        self._focus_text()

    def _on_content_resize(self, event):
        """内容窗口拖动：仅处理缩放。"""
        if event.widget in (self.text, self.stealth_text):
            return
        self._on_resize(event)

    def _on_content_resize_end(self, event):
        """内容窗口释放：仅结束缩放。"""
        if event.widget in (self.text, self.stealth_text):
            return
        self._on_resize_end(event)
        self._on_content_motion(event)

    def _on_root_wheel(self, event):
        """根窗口滚轮：仅在普通模式下转发给文本框。隐写模式由 stealth_text 自身处理。"""
        if self.cfg.get('stealth_mode'):
            return None
        widget = self.text
        if widget and self._forward_text_wheel(widget, event.x, event.y, event.delta):
            return "break"

    def _on_content_motion(self, event):
        """内容窗口移动：在四角热区切换鼠标指针"""
        # 事件来自文本框时不干预，避免干扰文本交互
        if event.widget in (self.text, self.stealth_text):
            return
        try:
            edge = self._get_resize_edge_at(event.x, event.y)
            cursor = {
                "nw": "top_left_corner",
                "ne": "top_right_corner",
                "sw": "bottom_left_corner",
                "se": "bottom_right_corner",
            }.get(edge, "")
            self.content_win.config(cursor=cursor)
            self.root.config(cursor=cursor)
        except Exception:
            pass
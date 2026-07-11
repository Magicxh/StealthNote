# -*- coding: utf-8 -*-
"""Stealth Note - 隐写框集群模块（StealthClusterMixin）"""
import tkinter as tk
from tkinter import font as tkfont
from constants import *
from utils import mix_color, clamp


class StealthClusterMixin:
    """隐写框集群 Mixin：隐写文本框、同步、横线、切换"""

    def _sync_to_stealth(self):
        """将普通文本框内容同步到隐写文本框"""
        if self._syncing_text or not self.cfg.get('stealth_mode'):
            return
        try:
            self._syncing_text = True
            src = self.text.get("1.0", "end-1c")
            dst = self.stealth_text.get("1.0", "end-1c")
            if src != dst:
                cur = self.text.index("insert")
                self.stealth_text.delete("1.0", "end")
                self.stealth_text.insert("1.0", src)
                self.stealth_text.mark_set("insert", cur)
                self._refresh_stealth_view()
        except Exception as e:
            print(f"[隐写同步] to stealth 失败: {e}")
        finally:
            self._syncing_text = False

    def _sync_from_stealth(self):
        """将隐写文本框内容同步回普通文本框"""
        if self._syncing_text:
            return
        try:
            self._syncing_text = True
            src = self.stealth_text.get("1.0", "end-1c")
            dst = self.text.get("1.0", "end-1c")
            if src != dst:
                cur = self.stealth_text.index("insert")
                self.text.delete("1.0", "end")
                self.text.insert("1.0", src)
                self.text.mark_set("insert", cur)
                if self.cfg['read_mode']:
                    self.root.after(50, self._apply_read_mode_bg)
            self._refresh_stealth_view()
        except Exception as e:
            print(f"[隐写同步] from stealth 失败: {e}")
        finally:
            self._syncing_text = False

    def _calc_stealth_window_height(self):
        """精确计算隐写模式下窗口的总高度。

        使用 stealth_text 的实际渲染字体计算 linespace，避免新建 Font 对象
        与实际渲染字体不一致导致行高偏差和半行显示。
        """
        lines = self.cfg.get('stealth_lines', 3)
        try:
            # 使用 stealth_text 的实际字体，而非新建 Font 对象
            font_str = self.stealth_text.cget("font")
            f = tkfont.Font(font=font_str)
            line_height = f.metrics("linespace")
        except Exception:
            line_height = int(self.cfg['text_size'] * 1.6)

        text_height = line_height * lines
        # 容器上下边距（隐写模式已缩小到 20%）+ 横线总高 2px
        return text_height + STEALTH_PAD_Y * 2 + 2

    def _set_stealth_lines(self, lines):
        self.cfg['stealth_lines'] = clamp(lines, 1, 3)
        # 同步 IntVar，更新菜单 radiobutton 选中状态
        if hasattr(self, '_stealth_lines_var'):
            self._stealth_lines_var.set(self.cfg['stealth_lines'])
        self.stealth_text.configure(height=self.cfg['stealth_lines'])
        if self.cfg.get('stealth_mode'):
            self.stealth_text.update_idletasks()
            self._refresh_stealth_view()
            new_h = self._calc_stealth_window_height()
            wx = self.root.winfo_x()
            wy = self.root.winfo_y()
            self.root.geometry(f"{self.root.winfo_width()}x{new_h}")
            self.content_win.geometry(f"{self.root.winfo_width()}x{new_h}")
            self.bg_win.geometry(f"{self.root.winfo_width()}x{new_h}")
            self.content_win.update_idletasks()
            self._corner_dirty = True
            self._update_corners()
            self._layout_handle()
        self._save_config_debounced()

    def _refresh_stealth_view(self):
        """根据光标所在视觉行刷新隐写文本框的显示范围与分隔线。

        B19 修复：使用 dlineinfo("insert") 获取光标所在视觉行的像素位置，
        直接像素级滚动对齐，解决 word wrap 时光标行不同步上移的问题。

        核心逻辑：
        1. 先 see("insert") 确保光标行可见
        2. 用 dlineinfo("insert") 获取光标行的视觉 Y 位置和行高
        3. 根据模式计算目标 Y 位置（光标行应在的 Y 位置）
           - 一行模式：光标行在顶部 (target_y = 0)
           - 两行模式：光标行在底部 (target_y = line_height)
           - 三行模式：光标行在中间 (target_y = line_height * 2)
        4. 用 yview_scroll 像素级滚动，将光标行精确对齐到目标位置
        """
        if not self.cfg.get('stealth_mode') or not self.stealth_text.winfo_exists():
            return
        try:
            widget = self.stealth_text if self.root.focus_get() == self.stealth_text else self.text
            cur = widget.index("insert")

            mode = self.cfg['stealth_lines']

            # Step 1: 确保光标行可见
            self.stealth_text.see("insert")
            self.stealth_text.update_idletasks()

            # Step 2: 获取光标所在视觉行的像素位置
            bbox = self.stealth_text.dlineinfo("insert")
            if not bbox:
                self.root.after(20, self._refresh_stealth_view)
                return

            _, y, _, h, _ = bbox
            line_height = h if h > 0 else 1

            # Step 3: 计算目标 Y 位置（光标行应在的 Y 位置）
            if mode == 1:
                # 一行模式：光标行在顶部
                target_y = 0
            elif mode == 2:
                # 两行模式：光标行在底部，上一视觉行在顶部
                target_y = line_height
            else:
                # 三行模式：光标行在中间，上两视觉行在顶部
                target_y = line_height * 2

            # Step 4: 像素级滚动对齐
            # delta > 0: 光标行在目标位置下方，需要向下滚动（内容上移）
            # delta < 0: 光标行在目标位置上方，需要向上滚动（内容下移）
            delta = y - target_y
            if abs(delta) > 0:
                self.stealth_text.yview_scroll(delta, "pixels")

            # 保持光标位置
            self.stealth_text.mark_set("insert", cur)

            self.root.after(10, self._update_stealth_line)
        except Exception as e:
            print(f"[隐写视图] 刷新失败: {e}")

    def _update_stealth_line(self):
        """在光标所在行下方绘制与文本框等宽的横线（缺省 1px 黑线 + 1px 白线叠合）"""
        if not self.cfg.get('stealth_mode') or not self.stealth_text.winfo_exists():
            self._stealth_line_container.place_forget()
            self._stealth_line_visible = False
            return
        try:
            self.stealth_text.update_idletasks()
            self.content_frame.update_idletasks()

            bbox = self.stealth_text.dlineinfo("insert")
            if not bbox:
                self.root.after(20, self._update_stealth_line)
                return
            _, y, _, h, _ = bbox
            # 横线在 content_frame 上的 y：容器上边距 + 光标行底部
            line_y = STEALTH_PAD_Y + y + h

            # 宽度 = content_frame 宽度 - 左右各 TEXT_PAD_X
            fw = self.content_frame.winfo_width()
            if fw <= 1:
                fw = self.root.winfo_width()
            if fw <= 1:
                fw = 600
            width = max(1, fw - TEXT_PAD_X * 2)

            # 同时设置 configure(width=...) 和 place(width=...) 确保宽度生效
            self._stealth_line_container.configure(width=width)
            self._stealth_line_container.place(x=TEXT_PAD_X, y=line_y, width=width)
            self._stealth_line_container.update_idletasks()
            self._stealth_line_container.lift()
            self._stealth_line_visible = True
        except Exception as e:
            print(f"[隐写线] 更新失败: {e}")

    def _on_stealth_wheel(self, event):
        """隐写文本框滚轮：累积 delta，每满 120 移动光标一行并刷新视图。"""
        if self._is_left_button_held():
            delta = 1 if event.delta > 0 else -1
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            self.cfg['bg_opacity'] = round(new_op, 2)
            self._apply_window_style()
            self._save_config_debounced()
            return "break"

        widget = self.stealth_text
        self._stealth_wheel_acc += event.delta
        threshold = 120

        try:
            lines = 0
            while self._stealth_wheel_acc >= threshold:
                lines -= 1
                self._stealth_wheel_acc -= threshold
            while self._stealth_wheel_acc <= -threshold:
                lines += 1
                self._stealth_wheel_acc += threshold

            if lines == 0:
                return "break"

            cur = widget.index("insert")
            line = int(cur.split(".")[0])
            total = int(widget.index("end-1c").split(".")[0])
            if total <= 0:
                total = 1
            new_line = max(1, min(total, line + lines))
            widget.mark_set("insert", f"{new_line}.0")
            widget.see("insert")
            self._refresh_stealth_view()
        except Exception:
            pass
        return "break"

    def toggle_stealth(self, lines=None):
        """切换隐写模式。文本框集群与隐写框集群互斥切换，左上角锚定，宽度不变。"""
        self.cfg['stealth_mode'] = not self.cfg.get('stealth_mode', False)
        if lines is not None:
            self.cfg['stealth_lines'] = clamp(lines, 1, 3)

        wx = self.root.winfo_x()
        wy = self.root.winfo_y()
        ww = self.root.winfo_width()

        if self.cfg['stealth_mode']:
            # 保存当前窗口高度（用于恢复）
            self._normal_window_height = self.root.winfo_height()

            # 同步内容和光标
            content = self.text.get("1.0", "end-1c")
            cur = self.text.index("insert")
            self.stealth_text.configure(height=self.cfg['stealth_lines'])
            self.stealth_text.delete("1.0", "end")
            self.stealth_text.insert("1.0", content)
            self.stealth_text.mark_set("insert", cur)

            # 切换容器：隐藏文本框集群，显示隐写框集群
            self.text_container.pack_forget()
            self.sb_container.place_forget()
            self.stealth_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=STEALTH_PAD_Y)

            # 调整窗口高度（左上角锚定，宽度不变）
            self.stealth_text.update_idletasks()
            new_h = self._calc_stealth_window_height()
            self.root.geometry(f"{ww}x{new_h}")
            self.content_win.geometry(f"{ww}x{new_h}")
            self.bg_win.geometry(f"{ww}x{new_h}")
            self.content_win.update_idletasks()

            self.stealth_text.focus_set()
            self._corner_dirty = True
            self._update_corners()
            self._refresh_stealth_view()
        else:
            # 退出隐写模式：先同步内容
            try:
                content = self.stealth_text.get("1.0", "end-1c")
                cur = self.stealth_text.index("insert")
                if content != self.text.get("1.0", "end-1c"):
                    self.text.delete("1.0", "end")
                    self.text.insert("1.0", content)
                self.text.mark_set("insert", cur)
            except Exception:
                pass

            # 切换容器：隐藏隐写框集群，显示文本框集群
            self.stealth_container.pack_forget()
            self._stealth_line_container.place_forget()
            self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)

            # 恢复窗口高度
            if self._normal_window_height and self._normal_window_height > MIN_WINDOW_H:
                new_h = self._normal_window_height
            else:
                new_h = max(MIN_WINDOW_H, self.cfg.get('window_height', 400))
            self.root.geometry(f"{ww}x{new_h}")
            self.content_win.geometry(f"{ww}x{new_h}")
            self.bg_win.geometry(f"{ww}x{new_h}")

            self.text.focus_set()
            self._corner_dirty = True
            self._update_corners()
            if self.cfg['show_scrollbar']:
                self._set_scrollbar_visible(self._sb_visible)

        self._apply_text_appearance()
        self._update_panel_button_states()
        self._layout_handle()
        self._save_config_debounced()

    def _apply_stealth_state(self):
        """根据当前 cfg 应用隐写模式状态（不修改配置，仅恢复显示）"""
        try:
            visible = self.cfg.get('stealth_mode', False)
            lines = self.cfg.get('stealth_lines', 3)
            self.stealth_text.configure(height=lines)

            if visible:
                # 进入隐写模式
                if self.text_container.winfo_manager() == "pack":
                    self.text_container.pack_forget()
                self.sb_container.place_forget()
                if not self._is_stealth_container_visible():
                    self.stealth_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=STEALTH_PAD_Y)
                    self.stealth_container.update_idletasks()
                    self._stealth_line_container.lift()

                content = self.text.get("1.0", "end-1c")
                cur = self.text.index("insert")
                self.stealth_text.delete("1.0", "end")
                self.stealth_text.insert("1.0", content)
                self.stealth_text.mark_set("insert", cur)

                # 调整窗口高度
                self.stealth_text.update_idletasks()
                ww = self.root.winfo_width()
                new_h = self._calc_stealth_window_height()
                self.root.geometry(f"{ww}x{new_h}")
                self.content_win.geometry(f"{ww}x{new_h}")
                self.bg_win.geometry(f"{ww}x{new_h}")
                self.content_win.update_idletasks()
                self._corner_dirty = True
                self._update_corners()

                self.root.after(10, lambda: (
                    self.stealth_text.focus_set(),
                    self._refresh_stealth_view(),
                    self._layout_handle()
                ))
            else:
                # 普通文本框模式
                if self._is_stealth_container_visible():
                    try:
                        content = self.stealth_text.get("1.0", "end-1c")
                        cur = self.stealth_text.index("insert")
                        if content != self.text.get("1.0", "end-1c"):
                            self.text.delete("1.0", "end")
                            self.text.insert("1.0", content)
                        self.text.mark_set("insert", cur)
                    except Exception:
                        pass
                    self.stealth_container.pack_forget()
                    self._stealth_line_container.place_forget()
                if self.text_container.winfo_manager() != "pack":
                    self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)
                if self.cfg['show_scrollbar']:
                    self._set_scrollbar_visible(self._sb_visible)
                self.text.focus_set()
            self._apply_text_appearance()
            self._update_panel_button_states()
        except Exception as e:
            print(f"[隐写状态] 应用失败: {e}")
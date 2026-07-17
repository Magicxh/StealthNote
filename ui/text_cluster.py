# -*- coding: utf-8 -*-
"""Stealth Note - 文本框集群模块（TextClusterMixin）"""
import tkinter as tk
from tkinter import font as tkfont
from constants import *
from utils import mix_color, clamp, invert_color

class TextClusterMixin:
    """文本框集群 Mixin：文本框、滚动条、外观"""

    def _init_content(self):
        """初始化内容层窗口：content_win 使用 LWA_ALPHA | LWA_COLORKEY 统一半透明，
        所有子元素 bg=raw_bg 实色，保证文本交互顺滑且无黑底色差。
        关键：四角画布/热区在文本容器之前创建，确保天然位于文本之下，不会遮挡文字。"""
        raw_bg = self.cfg['bg_color']

        # ===== 内容窗口 content_win：LWA_ALPHA | LWA_COLORKEY =====
        self.content_win = tk.Toplevel(self.root)
        self.content_win.withdraw()
        self.content_win.overrideredirect(True)
        self.content_win.configure(bg=raw_bg, bd=0, highlightthickness=0)
        self.content_win.attributes("-topmost", True)

        # v2.9.7: 立即设置所有者为 host_win，防止出现在任务栏
        self.content_win.update_idletasks()
        self._content_hwnd = self.content_win.winfo_id()
        self._set_window_owner(self._content_hwnd, self._host_hwnd)

        self.content_frame = tk.Frame(self.content_win, bg=raw_bg, bd=0, highlightthickness=0)
        self.content_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # ===== 四角框线画布和热区 =====
        # 在文本容器之前创建，确保自然位于文本之下，彻底避免遮挡文字
        self._corner_frames = {}      # 14x14 缩放热区
        self._corner_canvases = {}    # 独立视觉画布，绘制单个角的框线
        self._corner_bg_canvas = None

        corners = [
            ("nw", "top_left_corner"),
            ("ne", "top_right_corner"),
            ("sw", "bottom_left_corner"),
            ("se", "bottom_right_corner"),
        ]

        for name, cursor in corners:
            # 热区：仅保留角落 14x14，用于触发缩放
            frame = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0)
            frame.bind("<ButtonPress-1>", lambda e, n=name: self._on_resize_start(e, n))
            frame.bind("<B1-Motion>", self._on_resize)
            frame.bind("<ButtonRelease-1>", self._on_resize_end)
            frame.bind("<Motion>", self._on_content_motion)

            # 视觉画布：独立绘制单个角的框线
            canvas = tk.Canvas(self.content_frame, bg=raw_bg, highlightthickness=0, bd=0, cursor=cursor)
            canvas.bind("<ButtonPress-1>", lambda e, n=name: self._on_resize_start(e, n))
            canvas.bind("<B1-Motion>", self._on_resize)
            canvas.bind("<ButtonRelease-1>", self._on_resize_end)
            canvas.bind("<Motion>", self._on_content_motion)

            self._corner_frames[name] = frame
            self._corner_canvases[name] = canvas

        self.text_container = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0)
        self.text_container.pack(fill="both", expand=True, padx=TEXT_PAD_X, pady=TEXT_PAD_Y)

        self.text = tk.Text(
            self.text_container,
            bg=raw_bg,
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            selectbackground="#3399FF",
            selectforeground="#FFFFFF",
            font=("Microsoft YaHei UI", 12),
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=6,
            pady=6,
            undo=True,
            maxundo=100,
            exportselection=True,
        )
        self.text.pack(side="left", fill="both", expand=True)

        # ===== 隐写框集群 =====
        # 隐写容器：独立于文本框容器，切换模式时显示/隐藏
        self.stealth_container = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0)

        # 隐写文本框：无框，继承普通文本框样式，宽度填充，高度由行数决定
        # 垂直内边距设为 0，确保 winfo_reqheight / metrics 能精确对应行数
        self.stealth_text = tk.Text(
            self.stealth_container,
            bg=raw_bg,
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            selectbackground="#3399FF",
            selectforeground="#FFFFFF",
            font=("Microsoft YaHei UI", 12),
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=6,
            pady=0,
            undo=True,
            maxundo=100,
            height=3,
            exportselection=True,
        )
        # 顶部锚定，确保单行模式下文本位于容器顶端，横线可正确绘制在文字下方
        # fill="both", expand=True 确保文本框填满整个容器，右半部分可正常点击
        self.stealth_text.pack(side="left", fill="both", expand=True, anchor="n")
        # 隐写行分隔线（视觉提示：光标所在行下方）
        # 采用 1px 黑线 + 1px 白线上下叠合，总高度 2px
        # 放置在 content_frame 上，避免容器 padx 影响坐标计算
        self._stealth_line_container = tk.Frame(self.content_frame, bg="#000000", height=2, width=1)
        self._stealth_line_black = tk.Frame(self._stealth_line_container, bg="#000000", height=1)
        self._stealth_line_black.pack(side="top", fill="x", expand=False)
        self._stealth_line_white = tk.Frame(self._stealth_line_container, bg="#FFFFFF", height=1)
        self._stealth_line_white.pack(side="top", fill="x", expand=False)
        self._stealth_line_container.place_forget()
        self._stealth_line_visible = False

        # 保存切换前的窗口高度（用于从隐写模式返回时恢复）
        self._normal_window_height = None

        # 自定义滚动条
        self.sb_container = tk.Frame(self.content_frame, bg=raw_bg, bd=0, highlightthickness=0,
                                     width=SCROLLBAR_WIDTH + SCROLLBAR_PAD_RIGHT * 2)
        self.sb_container.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0, relheight=1.0)

        self._sb_canvas = tk.Canvas(self.sb_container, bg=raw_bg, highlightthickness=0, bd=0,
                                    width=SCROLLBAR_WIDTH)
        self._sb_canvas.pack(side="right", fill="y", padx=(0, SCROLLBAR_PAD_RIGHT))

        self._sb_visible = False

        self.text.configure(yscrollcommand=self._on_scroll)

        self._sb_canvas.bind("<ButtonPress-1>", self._on_sb_press)
        self._sb_canvas.bind("<B1-Motion>", self._on_sb_drag)
        self._sb_canvas.bind("<Enter>", lambda e: self._sb_hover(True))
        self._sb_canvas.bind("<Leave>", lambda e: self._sb_hover(False))

        self._set_scrollbar_visible(False)

        self.text.focus_set()
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.stealth_text.bind("<<Modified>>", self._on_stealth_text_modified)

        # 文本框背景已改为实色，恢复原生鼠标/键盘交互。
        # 仅保留隐写视图同步和滚轮增强，不再模拟点击/拖拽选区。
        for widget in (self.text, self.stealth_text):
            # 键盘输入/光标移动后同步隐写视图
            widget.bind("<KeyRelease>", self._on_text_cursor_moved)
            # 鼠标释放后刷新隐写视图（仅隐写模式生效）
            widget.bind("<ButtonRelease-1>", self._on_text_button_release)

        # 普通文本框：绑定滚轮滚动（Tkinter Text 在 Windows 上无原生滚轮支持）
        self.text.bind("<MouseWheel>", self._on_text_wheel_smooth)
        # 普通文本框容器空白区：转发滚轮给文本框
        self.text_container.bind("<MouseWheel>", lambda e: self._route_wheel_to_text(e, self.text))

        # 隐写文本框：滚轮用于移动光标/行
        self.stealth_text.bind("<MouseWheel>", self._on_stealth_wheel)
        self.stealth_container.bind("<MouseWheel>", lambda e: self._route_wheel_to_text(e, self.stealth_text))

        # 右键菜单改为释放时弹出（支持右键+滚轮调透明度）
        self.text.bind("<Button-3>", self._on_text_right_press)
        self.text.bind("<ButtonRelease-3>", self._on_text_right_release)
        self.stealth_text.bind("<Button-3>", self._on_text_right_press)
        self.stealth_text.bind("<ButtonRelease-3>", self._on_text_right_release)

        # 创建隐写行数 IntVar（供菜单 radiobutton 使用）
        self._stealth_lines_var = tk.IntVar(value=self.cfg.get('stealth_lines', 3))

        self._create_context_menu()

        self.content_win.update_idletasks()
        # 立即设置 WS_EX_TOOLWINDOW + LWA_ALPHA | LWA_COLORKEY
        try:
            _content_hwnd = self.content_win.winfo_id()
            ex_style = user32.GetWindowLongW(_content_hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(_content_hwnd, GWL_EXSTYLE, ex_style)
            # LWA_ALPHA | LWA_COLORKEY：alpha 控制整体半透明，COLORKEY(#010101) 穿透
            # Text bg=raw_bg 实色，原生交互顺滑，抗锯齿相对于 raw_bg 无毛边
            user32.SetLayeredWindowAttributes(_content_hwnd, COLORKEY_INT, 255, LWA_ALPHA | LWA_COLORKEY)
        except Exception:
            pass
        self.content_win.deiconify()

        # 内容窗口也需要响应四角缩放与滚轮（根窗口可能被内容窗口遮挡）
        self.content_win.bind("<ButtonPress-1>", self._on_content_button_press)
        self.content_win.bind("<B1-Motion>", self._on_content_resize)
        self.content_win.bind("<ButtonRelease-1>", self._on_content_resize_end)
        self.content_win.bind("<Motion>", self._on_content_motion)
        self.content_win.bind("<MouseWheel>", self._on_root_wheel)

    def _is_stealth_container_visible(self):
        """判断隐写框容器当前是否处于显示状态（从布局管理器派生，避免状态不一致）"""
        try:
            return self.stealth_container.winfo_manager() == "pack"
        except Exception:
            return False

    def _calc_bg_color(self):
        """计算当前应显示的背景色（考虑易读模式、反色模式和透明度）。

        根窗口使用 LWA_ALPHA 实现真实半透明，因此这里返回原始背景色（含反色），
        由 Windows 的 alpha 通道负责透明度混合。若再预乘一次透明度，会导致文本区
        域双重变暗、呈现不自然的黑色底色。
        """
        if self.cfg['read_mode']:
            return COLORKEY
        else:
            bg = self.cfg['bg_color']
            if self.cfg['invert_mode']:
                bg = invert_color(bg)
            return bg

    def _apply_text_appearance(self):
        """应用文本外观设置（v2.7.3 双层架构）。

        content_win 使用 LWA_ALPHA | LWA_COLORKEY 统一半透明。
        文字颜色通过 mix_color 预乘 text_opacity，背景透明度由 content_win 的 LWA_ALPHA 控制。
        """
        # 保存当前滚动位置，防止 configure 时重置
        try:
            scroll_pos = self.text.yview()
        except Exception:
            scroll_pos = (0.0, 1.0)

        # 原始背景色（content_win 的 LWA_ALPHA 负责实际半透明）
        raw_bg = self.cfg['bg_color']
        if self.cfg['invert_mode']:
            raw_bg = invert_color(raw_bg)

        # 文字颜色：预乘 text_opacity
        tc = self.cfg['text_color']
        if self.cfg['invert_mode']:
            tc = invert_color(tc)
        fg_op = self.cfg['text_opacity']
        fg_color = mix_color(tc, fg_op, raw_bg)

        # 更醒目的选区颜色
        sel_bg = mix_color("#3399FF", 0.85, raw_bg)
        sel_fg = "#FFFFFF"

        # 文本框背景：易读模式下用 COLORKEY（被 LWA_COLORKEY 透明化），
        # 普通模式下用 raw_bg 实色（content_win 的 LWA_ALPHA 控制透明度）
        if self.cfg['read_mode']:
            text_bg = COLORKEY
            stealth_bg = COLORKEY
            container_bg = COLORKEY
        else:
            text_bg = raw_bg
            stealth_bg = raw_bg
            container_bg = raw_bg

        self.text.configure(
            bg=text_bg,
            fg=fg_color,
            insertbackground=fg_color,
            selectbackground=sel_bg,
            selectforeground=sel_fg,
            font=(self.cfg['text_font'], self.cfg['text_size'])
        )
        if hasattr(self, 'stealth_text') and self.stealth_text:
            self.stealth_text.configure(
                bg=stealth_bg,
                fg=fg_color,
                insertbackground=fg_color,
                selectbackground=sel_bg,
                selectforeground=sel_fg,
                font=(self.cfg['text_font'], self.cfg['text_size'])
            )

        # 容器背景：易读模式下用 COLORKEY，普通模式下用 raw_bg
        if hasattr(self, 'text_container') and self.text_container:
            self.text_container.configure(bg=container_bg)
        if hasattr(self, 'stealth_container') and self.stealth_container:
            self.stealth_container.configure(bg=container_bg)
        # content_win 和 content_frame 也需同步背景色
        if hasattr(self, 'content_win') and self.content_win:
            self.content_win.configure(bg=container_bg)
        if hasattr(self, 'content_frame') and self.content_frame:
            self.content_frame.configure(bg=container_bg)
        # 四角画布和热区也需同步
        if hasattr(self, '_corner_frames'):
            for f in self._corner_frames.values():
                try:
                    f.configure(bg=container_bg)
                except Exception:
                    pass
        if hasattr(self, '_corner_canvases'):
            for c in self._corner_canvases.values():
                try:
                    c.configure(bg=container_bg)
                except Exception:
                    pass

        # 易读模式背景
        if self.cfg['read_mode']:
            # v2.9.8.5: 取消挂起的防抖回调，避免直接调用后旧回调又触发一次冗余执行
            if getattr(self, '_read_bg_after_id', None):
                try:
                    self.root.after_cancel(self._read_bg_after_id)
                except Exception:
                    pass
                self._read_bg_after_id = None
            self._apply_read_mode_bg()
        else:
            try:
                self.text.tag_remove("read_bg", "1.0", "end")
                if hasattr(self, 'stealth_text') and self.stealth_text:
                    self.stealth_text.tag_remove("read_bg", "1.0", "end")
            except Exception:
                pass

        # 隐写模式下字号变化时同步更新窗口高度
        if self.cfg.get('stealth_mode') and hasattr(self, 'stealth_container') and self._is_stealth_container_visible():
            ww = self.content_win.winfo_width()
            new_h = self._calc_stealth_window_height()
            root_y_offset = self._get_handle_root_y_offset() if hasattr(self, '_get_handle_root_y_offset') else 0
            if abs(new_h - (self.root.winfo_height() - root_y_offset)) > 2:
                offset = self._get_handle_offset() if hasattr(self, '_get_handle_offset') else 0
                self.root.geometry(f"{ww + offset}x{new_h + root_y_offset}")
                self.root.update_idletasks()
                self.content_win.geometry(f"{ww}x{new_h}")
                self._corner_dirty = True
                self._update_corners()
                self._layout_handle()

        if self._sb_visible:
            self._redraw_scrollbar()

        # B22: 恢复滚动位置
        try:
            self.text.yview_moveto(scroll_pos[0])
        except Exception:
            pass

        # v2.9.8: 同步标题栏外观（反色/颜色/透明度变化时确保标题栏同步）
        if hasattr(self, '_update_titlebar_appearance'):
            self._update_titlebar_appearance()
        # v2.9.8: 同步状态栏外观（反色/颜色/透明度变化时确保状态栏同步）
        if hasattr(self, '_update_statusbar_appearance'):
            self._update_statusbar_appearance()

    def _apply_read_mode_bg(self):
        """易读模式 — 仅在有文字的行显示背景色。

        v2.9.8: content_win 使用 LWA_ALPHA | LWA_COLORKEY，alpha = read_bg_opacity * 255。
        read_bg tag 使用纯 read_bg_color（不再混合 raw_bg），透明度由 LWA_ALPHA 统一控制。
        COLORKEY 区域（空行）全透明，有文字行半透明。
        """
        self._read_bg_after_id = None
        try:
            row_bg = self.cfg['read_bg_color']
            if self.cfg['invert_mode']:
                row_bg = invert_color(row_bg)
            # 直接使用 read_bg_color 纯色，透明度由 content_win 的 LWA_ALPHA 控制
            for widget in [self.text, getattr(self, 'stealth_text', None)]:
                if not widget or not widget.winfo_exists():
                    continue
                widget.tag_remove("read_bg", "1.0", "end")
                widget.tag_configure("read_bg", background=row_bg)
                count = int(widget.index("end-1c").split(".")[0])
                for i in range(1, count + 1):
                    line_start = f"{i}.0"
                    line_end = f"{i}.end"
                    line_text = widget.get(line_start, line_end)
                    if line_text.strip():
                        widget.tag_add("read_bg", line_start, line_end)
        except Exception as e:
            print(f"[易读模式] 应用失败: {e}")

    # -------------------------------------------------------------------------
    # 滚动条
    # -------------------------------------------------------------------------

    def _sb_hover(self, entering):
        self._redraw_scrollbar(highlight=entering)

    def _on_scroll(self, *args):
        need_scroll = not (float(args[0]) <= 0.0 and float(args[1]) >= 1.0)
        if self.cfg['show_scrollbar'] and need_scroll:
            self._set_scrollbar_visible(True)
            self._update_scrollbar_thumb(float(args[0]), float(args[1]))
        else:
            self._set_scrollbar_visible(False)

    def _set_scrollbar_visible(self, visible):
        if visible == self._sb_visible:
            return
        self._sb_visible = visible
        if visible:
            self.sb_container.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0, relheight=1.0)
            self._redraw_scrollbar()
        else:
            self.sb_container.place_forget()

    def _update_scrollbar_thumb(self, first, last):
        self._sb_first = first
        self._sb_last = last
        self._redraw_scrollbar()

    def _redraw_scrollbar(self, highlight=False):
        canvas = self._sb_canvas
        canvas.delete("all")
        if not self._sb_visible:
            return

        w = SCROLLBAR_WIDTH
        h = canvas.winfo_height()
        if h < 10:
            return

        cs = max(MIN_CORNER_LEN, self.cfg['corner_size'])
        margin_top = cs + 4
        margin_bottom = cs + 4
        track_top = margin_top
        track_bottom = h - margin_bottom
        track_h = track_bottom - track_top

        if track_h < 20:
            return

        first = getattr(self, '_sb_first', 0.0)
        last = getattr(self, '_sb_last', 1.0)
        thumb_h = max(20, int(track_h * (last - first)))
        thumb_y = track_top + int(track_h * first)

        base_color = self.cfg['corner_color']
        if self.cfg['invert_mode']:
            base_color = invert_color(base_color)

        track_color = mix_color(base_color, 0.2, "#000000")
        thumb_color = mix_color(base_color, 0.6 if not highlight else 0.9, "#000000")

        canvas.create_rectangle(
            w // 2 - 1, track_top, w // 2 + 1, track_bottom,
            fill=track_color, outline="")

        canvas.create_rectangle(
            0, thumb_y, w, thumb_y + thumb_h,
            fill=thumb_color, outline="")

        self._sb_thumb_y = thumb_y
        self._sb_thumb_h = thumb_h
        self._sb_track_top = track_top
        self._sb_track_bottom = track_bottom

    def _on_sb_press(self, event):
        if not hasattr(self, '_sb_thumb_y'):
            return
        if self._sb_thumb_y <= event.y <= self._sb_thumb_y + self._sb_thumb_h:
            self._sb_drag_start_y = event.y
            self._sb_drag_start_first = getattr(self, '_sb_first', 0.0)
        else:
            delta = 1.0 if event.y > self._sb_thumb_y else -1.0
            self.text.yview_scroll(int(delta), "pages")

    def _on_sb_drag(self, event):
        if not hasattr(self, '_sb_drag_start_y'):
            return
        track_h = self._sb_track_bottom - self._sb_track_top
        if track_h <= 0:
            return
        dy = event.y - self._sb_drag_start_y
        ratio = dy / track_h
        new_first = clamp(self._sb_drag_start_first + ratio, 0.0, 1.0)
        self.text.yview_moveto(new_first)

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="撤销", command=lambda: self.text.event_generate("<<Undo>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="剪切", command=lambda: self.text.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="复制", command=lambda: self.text.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="粘贴", command=lambda: self.text.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="删除", command=lambda: self.text.delete("sel.first", "sel.last"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="全选", command=lambda: self.text.event_generate("<<SelectAll>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="隐写模式" if not self.cfg.get('stealth_mode') else "退出隐写模式",
            command=self.toggle_stealth)
        self.context_menu.add_separator()
        # 隐写行数选择：radiobutton 自带选中指示器，无需额外图标
        for lines, label in [(1, "一行模式"), (2, "两行模式"), (3, "三行模式")]:
            self.context_menu.add_radiobutton(
                label=label,
                value=lines,
                variable=self._stealth_lines_var,
                command=lambda n=lines: self._set_stealth_lines(n))
        # 右键菜单绑定已移至 _init_content（改为释放时弹出）
        # self.text.bind("<Button-3>", self._show_context_menu)
        # self.stealth_text.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        try:
            label = "退出隐写模式" if self.cfg.get('stealth_mode') else "隐写模式"
            try:
                self.context_menu.entryconfigure("隐写模式", label=label)
                self.context_menu.entryconfigure("退出隐写模式", label=label)
            except Exception:
                pass
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_text_modified(self, event):
        if self.text.edit_modified():
            self._modified = True
            # 暂存模式触发检测：新文件（current_file is None）+ 有实际内容 → 进入暂存模式
            if not self.current_file and not self._autosave_mode:
                content = self.text.get("1.0", "end-1c").strip()
                if content:
                    self._enter_autosave_mode()
            elif self._autosave_mode:
                # 暂存模式下有新改动，标记为未保存
                self._autosave_dirty = True
            self._update_title()
            # v2.9.8: 同步状态栏字数显示
            # v2.9.8.5: 80ms 防抖，避免每次按键触发 O(N) 全文读取+Canvas重绘
            if hasattr(self, '_update_statusbar_text'):
                if getattr(self, '_statusbar_text_after_id', None):
                    try:
                        self.root.after_cancel(self._statusbar_text_after_id)
                    except Exception:
                        pass
                self._statusbar_text_after_id = self.root.after(80, self._do_update_statusbar_text)
            self.text.edit_modified(False)
            if self.cfg['read_mode']:
                # 防抖：取消旧的 after 回调，避免快速输入时回调堆积
                if getattr(self, '_read_bg_after_id', None):
                    try:
                        self.root.after_cancel(self._read_bg_after_id)
                    except Exception:
                        pass
                self._read_bg_after_id = self.root.after(50, self._apply_read_mode_bg)
            if self.cfg.get('stealth_mode'):
                self.root.after(10, self._sync_to_stealth)

    def _do_update_statusbar_text(self):
        """v2.9.8.5: 状态栏字数更新实际执行（防抖回调）"""
        self._statusbar_text_after_id = None
        if hasattr(self, '_update_statusbar_text'):
            self._update_statusbar_text()

    def _on_stealth_text_modified(self, event):
        if self.stealth_text.edit_modified():
            self._modified = True
            self._update_title()
            # v2.9.8: 同步状态栏字数显示
            # v2.9.8.5: 80ms 防抖
            if hasattr(self, '_update_statusbar_text'):
                if getattr(self, '_statusbar_text_after_id', None):
                    try:
                        self.root.after_cancel(self._statusbar_text_after_id)
                    except Exception:
                        pass
                self._statusbar_text_after_id = self.root.after(80, self._do_update_statusbar_text)
            self.stealth_text.edit_modified(False)
            self.root.after(10, self._sync_from_stealth)

    def _on_text_button_release(self, event):
        """鼠标释放后刷新隐写视图。"""
        if self.cfg.get('stealth_mode'):
            self.root.after(10, self._refresh_stealth_view)

    def _on_text_cursor_moved(self, event):
        """键盘导致光标/选区变化时保持隐写视图同步"""
        if self.cfg.get('stealth_mode'):
            self.root.after(10, self._refresh_stealth_view)

    def _update_title(self):
        if self.current_file:
            name = os.path.basename(self.current_file)
            mark = "*" if self._modified else ""
            title = f"{mark}{name} - {APP_NAME} [{self.current_encoding}]"
        else:
            mark = "*" if self._modified else ""
            title = f"{mark}未命名 - {APP_NAME}"
        self.root.title(title)
        # 同步任务栏标题
        if hasattr(self, '_taskbar_host') and self._taskbar_host:
            self._taskbar_host.set_title(title)
        # 同步标题栏文字
        if hasattr(self, '_refresh_titlebar'):
            self._refresh_titlebar()

    def _focus_text(self):
        try:
            if self.cfg.get('stealth_mode') and self.stealth_text.winfo_viewable():
                self.stealth_text.focus_set()
            else:
                self.text.focus_set()
        except Exception:
            pass

    def _on_text_wheel_smooth(self, event):
        """文本框滚轮：右键按下时调整背景透明度，左键按下时屏蔽，否则顺滑滚动文本"""
        # 左键按下时屏蔽滚轮
        if self._is_left_button_held():
            return "break"
        # 右键按下时滚轮调整背景透明度
        if self._is_right_button_held():
            self._right_button_wheel_used = True
            delta = 1 if event.delta > 0 else -1
            new_op = max(0.0, min(1.0, self.cfg['bg_opacity'] + delta * 0.08))
            self.cfg['bg_opacity'] = round(new_op, 2)
            self._apply_window_style_debounced()
            self._save_config_debounced()
            return "break"

        widget = event.widget
        if widget not in (self.text, self.stealth_text):
            return None
        # 每次滚轮事件精确滚动一行，避免步进过大导致隐写框出现半行或横线跳动
        lines = -1 if event.delta > 0 else 1
        widget.yview_scroll(lines, "units")
        return "break"

    def _on_text_right_press(self, event):
        """右键按下：记录状态，不立即弹菜单"""
        self._right_button_wheel_used = False

    def _on_text_right_release(self, event):
        """右键释放：如果期间没有滚轮操作，弹出上下文菜单"""
        if not getattr(self, '_right_button_wheel_used', False):
            self._show_context_menu(event)

    def _route_wheel_to_text(self, event, text_widget):
        """在容器/空白区域滚动时，将事件转发给对应文本框"""
        if not text_widget.winfo_exists():
            return None
        event.widget = text_widget
        if text_widget is self.stealth_text:
            return self._on_stealth_wheel(event)
        return self._on_text_wheel_smooth(event)
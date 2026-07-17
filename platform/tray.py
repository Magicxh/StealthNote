# -*- coding: utf-8 -*-
"""Stealth Note - 系统托盘模块"""
import os
import threading
from constants import APP_NAME
from utils import create_app_icon


class TrayIcon:
    """系统托盘图标：始终存在，左键切换显示/隐藏，右键菜单。

    v2.9.8.4: 托盘右键菜单与圆形手柄右键菜单保持一致。
    所有动作通过 root.after(0, ...) 转发到主线程执行。
    """

    def __init__(self, app):
        self.app = app
        self.icon = None
        self._init()

    def _init(self):
        """初始化系统托盘（在独立线程中运行）"""
        try:
            import pystray
            from pystray import Icon as PystrayIcon, Menu as TrayMenu, MenuItem as TrayItem
            print("[托盘] pystray导入成功")
        except Exception as e:
            print(f"[托盘] pystray导入失败: {e}")
            self.icon = None
            return

        try:
            # ===== 菜单项回调（按手柄菜单顺序） =====
            def _after(fn):
                """转发到主线程执行"""
                self.app.root.after(0, fn)

            def on_show_hide(icon, item):
                _after(self._toggle)

            def on_panel_locked(icon, item):
                _after(self.app._toggle_panel_locked)

            def on_open(icon, item):
                _after(self.app.file_open)

            def on_save(icon, item):
                _after(self.app.file_save)

            def on_load_autosave(icon, item):
                _after(self.app._load_autosave)

            def on_stealth(icon, item):
                _after(self.app.toggle_stealth)

            def on_stealth_lines(icon, item):
                n = int(str(item))
                _after(lambda: self.app._set_stealth_lines(n))

            def on_adapt_bg(icon, item):
                _after(self.app.toggle_adapt_bg)

            def on_theme(icon, item):
                _after(self.app._toggle_theme_menu)

            def on_invert(icon, item):
                _after(self.app.toggle_invert)

            def on_read(icon, item):
                _after(self.app.toggle_read)

            def on_topmost(icon, item):
                _after(self.app.toggle_topmost)

            def on_settings(icon, item):
                _after(self.app.show_settings)

            def on_about(icon, item):
                _after(self.app._show_about)

            def on_exit(icon, item):
                _after(self.app.exit_app)

            # ===== 动态状态查询函数（用于复选框勾选状态） =====
            def is_panel_locked(item):
                return bool(self.app.cfg.get('panel_locked', True))

            def is_adapt_bg(item):
                return bool(self.app.cfg.get('adapt_bg', False))

            def is_light_mode(item):
                return self.app.cfg.get('theme_mode', 'dark') == 'light'

            def stealth_label(item):
                return "退出隐写模式" if self.app.cfg.get('stealth_mode') else "隐写模式"

            def stealth_lines_value(item):
                return int(self.app.cfg.get('stealth_lines', 3))

            # ===== 菜单结构（与 handle.py 完全一致） =====
            menu = TrayMenu(
                TrayItem("显示/隐藏主窗口", on_show_hide, default=True),
                TrayItem("锁定仪表板相对位置", on_panel_locked, checked=is_panel_locked),
                TrayMenu.SEPARATOR,
                TrayItem("打开文件", on_open),
                TrayItem("保存文件", on_save),
                TrayItem("读取暂存", on_load_autosave),
                TrayMenu.SEPARATOR,
                TrayItem(stealth_label, on_stealth),
                TrayMenu.SEPARATOR,
                TrayItem("一行模式", on_stealth_lines, radio=True, checked=lambda i: stealth_lines_value(i) == 1),
                TrayItem("两行模式", on_stealth_lines, radio=True, checked=lambda i: stealth_lines_value(i) == 2),
                TrayItem("三行模式", on_stealth_lines, radio=True, checked=lambda i: stealth_lines_value(i) == 3),
                TrayMenu.SEPARATOR,
                TrayItem("双击适配背景", on_adapt_bg, checked=is_adapt_bg),
                TrayMenu.SEPARATOR,
                TrayItem("切换深色/浅色模式", on_theme, checked=is_light_mode),
                TrayMenu.SEPARATOR,
                TrayItem("反色显示", on_invert),
                TrayItem("易读模式", on_read),
                TrayItem("置顶模式", on_topmost),
                TrayMenu.SEPARATOR,
                TrayItem("设置", on_settings),
                TrayMenu.SEPARATOR,
                TrayItem("关于", on_about),
                TrayItem("退出", on_exit),
            )

            icon_image = self._load_icon()

            self.icon = PystrayIcon(APP_NAME, icon_image, APP_NAME, menu)
            print("[托盘] TrayIcon创建成功")

            def _tray_run():
                try:
                    print("[托盘] 开始运行")
                    self.icon.run()
                    print("[托盘] 运行结束")
                except Exception as e:
                    print(f"[托盘] 运行异常: {e}")
                    import traceback
                    traceback.print_exc()

            tray_thread = threading.Thread(target=_tray_run, daemon=True)
            tray_thread.start()
            print("[托盘] 线程已启动")

        except Exception as e:
            print(f"[托盘] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.icon = None

    def _load_icon(self):
        """加载托盘图标，失败则生成默认图标"""
        try:
            from PIL import Image
            if self.app.icon_path and os.path.exists(self.app.icon_path):
                try:
                    img = Image.open(self.app.icon_path)
                    print(f"[托盘] 从文件加载图标: {self.app.icon_path}")
                    return img
                except Exception as e:
                    print(f"[托盘] 图标文件加载失败: {e}")

            size = 64
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            cx, cy = size // 2, size // 2
            r = size // 2 - 4
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=(45, 45, 45, 255),
                         outline=(255, 255, 255, 255), width=2)
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", 36)
            except Exception:
                font = ImageFont.load_default()
            draw.text((cx, cy), "S", fill=(255, 255, 255, 255), font=font, anchor="mm")
            print("[托盘] 使用生成的默认图标")
            return img
        except Exception as e:
            print(f"[托盘] 生成默认图标失败: {e}")
            return None

    def _toggle(self):
        """托盘点击切换：显示在最前台 / 最小化隐藏"""
        if self.app._window_visible:
            self.app._hide_window()
        else:
            self.app._show_window()

    def stop(self):
        """停止托盘图标"""
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                print(f"[托盘] 停止失败: {e}")

    def on_clicked(self):
        """左键点击托盘图标"""
        self._toggle()

    def show_menu(self):
        """右键菜单（由 pystray 自动处理）"""
        pass
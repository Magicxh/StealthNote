# -*- coding: utf-8 -*-
"""Stealth Note - 系统托盘模块"""
import os
import threading
from constants import APP_NAME
from utils import create_app_icon


class TrayIcon:
    """系统托盘图标：始终存在，左键切换显示/隐藏，右键菜单"""

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
            def on_tray_clicked(icon, item):
                action = str(item)
                if action == "显示/隐藏":
                    self.app.root.after(0, self._toggle)
                elif action == "打开文件":
                    self.app.root.after(0, self.app.file_open)
                elif action == "保存文件":
                    self.app.root.after(0, self.app.file_save)
                elif action == "设置":
                    self.app.root.after(0, self.app.show_settings)
                elif action == "退出":
                    self.app.root.after(0, self.app.exit_app)

            menu = TrayMenu(
                TrayItem("显示/隐藏", on_tray_clicked, default=True),
                TrayItem("打开文件", on_tray_clicked),
                TrayItem("保存文件", on_tray_clicked),
                TrayItem("设置", on_tray_clicked),
                TrayItem("退出", on_tray_clicked)
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
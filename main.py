#!/usr/bin/env python3
"""
SW-8000Q 四通道相机采集软件

主入口文件

使用方法:
    python main.py

功能:
    - 设备发现与连接
    - RGB + NIR 双流实时预览
    - R/G/B/NIR 四通道分离显示
    - 单帧拍照与分通道保存
    - 曝光、增益等参数控制
"""

import sys
import os

# Windows OLE 初始化 - 必须在导入 Qt 之前
# 使用 OleInitialize 而不是 CoInitialize，以支持 Windows 原生对话框
if sys.platform == 'win32':
    try:
        import ctypes
        # OleInitialize 会同时初始化 COM（STA 模式）和 OLE
        ctypes.windll.ole32.OleInitialize(None)
    except Exception:
        pass  # 忽略错误，继续运行

# 确保能找到本地模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.main_window import MainWindow


def setup_high_dpi():
    """设置高DPI支持"""
    # Qt6 默认启用高DPI支持，但可以进行一些额外配置
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )


def setup_style(app: QApplication):
    """设置应用样式"""
    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 设置样式表
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }

        QGroupBox {
            font-weight: bold;
            border: 1px solid #444;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }

        QToolBar {
            background-color: #3c3c3c;
            border: none;
            spacing: 5px;
            padding: 3px;
        }

        QToolBar QToolButton {
            background-color: #4a4a4a;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px 10px;
            color: white;
        }

        QToolBar QToolButton:hover {
            background-color: #5a5a5a;
        }

        QToolBar QToolButton:pressed {
            background-color: #6a6a6a;
        }

        QToolBar QToolButton:disabled {
            background-color: #3a3a3a;
            color: #888;
        }

        QPushButton {
            background-color: #4a4a4a;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px 15px;
            color: white;
            min-width: 60px;
        }

        QPushButton:hover {
            background-color: #5a5a5a;
        }

        QPushButton:pressed {
            background-color: #6a6a6a;
        }

        QPushButton:disabled {
            background-color: #3a3a3a;
            color: #888;
        }

        QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 3px;
            color: white;
        }

        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 16px;
            border-left: 1px solid #555;
            border-bottom: 1px solid #555;
            background-color: #4a4a4a;
        }

        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 16px;
            border-left: 1px solid #555;
            background-color: #4a4a4a;
        }

        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
            background-color: #5a5a5a;
        }

        QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
        QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
            background-color: #6a6a6a;
        }

        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 6px solid white;
        }

        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid white;
        }

        QSlider::groove:horizontal {
            border: 1px solid #444;
            height: 6px;
            background: #3c3c3c;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: #0078d4;
            border: none;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }

        QSlider::handle:horizontal:hover {
            background: #1a8aff;
        }

        QStatusBar {
            background-color: #3c3c3c;
            color: white;
        }

        QTableWidget {
            background-color: #2b2b2b;
            alternate-background-color: #333;
            gridline-color: #444;
            color: white;
            border: 1px solid #444;
        }

        QTableWidget::item:selected {
            background-color: #0078d4;
        }

        QHeaderView::section {
            background-color: #3c3c3c;
            color: white;
            padding: 5px;
            border: 1px solid #444;
        }

        QMenuBar {
            background-color: #3c3c3c;
            color: white;
        }

        QMenuBar::item:selected {
            background-color: #4a4a4a;
        }

        QMenu {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #444;
        }

        QMenu::item:selected {
            background-color: #0078d4;
        }

        QLabel {
            color: white;
        }

        QMessageBox {
            background-color: #2b2b2b;
        }

        QMessageBox QLabel {
            color: white;
        }
    """)


def main():
    """主函数"""
    # 设置高DPI
    setup_high_dpi()

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("SW-8000Q Capture")
    app.setOrganizationName("Photometric Stereo")

    # 设置样式
    setup_style(app)

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

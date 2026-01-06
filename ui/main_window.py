"""
主窗口
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QLabel,
    QMessageBox, QFileDialog, QDockWidget
)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtCore import Qt, QTimer

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from camera.device_manager import DeviceManager
from camera.dual_stream_worker import DualStreamWorker
from .channel_panel import ChannelPanel
from .control_panel import ControlPanel
from .device_selector import DeviceSelectorDialog
from utils.image_saver import ImageSaver
from utils.settings import get_settings, CameraSettings


class MainWindow(QMainWindow):
    """
    主窗口

    整合所有组件，提供完整的相机控制界面
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化组件
        self.device_manager = DeviceManager()
        self.acquisition_worker: Optional[DualStreamWorker] = None
        self.image_saver = ImageSaver()
        self._settings = get_settings()
        self._current_mac_address: Optional[str] = None  # 当前连接相机的 MAC 地址

        # 恢复上次保存的目录（如果存在）
        saved_dir = self._settings.save_directory
        if saved_dir:
            self.image_saver.set_save_dir(saved_dir)

        # 设置窗口
        self.setWindowTitle("SW-8000Q 四通道相机采集软件")
        self.setMinimumSize(1200, 800)

        # 设置UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

        # 状态更新定时器
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(500)

    def _setup_ui(self):
        """设置UI"""
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 通道预览面板
        self.channel_panel = ChannelPanel()
        main_layout.addWidget(self.channel_panel, 1)

        # 控制面板
        self.control_panel = ControlPanel(self.device_manager)
        self.control_panel.set_enabled(False)
        main_layout.addWidget(self.control_panel)

    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        self._set_save_dir_action = QAction("设置保存目录...", self)
        self._set_save_dir_action.triggered.connect(self._on_set_save_dir)
        file_menu.addAction(self._set_save_dir_action)

        file_menu.addSeparator()

        self._exit_action = QAction("退出(&X)", self)
        self._exit_action.setShortcut(QKeySequence.Quit)
        self._exit_action.triggered.connect(self.close)
        file_menu.addAction(self._exit_action)

        # 相机菜单
        camera_menu = menubar.addMenu("相机(&C)")

        self._connect_action = QAction("连接设备...", self)
        self._connect_action.setShortcut("Ctrl+O")
        self._connect_action.triggered.connect(self._on_connect_device)
        camera_menu.addAction(self._connect_action)

        self._disconnect_action = QAction("断开连接", self)
        self._disconnect_action.setShortcut("Ctrl+D")
        self._disconnect_action.triggered.connect(self._on_disconnect_device)
        self._disconnect_action.setEnabled(False)
        camera_menu.addAction(self._disconnect_action)

        camera_menu.addSeparator()

        self._start_action = QAction("开始采集", self)
        self._start_action.setShortcut("F5")
        self._start_action.triggered.connect(self._on_start_acquisition)
        self._start_action.setEnabled(False)
        camera_menu.addAction(self._start_action)

        self._stop_action = QAction("停止采集", self)
        self._stop_action.setShortcut("F6")
        self._stop_action.triggered.connect(self._on_stop_acquisition)
        self._stop_action.setEnabled(False)
        camera_menu.addAction(self._stop_action)

        camera_menu.addSeparator()

        self._capture_action = QAction("拍照保存", self)
        self._capture_action.setShortcut("Space")
        self._capture_action.triggered.connect(self._on_capture)
        self._capture_action.setEnabled(False)
        camera_menu.addAction(self._capture_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        self._about_action = QAction("关于...", self)
        self._about_action.triggered.connect(self._on_about)
        help_menu.addAction(self._about_action)

    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 连接按钮
        self._toolbar_connect = toolbar.addAction("连接")
        self._toolbar_connect.triggered.connect(self._on_connect_device)

        # 断开按钮
        self._toolbar_disconnect = toolbar.addAction("断开")
        self._toolbar_disconnect.triggered.connect(self._on_disconnect_device)
        self._toolbar_disconnect.setEnabled(False)

        toolbar.addSeparator()

        # 开始采集按钮
        self._toolbar_start = toolbar.addAction("开始采集")
        self._toolbar_start.triggered.connect(self._on_start_acquisition)
        self._toolbar_start.setEnabled(False)

        # 停止采集按钮
        self._toolbar_stop = toolbar.addAction("停止采集")
        self._toolbar_stop.triggered.connect(self._on_stop_acquisition)
        self._toolbar_stop.setEnabled(False)

        toolbar.addSeparator()

        # 拍照按钮
        self._toolbar_capture = toolbar.addAction("拍照 (Space)")
        self._toolbar_capture.triggered.connect(self._on_capture)
        self._toolbar_capture.setEnabled(False)

        toolbar.addSeparator()

        # 保存目录显示
        toolbar.addWidget(QLabel("保存目录: "))
        self._save_dir_label = QLabel(self.image_saver.save_dir or "未设置")
        self._save_dir_label.setStyleSheet("color: lightblue;")
        toolbar.addWidget(self._save_dir_label)

        # 设置目录按钮
        self._toolbar_set_dir = toolbar.addAction("浏览...")
        self._toolbar_set_dir.triggered.connect(self._on_set_save_dir)

    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # 连接状态
        self._status_connection = QLabel("未连接")
        self.statusbar.addWidget(self._status_connection)

        self.statusbar.addWidget(QLabel(" | "))

        # 采集状态
        self._status_acquisition = QLabel("采集: 停止")
        self.statusbar.addWidget(self._status_acquisition)

        self.statusbar.addWidget(QLabel(" | "))

        # 帧率
        self._status_fps = QLabel("FPS: --")
        self.statusbar.addWidget(self._status_fps)

        self.statusbar.addWidget(QLabel(" | "))

        # 带宽
        self._status_bandwidth = QLabel("带宽: -- Mb/s")
        self.statusbar.addWidget(self._status_bandwidth)

    def _on_connect_device(self):
        """连接设备"""
        device_info = DeviceSelectorDialog.select_device(self.device_manager, self)

        if device_info:
            success, message = self.device_manager.connect(device_info.connection_id)

            if success:
                # 保存当前相机的 MAC 地址
                self._current_mac_address = device_info.mac_address

                self._update_ui_connected()
                self.control_panel.refresh_parameters()

                # 连接参数变化信号，用于持久化保存
                self.control_panel.parameter_changed.connect(self._on_parameter_changed)

                # 恢复相机保存的参数设置
                self._restore_camera_settings()

                QMessageBox.information(self, "成功", f"已连接到设备:\n{device_info}")
            else:
                QMessageBox.critical(self, "连接失败", message)

    def _on_disconnect_device(self):
        """断开设备"""
        # 先停止采集
        if self.acquisition_worker and self.acquisition_worker.is_running:
            self._on_stop_acquisition()

        # 断开参数变化信号连接
        try:
            self.control_panel.parameter_changed.disconnect(self._on_parameter_changed)
        except RuntimeError:
            pass  # 信号未连接

        success, message = self.device_manager.disconnect()

        if success:
            self._current_mac_address = None
            self._update_ui_disconnected()
            self.channel_panel.clear_all()

    def _on_start_acquisition(self):
        """开始采集"""
        if not self.device_manager.is_connected:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return

        if self.acquisition_worker and self.acquisition_worker.is_running:
            return

        # 创建采集线程
        self.acquisition_worker = DualStreamWorker(self.device_manager, self)

        # 连接信号
        self.acquisition_worker.rgb_frame_ready.connect(self.channel_panel.update_rgb_frame)
        self.acquisition_worker.nir_frame_ready.connect(self.channel_panel.update_nir_frame)
        self.acquisition_worker.statistics_updated.connect(self._on_statistics_updated)
        self.acquisition_worker.error_occurred.connect(self._on_acquisition_error)
        self.acquisition_worker.acquisition_started.connect(self._on_acquisition_started)
        self.acquisition_worker.acquisition_stopped.connect(self._on_acquisition_stopped)

        # 启动线程
        self.acquisition_worker.start()

    def _on_stop_acquisition(self):
        """停止采集"""
        if self.acquisition_worker:
            self.acquisition_worker.stop()

    def _on_capture(self):
        """拍照保存"""
        if not self.acquisition_worker or not self.acquisition_worker.is_running:
            QMessageBox.warning(self, "警告", "请先开始采集")
            return

        if not self.image_saver.save_dir:
            result = QMessageBox.question(
                self, "提示",
                "尚未设置保存目录，是否现在设置？",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                self._on_set_save_dir()
                if not self.image_saver.save_dir:
                    return
            else:
                return

        # 获取当前帧数据
        channel_data = self.channel_panel.get_channel_data()

        rgb_data = channel_data.get('rgb')
        nir_data = channel_data.get('nir')

        if rgb_data is None:
            QMessageBox.warning(self, "警告", "没有可用的图像数据")
            return

        # 保存图像
        try:
            saved_files = self.image_saver.save_capture(rgb_data, nir_data)
            self.statusbar.showMessage(f"已保存 {len(saved_files)} 个文件", 3000)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存图像时出错:\n{str(e)}")

    def _on_set_save_dir(self):
        """设置保存目录"""
        current_dir = self.image_saver.save_dir or os.path.expanduser("~")

        # 使用 Qt 自己的文件对话框，避免 COM 初始化问题
        directory = QFileDialog.getExistingDirectory(
            self, "选择保存目录", current_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        )

        if directory:
            self.image_saver.set_save_dir(directory)
            self._save_dir_label.setText(directory)
            # 持久化保存目录设置
            self._settings.save_directory = directory

    def _restore_camera_settings(self):
        """
        恢复相机保存的参数设置

        在相机连接后调用，从 QSettings 读取上次保存的参数并应用到相机
        """
        if not self._current_mac_address:
            return

        # 获取保存的设置
        saved_settings = self._settings.get_camera_settings(self._current_mac_address)

        if saved_settings.is_empty():
            print(f"[MainWindow] 未找到相机 {self._current_mac_address} 的保存设置")
            return

        print(f"[MainWindow] 恢复相机 {self._current_mac_address} 的设置:")

        # 应用曝光时间
        if saved_settings.exposure_time is not None:
            success = self.device_manager.set_exposure_time(saved_settings.exposure_time)
            if success:
                print(f"  - 曝光时间: {saved_settings.exposure_time} µs")

        # 应用增益
        if saved_settings.gain is not None:
            success = self.device_manager.set_gain(saved_settings.gain)
            if success:
                print(f"  - 增益: {saved_settings.gain} dB")

        # 应用行频
        if saved_settings.line_rate is not None:
            success = self.device_manager.set_acquisition_line_rate(saved_settings.line_rate)
            if success:
                print(f"  - 行频: {saved_settings.line_rate} Hz")

        # 刷新控制面板显示
        self.control_panel.refresh_parameters()

    def _on_parameter_changed(self, param_name: str, value):
        """
        参数变化时保存到设置

        Args:
            param_name: 参数名称
            value: 参数值
        """
        if not self._current_mac_address:
            return

        # 映射 GenICam 参数名到设置键名
        param_map = {
            "ExposureTime": "exposure_time",
            "Gain": "gain",
            "AcquisitionLineRate": "line_rate"
        }

        settings_key = param_map.get(param_name)
        if settings_key:
            self._settings.save_camera_parameter(
                self._current_mac_address,
                settings_key,
                value
            )
            print(f"[MainWindow] 保存相机参数: {param_name} = {value}")

    def _on_statistics_updated(self, stats: dict):
        """统计信息更新"""
        # 计算总帧率和带宽
        total_fps = 0
        total_bandwidth = 0

        for source_name, source_stats in stats.items():
            total_fps += source_stats.get('fps', 0)
            total_bandwidth += source_stats.get('bandwidth', 0)

        self._status_fps.setText(f"FPS: {total_fps:.1f}")
        self._status_bandwidth.setText(f"带宽: {total_bandwidth:.1f} Mb/s")

    def _on_acquisition_error(self, error_msg: str):
        """采集错误"""
        QMessageBox.critical(self, "采集错误", error_msg)
        self._update_ui_acquisition_stopped()

    def _on_acquisition_started(self):
        """采集已启动"""
        self._update_ui_acquisition_started()

    def _on_acquisition_stopped(self):
        """采集已停止"""
        self._update_ui_acquisition_stopped()

    def _update_ui_connected(self):
        """更新UI - 已连接状态"""
        self._connect_action.setEnabled(False)
        self._disconnect_action.setEnabled(True)
        self._start_action.setEnabled(True)
        self._toolbar_connect.setEnabled(False)
        self._toolbar_disconnect.setEnabled(True)
        self._toolbar_start.setEnabled(True)
        self.control_panel.set_enabled(True)
        self._status_connection.setText("已连接")
        self._status_connection.setStyleSheet("color: green;")

    def _update_ui_disconnected(self):
        """更新UI - 未连接状态"""
        self._connect_action.setEnabled(True)
        self._disconnect_action.setEnabled(False)
        self._start_action.setEnabled(False)
        self._stop_action.setEnabled(False)
        self._capture_action.setEnabled(False)
        self._toolbar_connect.setEnabled(True)
        self._toolbar_disconnect.setEnabled(False)
        self._toolbar_start.setEnabled(False)
        self._toolbar_stop.setEnabled(False)
        self._toolbar_capture.setEnabled(False)
        self.control_panel.set_enabled(False)
        self._status_connection.setText("未连接")
        self._status_connection.setStyleSheet("color: red;")
        self._status_acquisition.setText("采集: 停止")
        self._status_fps.setText("FPS: --")
        self._status_bandwidth.setText("带宽: -- Mb/s")

    def _update_ui_acquisition_started(self):
        """更新UI - 采集中状态"""
        self._start_action.setEnabled(False)
        self._stop_action.setEnabled(True)
        self._capture_action.setEnabled(True)
        self._disconnect_action.setEnabled(False)
        self._toolbar_start.setEnabled(False)
        self._toolbar_stop.setEnabled(True)
        self._toolbar_capture.setEnabled(True)
        self._toolbar_disconnect.setEnabled(False)
        self._status_acquisition.setText("采集: 运行中")
        self._status_acquisition.setStyleSheet("color: green;")

    def _update_ui_acquisition_stopped(self):
        """更新UI - 采集停止状态"""
        self._start_action.setEnabled(True)
        self._stop_action.setEnabled(False)
        self._capture_action.setEnabled(False)
        self._disconnect_action.setEnabled(True)
        self._toolbar_start.setEnabled(True)
        self._toolbar_stop.setEnabled(False)
        self._toolbar_capture.setEnabled(False)
        self._toolbar_disconnect.setEnabled(True)
        self._status_acquisition.setText("采集: 停止")
        self._status_acquisition.setStyleSheet("")
        self._status_fps.setText("FPS: --")
        self._status_bandwidth.setText("带宽: -- Mb/s")

    def _update_status(self):
        """定时状态更新"""
        pass  # 可用于更新其他状态信息

    def _on_about(self):
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于 SW-8000Q 采集软件",
            """<h3>SW-8000Q 四通道相机采集软件</h3>
            <p>版本: 1.0.0</p>
            <p>用于光度立体重建的图像采集测试</p>
            <p>支持 JAI SW-8000Q-10GE 四CMOS棱镜相机</p>
            <hr>
            <p>功能特性:</p>
            <ul>
                <li>设备发现与连接</li>
                <li>RGB + NIR 双流实时预览</li>
                <li>R/G/B/NIR 四通道分离显示</li>
                <li>单帧拍照与分通道保存</li>
                <li>曝光、增益等参数控制</li>
            </ul>
            """
        )

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止采集
        if self.acquisition_worker and self.acquisition_worker.is_running:
            self.acquisition_worker.stop()

        # 断开设备
        if self.device_manager.is_connected:
            self.device_manager.disconnect()

        event.accept()

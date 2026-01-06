"""
参数控制面板
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QSpinBox, QDoubleSpinBox,
    QSlider, QPushButton, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from camera.device_manager import DeviceManager


class ControlPanel(QWidget):
    """
    参数控制面板

    包含曝光时间、增益、图像尺寸等参数的控制
    """

    # 信号
    parameter_changed = Signal(str, object)  # 参数名, 新值

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # 曝光控制组
        exposure_group = QGroupBox(self.tr("Exposure Control"))
        exposure_layout = QGridLayout(exposure_group)

        # 曝光时间
        exposure_layout.addWidget(QLabel(self.tr("Exposure Time (µs):")), 0, 0)

        self._exposure_edit = QLineEdit()
        self._exposure_edit.setValidator(QDoubleValidator(1, 1000000, 1))
        self._exposure_edit.setText("1000")
        self._exposure_edit.setFixedWidth(80)
        exposure_layout.addWidget(self._exposure_edit, 0, 1)

        self._exposure_slider = QSlider(Qt.Horizontal)
        self._exposure_slider.setRange(1, 100000)
        self._exposure_slider.setValue(1000)
        exposure_layout.addWidget(self._exposure_slider, 1, 0, 1, 2)

        main_layout.addWidget(exposure_group)

        # 增益控制组
        gain_group = QGroupBox(self.tr("Gain Control"))
        gain_layout = QGridLayout(gain_group)

        # 增益
        gain_layout.addWidget(QLabel(self.tr("Gain (dB):")), 0, 0)

        self._gain_edit = QLineEdit()
        self._gain_edit.setValidator(QDoubleValidator(0, 36, 1))
        self._gain_edit.setText("0")
        self._gain_edit.setFixedWidth(80)
        gain_layout.addWidget(self._gain_edit, 0, 1)

        self._gain_slider = QSlider(Qt.Horizontal)
        self._gain_slider.setRange(0, 360)  # 0.1 dB 精度
        self._gain_slider.setValue(0)
        gain_layout.addWidget(self._gain_slider, 1, 0, 1, 2)

        main_layout.addWidget(gain_group)

        # 行频控制组
        line_rate_group = QGroupBox(self.tr("Line Rate Control"))
        line_rate_layout = QGridLayout(line_rate_group)

        # 行频
        line_rate_layout.addWidget(QLabel(self.tr("Line Rate (Hz):")), 0, 0)

        self._line_rate_edit = QLineEdit()
        self._line_rate_edit.setValidator(QIntValidator(1, 100000))
        self._line_rate_edit.setText("10000")
        self._line_rate_edit.setFixedWidth(80)
        line_rate_layout.addWidget(self._line_rate_edit, 0, 1)

        self._line_rate_slider = QSlider(Qt.Horizontal)
        self._line_rate_slider.setRange(1, 100000)
        self._line_rate_slider.setValue(10000)
        line_rate_layout.addWidget(self._line_rate_slider, 1, 0, 1, 2)

        main_layout.addWidget(line_rate_group)

        # 图像尺寸控制组
        size_group = QGroupBox(self.tr("Image Size"))
        size_layout = QGridLayout(size_group)

        # 宽度
        size_layout.addWidget(QLabel(self.tr("Width:")), 0, 0)
        self._width_spinbox = QSpinBox()
        self._width_spinbox.setRange(64, 16384)
        self._width_spinbox.setSingleStep(64)
        self._width_spinbox.setValue(8192)
        size_layout.addWidget(self._width_spinbox, 0, 1)

        # 高度
        size_layout.addWidget(QLabel(self.tr("Height:")), 1, 0)
        self._height_spinbox = QSpinBox()
        self._height_spinbox.setRange(1, 65535)
        self._height_spinbox.setSingleStep(1)
        self._height_spinbox.setValue(1)
        size_layout.addWidget(self._height_spinbox, 1, 1)

        # 应用按钮
        self._apply_size_button = QPushButton(self.tr("Apply Size"))
        size_layout.addWidget(self._apply_size_button, 2, 0, 1, 2)

        main_layout.addWidget(size_group)

        # 刷新按钮
        refresh_layout = QVBoxLayout()
        refresh_layout.addStretch()

        self._refresh_button = QPushButton(self.tr("Refresh"))
        self._refresh_button.setToolTip(self.tr("Read current parameter values from camera"))
        refresh_layout.addWidget(self._refresh_button)

        refresh_layout.addStretch()
        main_layout.addLayout(refresh_layout)

        main_layout.addStretch()

    def _connect_signals(self):
        """连接信号"""
        # 曝光时间
        self._exposure_edit.editingFinished.connect(self._on_exposure_edit_changed)
        self._exposure_slider.valueChanged.connect(self._on_exposure_slider_changed)

        # 增益
        self._gain_edit.editingFinished.connect(self._on_gain_edit_changed)
        self._gain_slider.valueChanged.connect(self._on_gain_slider_changed)

        # 行频
        self._line_rate_edit.editingFinished.connect(self._on_line_rate_edit_changed)
        self._line_rate_slider.valueChanged.connect(self._on_line_rate_slider_changed)

        # 图像尺寸
        self._apply_size_button.clicked.connect(self._on_apply_size)

        # 刷新
        self._refresh_button.clicked.connect(self.refresh_parameters)

    def _on_exposure_edit_changed(self):
        """曝光时间输入框改变"""
        try:
            value = float(self._exposure_edit.text())
            self._exposure_slider.blockSignals(True)
            self._exposure_slider.setValue(int(value))
            self._exposure_slider.blockSignals(False)
            self._apply_exposure(value)
        except ValueError:
            pass

    def _on_exposure_slider_changed(self, value: int):
        """曝光时间 slider 改变"""
        self._exposure_edit.blockSignals(True)
        self._exposure_edit.setText(str(value))
        self._exposure_edit.blockSignals(False)
        self._apply_exposure(float(value))

    def _apply_exposure(self, value: float):
        """应用曝光时间"""
        if self.device_manager.is_connected:
            success = self.device_manager.set_exposure_time(value)
            if success:
                self.parameter_changed.emit("ExposureTime", value)

    def _on_gain_edit_changed(self):
        """增益输入框改变"""
        try:
            value = float(self._gain_edit.text())
            self._gain_slider.blockSignals(True)
            self._gain_slider.setValue(int(value * 10))
            self._gain_slider.blockSignals(False)
            self._apply_gain(value)
        except ValueError:
            pass

    def _on_gain_slider_changed(self, value: int):
        """增益 slider 改变"""
        gain_value = value / 10.0
        self._gain_edit.blockSignals(True)
        self._gain_edit.setText(f"{gain_value:.1f}")
        self._gain_edit.blockSignals(False)
        self._apply_gain(gain_value)

    def _apply_gain(self, value: float):
        """应用增益"""
        if self.device_manager.is_connected:
            success = self.device_manager.set_gain(value)
            if success:
                self.parameter_changed.emit("Gain", value)

    def _on_line_rate_edit_changed(self):
        """行频输入框改变"""
        try:
            value = int(self._line_rate_edit.text())
            self._line_rate_slider.blockSignals(True)
            self._line_rate_slider.setValue(value)
            self._line_rate_slider.blockSignals(False)
            self._apply_line_rate(value)
        except ValueError:
            pass

    def _on_line_rate_slider_changed(self, value: int):
        """行频 slider 改变"""
        self._line_rate_edit.blockSignals(True)
        self._line_rate_edit.setText(str(value))
        self._line_rate_edit.blockSignals(False)
        self._apply_line_rate(value)

    def _apply_line_rate(self, value: int):
        """应用行频"""
        if self.device_manager.is_connected:
            success = self.device_manager.set_acquisition_line_rate(value)
            if success:
                self.parameter_changed.emit("AcquisitionLineRate", value)

    def _on_apply_size(self):
        """应用图像尺寸"""
        if not self.device_manager.is_connected:
            return

        width = self._width_spinbox.value()
        height = self._height_spinbox.value()

        # 分别设置宽度和高度，以便获取单独的成功/失败状态
        success_w = self.device_manager.set_parameter("Width", width)
        success_h = self.device_manager.set_parameter("Height", height)

        if success_w:
            self.parameter_changed.emit("Width", width)
            print(f"[ControlPanel] 成功设置 Width = {width}")
        else:
            print(f"[ControlPanel] 设置 Width = {width} 失败")

        if success_h:
            self.parameter_changed.emit("Height", height)
            print(f"[ControlPanel] 成功设置 Height = {height}")
        else:
            print(f"[ControlPanel] 设置 Height = {height} 失败")

        # 刷新参数以显示实际值
        if not success_w or not success_h:
            self.refresh_parameters()

    def refresh_parameters(self):
        """从设备读取当前参数"""
        if not self.device_manager.is_connected:
            return

        # 读取曝光时间
        success, exposure = self.device_manager.get_exposure_time()
        if success and exposure is not None:
            self._exposure_edit.blockSignals(True)
            self._exposure_slider.blockSignals(True)
            self._exposure_edit.setText(str(int(exposure)))
            self._exposure_slider.setValue(int(exposure))
            self._exposure_edit.blockSignals(False)
            self._exposure_slider.blockSignals(False)

            # 更新范围
            info = self.device_manager.get_parameter_info("ExposureTime")
            if info and info.min_val is not None and info.max_val is not None:
                self._exposure_edit.setValidator(QDoubleValidator(info.min_val, info.max_val, 1))
                self._exposure_slider.setRange(int(info.min_val), min(int(info.max_val), 100000))

        # 读取增益
        success, gain = self.device_manager.get_gain()
        if success and gain is not None:
            self._gain_edit.blockSignals(True)
            self._gain_slider.blockSignals(True)
            self._gain_edit.setText(f"{gain:.1f}")
            self._gain_slider.setValue(int(gain * 10))
            self._gain_edit.blockSignals(False)
            self._gain_slider.blockSignals(False)

            # 更新范围
            info = self.device_manager.get_parameter_info("Gain")
            if info and info.min_val is not None and info.max_val is not None:
                self._gain_edit.setValidator(QDoubleValidator(info.min_val, info.max_val, 1))
                self._gain_slider.setRange(int(info.min_val * 10), int(info.max_val * 10))

        # 读取行频
        success, line_rate = self.device_manager.get_acquisition_line_rate()
        if success and line_rate is not None:
            self._line_rate_edit.blockSignals(True)
            self._line_rate_slider.blockSignals(True)
            self._line_rate_edit.setText(str(int(line_rate)))
            self._line_rate_slider.setValue(int(line_rate))
            self._line_rate_edit.blockSignals(False)
            self._line_rate_slider.blockSignals(False)

            # 更新范围
            info = self.device_manager.get_parameter_info("AcquisitionLineRate")
            if info and info.min_val is not None and info.max_val is not None:
                self._line_rate_edit.setValidator(QIntValidator(int(info.min_val), int(info.max_val)))
                self._line_rate_slider.setRange(int(info.min_val), min(int(info.max_val), 100000))

        # 读取图像尺寸
        width, height = self.device_manager.get_image_size()
        if width > 0:
            self._width_spinbox.blockSignals(True)
            self._width_spinbox.setValue(width)
            self._width_spinbox.blockSignals(False)

            # 更新范围
            info = self.device_manager.get_parameter_info("Width")
            if info and info.min_val is not None and info.max_val is not None:
                self._width_spinbox.setRange(int(info.min_val), int(info.max_val))

        if height > 0:
            self._height_spinbox.blockSignals(True)
            self._height_spinbox.setValue(height)
            self._height_spinbox.blockSignals(False)

            info = self.device_manager.get_parameter_info("Height")
            if info and info.min_val is not None and info.max_val is not None:
                self._height_spinbox.setRange(int(info.min_val), int(info.max_val))

    def set_enabled(self, enabled: bool):
        """设置控件是否可用"""
        self._exposure_edit.setEnabled(enabled)
        self._exposure_slider.setEnabled(enabled)
        self._gain_edit.setEnabled(enabled)
        self._gain_slider.setEnabled(enabled)
        self._line_rate_edit.setEnabled(enabled)
        self._line_rate_slider.setEnabled(enabled)
        self._width_spinbox.setEnabled(enabled)
        self._height_spinbox.setEnabled(enabled)
        self._apply_size_button.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)

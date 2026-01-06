"""
设备选择对话框
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QProgressDialog
)
from PySide6.QtCore import Qt, QTimer

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from camera.device_manager import DeviceManager, DeviceInfo


class DeviceSelectorDialog(QDialog):
    """
    设备选择对话框

    显示可用设备列表，允许用户选择要连接的设备
    """

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._devices: List[DeviceInfo] = []
        self._selected_device: Optional[DeviceInfo] = None

        self.setWindowTitle(self.tr("Select Device"))
        self.setMinimumSize(700, 400)
        self.setModal(True)

        self._setup_ui()

        # 自动扫描设备
        QTimer.singleShot(100, self._scan_devices)

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 提示标签
        hint_label = QLabel(self.tr("Please select a device to connect:"))
        layout.addWidget(hint_label)

        # 设备列表表格
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            self.tr("Model"), self.tr("Serial Number"), self.tr("IP Address"),
            self.tr("MAC Address"), self.tr("Type")
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table)

        # 按钮区域
        button_layout = QHBoxLayout()

        self._refresh_button = QPushButton(self.tr("Refresh"))
        self._refresh_button.clicked.connect(self._scan_devices)
        button_layout.addWidget(self._refresh_button)

        button_layout.addStretch()

        self._connect_button = QPushButton(self.tr("Connect"))
        self._connect_button.setDefault(True)
        self._connect_button.clicked.connect(self._on_connect)
        button_layout.addWidget(self._connect_button)

        self._cancel_button = QPushButton(self.tr("Cancel"))
        self._cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_button)

        layout.addLayout(button_layout)

    def _scan_devices(self):
        """扫描设备"""
        self._refresh_button.setEnabled(False)
        self._refresh_button.setText(self.tr("Scanning..."))

        # 清空表格
        self._table.setRowCount(0)
        self._devices = []

        try:
            # 扫描设备
            self._devices = self.device_manager.find_devices()

            # 填充表格
            self._table.setRowCount(len(self._devices))

            for row, device in enumerate(self._devices):
                # 确保所有值都是字符串类型
                self._table.setItem(row, 0, QTableWidgetItem(str(device.model_name or "")))
                self._table.setItem(row, 1, QTableWidgetItem(str(device.serial_number or "")))
                self._table.setItem(row, 2, QTableWidgetItem(str(device.ip_address or "")))
                self._table.setItem(row, 3, QTableWidgetItem(str(device.mac_address or "")))
                self._table.setItem(row, 4, QTableWidgetItem(str(device.device_type or "")))

            if not self._devices:
                QMessageBox.information(
                    self, self.tr("Notice"),
                    self.tr("No devices found.\nPlease check device connections and network settings.")
                )

        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Error"),
                self.tr("Error scanning devices:") + f"\n{str(e)}"
            )

        finally:
            self._refresh_button.setEnabled(True)
            self._refresh_button.setText(self.tr("Refresh"))

    def _on_connect(self):
        """连接按钮点击"""
        selected_rows = self._table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, self.tr("Notice"), self.tr("Please select a device first"))
            return

        row = self._table.currentRow()
        if row < 0 or row >= len(self._devices):
            return

        self._selected_device = self._devices[row]
        self.accept()

    def _on_double_click(self):
        """双击连接"""
        self._on_connect()

    def get_selected_device(self) -> Optional[DeviceInfo]:
        """获取选中的设备"""
        return self._selected_device

    @staticmethod
    def select_device(device_manager: DeviceManager, parent=None) -> Optional[DeviceInfo]:
        """
        静态方法：显示对话框并返回选中的设备

        Args:
            device_manager: 设备管理器
            parent: 父窗口

        Returns:
            选中的 DeviceInfo 或 None
        """
        dialog = DeviceSelectorDialog(device_manager, parent)
        if dialog.exec() == QDialog.Accepted:
            return dialog.get_selected_device()
        return None

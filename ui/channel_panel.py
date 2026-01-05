"""
多通道预览面板 - 1+2x2 布局
"""

import numpy as np
from typing import Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QGroupBox, QSplitter
)
from PySide6.QtCore import Qt

from .preview_widget import PreviewWidget, ChannelPreviewWidget


def split_rgb_channels(rgb_image: np.ndarray):
    """
    拆分 RGB 图像为单独通道

    Args:
        rgb_image: RGB 图像数组 (H, W, 3)

    Returns:
        (r, g, b) 三个单通道数组
    """
    if rgb_image is None or len(rgb_image.shape) != 3:
        return None, None, None

    r = rgb_image[:, :, 0]
    g = rgb_image[:, :, 1]
    b = rgb_image[:, :, 2]

    return r, g, b


class ChannelPanel(QWidget):
    """
    多通道预览面板

    布局: 1+2x2
    ┌────────────────┬──────────────────┐
    │                │   R    │   G    │
    │   全通道(RGB)  ├────────┼────────┤
    │                │   B    │  NIR   │
    └────────────────┴──────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._latest_rgb_data: Optional[np.ndarray] = None
        self._latest_nir_data: Optional[np.ndarray] = None

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 使用 QSplitter 实现可调整大小的分割
        splitter = QSplitter(Qt.Horizontal)

        # 左侧: 全通道预览 (大图)
        left_group = QGroupBox("全通道预览")
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(5, 10, 5, 5)

        self._main_preview = PreviewWidget("RGB 全通道")
        left_layout.addWidget(self._main_preview)

        splitter.addWidget(left_group)

        # 右侧: 单通道预览 (2x2网格)
        right_group = QGroupBox("单通道预览")
        right_layout = QVBoxLayout(right_group)
        right_layout.setContentsMargins(5, 10, 5, 5)

        # 2x2 网格布局
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # 创建四个单通道预览
        self._r_preview = ChannelPreviewWidget("R")
        self._g_preview = ChannelPreviewWidget("G")
        self._b_preview = ChannelPreviewWidget("B")
        self._nir_preview = ChannelPreviewWidget("NIR")

        # 添加到网格
        grid_layout.addWidget(self._r_preview, 0, 0)
        grid_layout.addWidget(self._g_preview, 0, 1)
        grid_layout.addWidget(self._b_preview, 1, 0)
        grid_layout.addWidget(self._nir_preview, 1, 1)

        # 设置网格行列等比例
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        right_layout.addWidget(grid_widget)
        splitter.addWidget(right_group)

        # 设置分割比例 (左:右 = 3:2)
        splitter.setSizes([600, 400])

        main_layout.addWidget(splitter)

    def update_rgb_frame(self, frame_data: Dict):
        """
        更新 RGB 帧

        Args:
            frame_data: 帧数据字典，包含 'data', 'width', 'height' 等
        """
        data = frame_data.get('data')
        if data is None:
            return

        self._latest_rgb_data = data

        # 更新主预览
        self._main_preview.update_image(data)

        # 拆分并更新单通道
        r, g, b = split_rgb_channels(data)

        if r is not None:
            self._r_preview.update_image(r)
        if g is not None:
            self._g_preview.update_image(g)
        if b is not None:
            self._b_preview.update_image(b)

    def update_nir_frame(self, frame_data: Dict):
        """
        更新 NIR 帧

        Args:
            frame_data: 帧数据字典，包含 'data', 'width', 'height' 等
        """
        data = frame_data.get('data')
        if data is None:
            return

        self._latest_nir_data = data

        # 更新 NIR 通道预览
        self._nir_preview.update_image(data)

    def get_channel_data(self) -> Dict[str, Optional[np.ndarray]]:
        """
        获取所有通道的当前数据

        Returns:
            包含所有通道数据的字典
        """
        result = {
            'rgb': self._latest_rgb_data,
            'nir': self._latest_nir_data,
            'r': None,
            'g': None,
            'b': None,
        }

        if self._latest_rgb_data is not None:
            r, g, b = split_rgb_channels(self._latest_rgb_data)
            result['r'] = r
            result['g'] = g
            result['b'] = b

        return result

    def clear_all(self):
        """清除所有预览"""
        self._main_preview.clear()
        self._r_preview.clear()
        self._g_preview.clear()
        self._b_preview.clear()
        self._nir_preview.clear()

        self._latest_rgb_data = None
        self._latest_nir_data = None


class SingleStreamChannelPanel(QWidget):
    """
    单流通道预览面板（用于只有 RGB 没有 NIR 的情况）

    布局: 1+1x3
    ┌────────────────┬─────────────────────────┐
    │                │   R   │   G   │   B    │
    │   全通道(RGB)  │       │       │        │
    │                │       │       │        │
    └────────────────┴───────┴───────┴────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._latest_rgb_data: Optional[np.ndarray] = None

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧: 全通道预览
        left_group = QGroupBox("全通道预览")
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(5, 10, 5, 5)

        self._main_preview = PreviewWidget("RGB 全通道")
        left_layout.addWidget(self._main_preview)

        splitter.addWidget(left_group)

        # 右侧: 单通道预览 (1x3)
        right_group = QGroupBox("单通道预览")
        right_layout = QVBoxLayout(right_group)
        right_layout.setContentsMargins(5, 10, 5, 5)

        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self._r_preview = ChannelPreviewWidget("R")
        self._g_preview = ChannelPreviewWidget("G")
        self._b_preview = ChannelPreviewWidget("B")

        grid_layout.addWidget(self._r_preview)
        grid_layout.addWidget(self._g_preview)
        grid_layout.addWidget(self._b_preview)

        right_layout.addWidget(grid_widget)
        splitter.addWidget(right_group)

        splitter.setSizes([500, 500])

        main_layout.addWidget(splitter)

    def update_rgb_frame(self, frame_data: Dict):
        """更新 RGB 帧"""
        data = frame_data.get('data')
        if data is None:
            return

        self._latest_rgb_data = data

        self._main_preview.update_image(data)

        r, g, b = split_rgb_channels(data)

        if r is not None:
            self._r_preview.update_image(r)
        if g is not None:
            self._g_preview.update_image(g)
        if b is not None:
            self._b_preview.update_image(b)

    def get_channel_data(self) -> Dict[str, Optional[np.ndarray]]:
        """获取所有通道的当前数据"""
        result = {
            'rgb': self._latest_rgb_data,
            'r': None,
            'g': None,
            'b': None,
        }

        if self._latest_rgb_data is not None:
            r, g, b = split_rgb_channels(self._latest_rgb_data)
            result['r'] = r
            result['g'] = g
            result['b'] = b

        return result

    def clear_all(self):
        """清除所有预览"""
        self._main_preview.clear()
        self._r_preview.clear()
        self._g_preview.clear()
        self._b_preview.clear()

        self._latest_rgb_data = None

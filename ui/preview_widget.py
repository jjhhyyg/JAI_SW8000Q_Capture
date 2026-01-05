"""
图像预览组件
"""

import numpy as np
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QSize


class PreviewWidget(QWidget):
    """
    图像预览组件

    支持显示灰度图和彩色图，自动适应大小
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._image: QImage = None
        self._pixmap: QPixmap = None
        self._keep_aspect_ratio = True

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # 标题标签
        if self._title:
            self._title_label = QLabel(self._title)
            self._title_label.setAlignment(Qt.AlignCenter)
            self._title_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    padding: 2px;
                    background-color: #333;
                    color: white;
                    border-radius: 2px;
                }
            """)
            layout.addWidget(self._title_label)

        # 图像显示标签
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setMinimumSize(100, 75)
        self._image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #444;
            }
        """)

        layout.addWidget(self._image_label)

        # 显示占位符文本
        self._show_placeholder()

    def _show_placeholder(self):
        """显示占位符"""
        self._image_label.setText("无图像")
        self._image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #444;
                color: #666;
            }
        """)

    def set_title(self, title: str):
        """设置标题"""
        self._title = title
        if hasattr(self, '_title_label'):
            self._title_label.setText(title)

    def update_image(self, data: np.ndarray):
        """
        更新显示的图像

        Args:
            data: NumPy 数组，支持灰度 (H, W) 或彩色 (H, W, 3)
        """
        if data is None or data.size == 0:
            self._show_placeholder()
            return

        try:
            # 确保数据是连续的
            if not data.flags['C_CONTIGUOUS']:
                data = np.ascontiguousarray(data)

            # 确保数据类型是 uint8
            if data.dtype != np.uint8:
                data = data.astype(np.uint8)

            # 根据数据维度创建 QImage
            if len(data.shape) == 2:
                # 灰度图
                h, w = data.shape
                bytes_per_line = w
                self._image = QImage(
                    data.data, w, h, bytes_per_line,
                    QImage.Format_Grayscale8
                ).copy()  # 复制以确保数据独立

            elif len(data.shape) == 3:
                h, w, c = data.shape

                if c == 3:
                    # RGB 图像
                    bytes_per_line = 3 * w
                    self._image = QImage(
                        data.data, w, h, bytes_per_line,
                        QImage.Format_RGB888
                    ).copy()

                elif c == 4:
                    # RGBA 图像
                    bytes_per_line = 4 * w
                    self._image = QImage(
                        data.data, w, h, bytes_per_line,
                        QImage.Format_RGBA8888
                    ).copy()

                else:
                    self._show_placeholder()
                    return
            else:
                self._show_placeholder()
                return

            # 更新显示
            self._update_display()

        except Exception as e:
            print(f"更新图像时出错: {str(e)}")
            self._show_placeholder()

    def _update_display(self):
        """更新显示"""
        if self._image is None:
            return

        # 获取标签大小
        label_size = self._image_label.size()

        if self._keep_aspect_ratio:
            # 保持纵横比缩放
            scaled_pixmap = QPixmap.fromImage(self._image).scaled(
                label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        else:
            # 填充整个区域
            scaled_pixmap = QPixmap.fromImage(self._image).scaled(
                label_size,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )

        self._image_label.setPixmap(scaled_pixmap)
        self._image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #444;
            }
        """)

    def resizeEvent(self, event):
        """窗口大小改变时更新显示"""
        super().resizeEvent(event)
        if self._image is not None:
            self._update_display()

    def clear(self):
        """清除图像"""
        self._image = None
        self._pixmap = None
        self._show_placeholder()

    def set_keep_aspect_ratio(self, keep: bool):
        """设置是否保持纵横比"""
        self._keep_aspect_ratio = keep
        if self._image is not None:
            self._update_display()

    def get_image(self) -> QImage:
        """获取当前图像"""
        return self._image

    def sizeHint(self) -> QSize:
        """建议大小"""
        return QSize(320, 240)


class ChannelPreviewWidget(PreviewWidget):
    """
    单通道预览组件

    继承自 PreviewWidget，添加通道颜色标识
    R/G/B 通道以对应颜色显示，NIR 以灰度显示
    """

    CHANNEL_COLORS = {
        'R': '#ff4444',
        'G': '#44ff44',
        'B': '#4444ff',
        'NIR': '#ff44ff',
        'RGB': '#ffffff',
    }

    def __init__(self, channel_name: str, parent=None):
        self._channel_name = channel_name
        super().__init__(title=channel_name, parent=parent)

        # 设置通道颜色
        color = self.CHANNEL_COLORS.get(channel_name.upper(), '#ffffff')
        if hasattr(self, '_title_label'):
            self._title_label.setStyleSheet(f"""
                QLabel {{
                    font-weight: bold;
                    padding: 2px;
                    background-color: {color};
                    color: {'black' if channel_name.upper() in ['G', 'RGB'] else 'white'};
                    border-radius: 2px;
                }}
            """)

    @property
    def channel_name(self) -> str:
        return self._channel_name

    def _colorize_channel(self, data: np.ndarray) -> np.ndarray:
        """
        将灰度数据转换为对应通道颜色

        Args:
            data: 灰度图像数据 (H, W)

        Returns:
            彩色图像数据 (H, W, 3)
        """
        if data is None or len(data.shape) != 2:
            return data

        h, w = data.shape
        colored = np.zeros((h, w, 3), dtype=np.uint8)

        channel = self._channel_name.upper()
        if channel == 'R':
            colored[:, :, 0] = data  # Red channel
        elif channel == 'G':
            colored[:, :, 1] = data  # Green channel
        elif channel == 'B':
            colored[:, :, 2] = data  # Blue channel
        else:
            # NIR and others: return original grayscale
            return data

        return colored

    def update_image(self, data: np.ndarray):
        """
        更新显示的图像

        R/G/B 通道以对应颜色显示，NIR 以灰度显示

        Args:
            data: NumPy 数组，灰度图 (H, W)
        """
        if data is None or data.size == 0:
            self._show_placeholder()
            return

        # 对 R/G/B 通道进行着色
        channel = self._channel_name.upper()
        if channel in ['R', 'G', 'B'] and len(data.shape) == 2:
            colored_data = self._colorize_channel(data)
            super().update_image(colored_data)
        else:
            # NIR 保持灰度显示
            super().update_image(data)

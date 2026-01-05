"""
图像保存工具
"""

import os
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict
import cv2


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


class ImageSaver:
    """
    图像保存工具

    支持保存全通道 RGB 和分离的 R/G/B/NIR 单通道
    """

    def __init__(self, save_dir: Optional[str] = None):
        """
        初始化图像保存器

        Args:
            save_dir: 保存目录路径，如果为 None 则需要后续设置
        """
        self._save_dir = save_dir
        self._capture_count = 0

    @property
    def save_dir(self) -> Optional[str]:
        """获取保存目录"""
        return self._save_dir

    @property
    def capture_count(self) -> int:
        """获取已保存的拍照次数"""
        return self._capture_count

    def set_save_dir(self, directory: str) -> bool:
        """
        设置保存目录

        Args:
            directory: 目录路径

        Returns:
            是否成功
        """
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except Exception as e:
                print(f"创建目录失败: {e}")
                return False

        self._save_dir = directory
        return True

    def _generate_timestamp(self) -> str:
        """生成时间戳字符串"""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒

    def save_capture(
        self,
        rgb_data: Optional[np.ndarray],
        nir_data: Optional[np.ndarray] = None,
        timestamp: Optional[str] = None,
        save_nir: bool = True
    ) -> List[str]:
        """
        保存拍照图像

        保存到文件夹: 5_channels_{timestamp}/
        - full_rgb.png     # 全通道 RGB
        - channel_r.png    # R 通道
        - channel_g.png    # G 通道
        - channel_b.png    # B 通道
        - channel_nir.png  # NIR 通道（如果有）

        Args:
            rgb_data: RGB 图像数据 (H, W, 3)
            nir_data: NIR 图像数据 (H, W)，可选
            timestamp: 时间戳字符串，如果为 None 则自动生成
            save_nir: 是否保存 NIR 通道

        Returns:
            保存的文件路径列表
        """
        if not self._save_dir:
            raise ValueError("保存目录未设置")

        if rgb_data is None:
            raise ValueError("RGB 数据不能为空")

        # 生成时间戳
        if timestamp is None:
            timestamp = self._generate_timestamp()

        # 创建以时间戳命名的子文件夹
        capture_dir = os.path.join(self._save_dir, f"5_channels_{timestamp}")
        os.makedirs(capture_dir, exist_ok=True)

        saved_files = []

        # 确保数据类型正确
        if rgb_data.dtype != np.uint8:
            rgb_data = rgb_data.astype(np.uint8)

        # 保存全通道 RGB
        rgb_path = os.path.join(capture_dir, "full_rgb.png")
        # OpenCV 使用 BGR 格式，需要转换
        if len(rgb_data.shape) == 3 and rgb_data.shape[2] == 3:
            bgr_data = cv2.cvtColor(rgb_data, cv2.COLOR_RGB2BGR)
            cv2.imwrite(rgb_path, bgr_data)
        else:
            cv2.imwrite(rgb_path, rgb_data)
        saved_files.append(rgb_path)

        # 拆分并保存单通道
        r, g, b = split_rgb_channels(rgb_data)

        if r is not None:
            r_path = os.path.join(capture_dir, "channel_r.png")
            cv2.imwrite(r_path, r)
            saved_files.append(r_path)

        if g is not None:
            g_path = os.path.join(capture_dir, "channel_g.png")
            cv2.imwrite(g_path, g)
            saved_files.append(g_path)

        if b is not None:
            b_path = os.path.join(capture_dir, "channel_b.png")
            cv2.imwrite(b_path, b)
            saved_files.append(b_path)

        # 保存 NIR 通道
        if save_nir and nir_data is not None:
            if nir_data.dtype != np.uint8:
                nir_data = nir_data.astype(np.uint8)

            nir_path = os.path.join(capture_dir, "channel_nir.png")
            cv2.imwrite(nir_path, nir_data)
            saved_files.append(nir_path)

        self._capture_count += 1

        return saved_files

    def save_single_channel(
        self,
        data: np.ndarray,
        channel_name: str,
        timestamp: Optional[str] = None
    ) -> str:
        """
        保存单个通道图像

        Args:
            data: 图像数据
            channel_name: 通道名称（如 'r', 'g', 'b', 'nir'）
            timestamp: 时间戳字符串

        Returns:
            保存的文件路径
        """
        if not self._save_dir:
            raise ValueError("保存目录未设置")

        if timestamp is None:
            timestamp = self._generate_timestamp()

        if data.dtype != np.uint8:
            data = data.astype(np.uint8)

        file_path = os.path.join(
            self._save_dir,
            f"{timestamp}_channel_{channel_name.lower()}.png"
        )

        cv2.imwrite(file_path, data)
        return file_path

    def save_batch(
        self,
        images: Dict[str, np.ndarray],
        timestamp: Optional[str] = None
    ) -> List[str]:
        """
        批量保存图像

        Args:
            images: 图像字典，键为通道名称，值为图像数据
            timestamp: 时间戳字符串

        Returns:
            保存的文件路径列表
        """
        if not self._save_dir:
            raise ValueError("保存目录未设置")

        if timestamp is None:
            timestamp = self._generate_timestamp()

        saved_files = []

        for name, data in images.items():
            if data is not None:
                file_path = self.save_single_channel(data, name, timestamp)
                saved_files.append(file_path)

        return saved_files


class SequenceImageSaver(ImageSaver):
    """
    序列图像保存器

    用于连续采集模式，支持自动编号
    """

    def __init__(self, save_dir: Optional[str] = None, prefix: str = "capture"):
        super().__init__(save_dir)
        self._prefix = prefix
        self._sequence_number = 0

    @property
    def sequence_number(self) -> int:
        return self._sequence_number

    def reset_sequence(self):
        """重置序列号"""
        self._sequence_number = 0

    def save_next(
        self,
        rgb_data: Optional[np.ndarray],
        nir_data: Optional[np.ndarray] = None
    ) -> List[str]:
        """
        保存下一帧（自动编号）

        Args:
            rgb_data: RGB 图像数据
            nir_data: NIR 图像数据

        Returns:
            保存的文件路径列表
        """
        timestamp = f"{self._prefix}_{self._sequence_number:06d}"
        saved_files = self.save_capture(rgb_data, nir_data, timestamp)
        self._sequence_number += 1
        return saved_files

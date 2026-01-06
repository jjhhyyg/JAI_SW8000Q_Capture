"""
应用设置管理

使用 QSettings 实现跨平台的持久化配置存储
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from PySide6.QtCore import QSettings


@dataclass
class CameraSettings:
    """相机参数设置"""
    exposure_time: Optional[float] = None  # 曝光时间 (µs)
    gain: Optional[float] = None           # 增益 (dB)
    line_rate: Optional[int] = None        # 行频 (Hz)

    def is_empty(self) -> bool:
        """检查是否所有参数都为空"""
        return (self.exposure_time is None and
                self.gain is None and
                self.line_rate is None)


class AppSettings:
    """
    应用设置管理类

    使用 QSettings 存储持久化配置，自动选择适合当前平台的存储方式：
    - Windows: 注册表或 INI 文件
    - macOS: plist 文件
    - Linux: ~/.config 目录下的配置文件
    """

    # 应用标识
    ORGANIZATION = "USTB_MVIT"
    APPLICATION = "SW8000Q_Capture"

    # 设置键名
    KEY_SAVE_DIRECTORY = "image_save/directory"
    KEY_LANGUAGE = "app/language"

    def __init__(self):
        """初始化设置管理器"""
        self._settings = QSettings(
            QSettings.IniFormat,
            QSettings.UserScope,
            self.ORGANIZATION,
            self.APPLICATION
        )

    @property
    def save_directory(self) -> str:
        """
        获取保存目录

        Returns:
            保存目录路径，如果未设置或目录不存在则返回空字符串
        """
        directory = self._settings.value(self.KEY_SAVE_DIRECTORY, "")

        # 验证目录是否存在
        if directory and os.path.isdir(directory):
            return directory

        return ""

    @save_directory.setter
    def save_directory(self, directory: str):
        """
        设置保存目录

        Args:
            directory: 目录路径
        """
        if directory:
            self._settings.setValue(self.KEY_SAVE_DIRECTORY, directory)
            self._settings.sync()  # 立即写入存储

    def clear_save_directory(self):
        """清除保存目录设置"""
        self._settings.remove(self.KEY_SAVE_DIRECTORY)
        self._settings.sync()

    # ========== 语言设置 ==========

    def get_language(self) -> str:
        """
        获取当前语言设置

        Returns:
            语言代码: 'auto' (跟随系统), 'zh_CN' (中文), 'en_US' (英文)
        """
        return self._settings.value(self.KEY_LANGUAGE, "auto")

    def set_language(self, language: str):
        """
        设置语言

        Args:
            language: 语言代码 ('auto', 'zh_CN', 'en_US')
        """
        self._settings.setValue(self.KEY_LANGUAGE, language)
        self._settings.sync()

    def get_settings_file_path(self) -> str:
        """
        获取设置文件的路径（用于调试）

        Returns:
            设置文件的完整路径
        """
        return self._settings.fileName()

    # ========== 相机参数设置 ==========

    def _normalize_mac(self, mac_address: str) -> str:
        """
        规范化 MAC 地址格式

        移除分隔符，转为大写

        Args:
            mac_address: 原始 MAC 地址

        Returns:
            规范化后的 MAC 地址
        """
        # 移除常见分隔符 (冒号, 短横线, 点号)
        normalized = mac_address.replace(":", "").replace("-", "").replace(".", "")
        return normalized.upper()

    def _get_camera_key(self, mac_address: str, param: str) -> str:
        """
        获取相机参数的设置键名

        Args:
            mac_address: 相机 MAC 地址
            param: 参数名称

        Returns:
            设置键名
        """
        normalized_mac = self._normalize_mac(mac_address)
        return f"cameras/{normalized_mac}/{param}"

    def get_camera_settings(self, mac_address: str) -> CameraSettings:
        """
        获取指定相机的保存设置

        Args:
            mac_address: 相机 MAC 地址

        Returns:
            CameraSettings 对象
        """
        settings = CameraSettings()

        exposure_key = self._get_camera_key(mac_address, "exposure_time")
        gain_key = self._get_camera_key(mac_address, "gain")
        line_rate_key = self._get_camera_key(mac_address, "line_rate")

        exposure_val = self._settings.value(exposure_key)
        if exposure_val is not None:
            try:
                settings.exposure_time = float(exposure_val)
            except (ValueError, TypeError):
                pass

        gain_val = self._settings.value(gain_key)
        if gain_val is not None:
            try:
                settings.gain = float(gain_val)
            except (ValueError, TypeError):
                pass

        line_rate_val = self._settings.value(line_rate_key)
        if line_rate_val is not None:
            try:
                settings.line_rate = int(line_rate_val)
            except (ValueError, TypeError):
                pass

        return settings

    def save_camera_settings(self, mac_address: str, settings: CameraSettings):
        """
        保存相机参数设置

        Args:
            mac_address: 相机 MAC 地址
            settings: CameraSettings 对象
        """
        if settings.exposure_time is not None:
            key = self._get_camera_key(mac_address, "exposure_time")
            self._settings.setValue(key, settings.exposure_time)

        if settings.gain is not None:
            key = self._get_camera_key(mac_address, "gain")
            self._settings.setValue(key, settings.gain)

        if settings.line_rate is not None:
            key = self._get_camera_key(mac_address, "line_rate")
            self._settings.setValue(key, settings.line_rate)

        self._settings.sync()

    def save_camera_parameter(self, mac_address: str, param_name: str, value: Any):
        """
        保存单个相机参数

        Args:
            mac_address: 相机 MAC 地址
            param_name: 参数名称 ('exposure_time', 'gain', 'line_rate')
            value: 参数值
        """
        key = self._get_camera_key(mac_address, param_name)
        self._settings.setValue(key, value)
        self._settings.sync()

    def clear_camera_settings(self, mac_address: str):
        """
        清除指定相机的所有设置

        Args:
            mac_address: 相机 MAC 地址
        """
        normalized_mac = self._normalize_mac(mac_address)
        self._settings.remove(f"cameras/{normalized_mac}")
        self._settings.sync()


# 单例模式 - 全局设置实例
_app_settings = None


def get_settings() -> AppSettings:
    """
    获取全局设置实例

    Returns:
        AppSettings 实例
    """
    global _app_settings
    if _app_settings is None:
        _app_settings = AppSettings()
    return _app_settings

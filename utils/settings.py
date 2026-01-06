"""
应用设置管理

使用 QSettings 实现跨平台的持久化配置存储
"""

import os
from PySide6.QtCore import QSettings


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

    def get_settings_file_path(self) -> str:
        """
        获取设置文件的路径（用于调试）

        Returns:
            设置文件的完整路径
        """
        return self._settings.fileName()


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

"""
设备管理器 - 处理设备发现、连接、断开
"""

import eBUS as eb
from typing import List, Optional, Tuple, Any
from dataclasses import dataclass

from .utils import read_parameter, write_parameter, get_parameter_info, get_enum_entries


@dataclass
class DeviceInfo:
    """设备信息数据类"""
    connection_id: str
    display_id: str
    serial_number: str
    model_name: str
    ip_address: str = ""
    mac_address: str = ""
    device_type: str = "Unknown"

    def __str__(self):
        return f"{self.model_name} ({self.serial_number}) - {self.ip_address or self.connection_id}"


@dataclass
class SourceInfo:
    """源信息数据类 (保留用于兼容)"""
    name: str
    channel: int
    is_visible: bool  # True for RGB, False for NIR


@dataclass
class StreamChannelInfo:
    """流通道信息 - 用于 JAI FS/SW 系列双通道相机"""
    channel: int          # GigE Vision 流通道号 (0 或 1)
    name: str             # 通道名称 (如 "RGB", "NIR")
    is_visible: bool      # True for RGB/Visible, False for NIR


class DeviceManager:
    """
    设备管理器类

    负责：
    - 设备发现和枚举
    - 设备连接和断开
    - GenICam 参数读写
    - 双通道流管理 (JAI FS/SW 系列)
    """

    def __init__(self):
        self._system = eb.PvSystem()
        self._device: Optional[eb.PvDevice] = None
        self._connection_id: Optional[str] = None
        self._sources: List[SourceInfo] = []  # 保留用于兼容
        self._stream_channels: List[StreamChannelInfo] = []  # 流通道信息

    @property
    def is_connected(self) -> bool:
        """检查设备是否已连接"""
        return self._device is not None and self._device.IsConnected()

    @property
    def device(self) -> Optional[eb.PvDevice]:
        """获取 PvDevice 对象"""
        return self._device

    @property
    def connection_id(self) -> Optional[str]:
        """获取连接ID"""
        return self._connection_id

    @property
    def sources(self) -> List[SourceInfo]:
        """获取源列表 (兼容旧代码)"""
        return self._sources

    @property
    def stream_channels(self) -> List[StreamChannelInfo]:
        """获取流通道列表"""
        return self._stream_channels

    @property
    def is_dual_channel(self) -> bool:
        """检查是否支持双通道 (JAI FS/SW 系列)"""
        return len(self._stream_channels) > 1

    def find_devices(self) -> List[DeviceInfo]:
        """
        扫描并返回所有可用设备列表

        Returns:
            DeviceInfo 对象列表
        """
        devices = []

        result = self._system.Find()
        if not result.IsOK():
            print(f"设备扫描失败: {result.GetCodeString()}")
            return devices

        interface_count = self._system.GetInterfaceCount()

        for i in range(interface_count):
            interface = self._system.GetInterface(i)

            for j in range(interface.GetDeviceCount()):
                device_info = interface.GetDeviceInfo(j)

                # 安全获取字符串值的辅助函数
                def safe_str(val):
                    if val is None:
                        return ""
                    # 处理 eBUS 的 PvString 类型
                    if hasattr(val, 'GetAscii'):
                        return val.GetAscii()
                    return str(val)

                info = DeviceInfo(
                    connection_id=safe_str(device_info.GetConnectionID()),
                    display_id=safe_str(device_info.GetDisplayID()),
                    serial_number=safe_str(device_info.GetSerialNumber()),
                    model_name=safe_str(device_info.GetModelName()),
                )

                # GigE Vision 设备
                if isinstance(device_info, eb.PvDeviceInfoGEV):
                    info.device_type = "GigE Vision"
                    info.ip_address = safe_str(device_info.GetIPAddress())
                    info.mac_address = safe_str(device_info.GetMACAddress())
                # USB3 Vision 设备
                elif isinstance(device_info, eb.PvDeviceInfoU3V):
                    info.device_type = "USB3 Vision"

                devices.append(info)

        return devices

    def connect(self, connection_id: str) -> Tuple[bool, str]:
        """
        连接到指定设备

        Args:
            connection_id: 设备连接ID

        Returns:
            (success, message) 元组
        """
        if self.is_connected:
            return False, "已有设备连接，请先断开"

        result, device = eb.PvDevice.CreateAndConnect(connection_id)

        if not result.IsOK():
            return False, f"连接失败: {result.GetCodeString()} - {result.GetDescription()}"

        self._device = device
        self._connection_id = connection_id

        # 如果是 GigE Vision 设备，协商包大小
        if isinstance(device, eb.PvDeviceGEV):
            device.NegotiatePacketSize()

        # 枚举流通道 (JAI FS/SW 双通道相机)
        self._enumerate_stream_channels()

        return True, "连接成功"

    def disconnect(self) -> Tuple[bool, str]:
        """
        断开设备连接

        Returns:
            (success, message) 元组
        """
        if not self.is_connected:
            return False, "没有已连接的设备"

        try:
            # 释放设备
            eb.PvDevice.Free(self._device)
            self._device = None
            self._connection_id = None
            self._sources = []
            self._stream_channels = []

            return True, "已断开连接"
        except Exception as e:
            return False, f"断开连接时出错: {str(e)}"

    def _enumerate_stream_channels(self):
        """
        枚举流通道 (用于 JAI FS/SW 系列双通道相机)

        JAI FS/SW 相机特点:
        - 没有 SourceSelector (单源设备)
        - 但有两个 GigE Vision 流通道: Channel 0 (RGB) 和 Channel 1 (NIR)
        - 通过 GevStreamChannelSelector 配置第二通道的目标地址
        """
        self._stream_channels = []
        self._sources = []  # 同时更新兼容列表

        if not self.is_connected:
            return

        parameters = self._device.GetParameters()

        # 检查是否有 GevStreamChannelSelector (表示支持多流通道)
        gev_channel_selector = parameters.GetEnum("GevStreamChannelSelector")

        if gev_channel_selector is not None:
            # 获取可用通道数
            result, channel_count = gev_channel_selector.GetEntriesCount()
            if result.IsOK() and channel_count > 1:
                print(f"[DeviceManager] 检测到 GevStreamChannelSelector，共 {channel_count} 个流通道")
                print(f"[DeviceManager] 这是 JAI FS/SW 系列双通道相机")

                # Channel 0: RGB/Visible
                self._stream_channels.append(StreamChannelInfo(
                    channel=0,
                    name="RGB",
                    is_visible=True
                ))

                # Channel 1: NIR
                self._stream_channels.append(StreamChannelInfo(
                    channel=1,
                    name="NIR",
                    is_visible=False
                ))

                print(f"[DeviceManager] 配置双通道:")
                print(f"[DeviceManager]   - Channel 0: RGB (可见光)")
                print(f"[DeviceManager]   - Channel 1: NIR (近红外)")
            else:
                print(f"[DeviceManager] GevStreamChannelSelector 只有 {channel_count} 个通道，使用单通道模式")
                self._stream_channels.append(StreamChannelInfo(
                    channel=0,
                    name="RGB",
                    is_visible=True
                ))
        else:
            # 没有 GevStreamChannelSelector，但 JAI 相机可能仍然支持双通道
            # 尝试直接设置 GevStreamChannelSelector 值来检测
            print("[DeviceManager] 没有找到 GevStreamChannelSelector 枚举")

            # 检查是否可以通过整数方式设置通道选择器
            result = parameters.SetIntegerValue("GevStreamChannelSelector", 1)
            if result.IsOK():
                print("[DeviceManager] 可以设置 GevStreamChannelSelector=1，支持双通道")
                # 恢复到通道 0
                parameters.SetIntegerValue("GevStreamChannelSelector", 0)

                self._stream_channels.append(StreamChannelInfo(
                    channel=0,
                    name="RGB",
                    is_visible=True
                ))
                self._stream_channels.append(StreamChannelInfo(
                    channel=1,
                    name="NIR",
                    is_visible=False
                ))
            else:
                print("[DeviceManager] 不支持双通道，使用单通道模式")
                self._stream_channels.append(StreamChannelInfo(
                    channel=0,
                    name="RGB",
                    is_visible=True
                ))

        # 同时更新 sources 列表 (兼容旧代码)
        for ch in self._stream_channels:
            self._sources.append(SourceInfo(
                name=ch.name,
                channel=ch.channel,
                is_visible=ch.is_visible
            ))

        print(f"[DeviceManager] 流通道枚举完成: {len(self._stream_channels)} 个通道")

    def get_parameter(self, name: str) -> Tuple[bool, Any]:
        """
        读取参数值

        Args:
            name: 参数名称

        Returns:
            (success, value) 元组
        """
        if not self.is_connected:
            return False, None

        return read_parameter(self._device.GetParameters(), name)

    def set_parameter(self, name: str, value: Any) -> bool:
        """
        设置参数值

        Args:
            name: 参数名称
            value: 参数值

        Returns:
            是否成功
        """
        if not self.is_connected:
            return False

        return write_parameter(self._device.GetParameters(), name, value)

    def get_parameter_info(self, name: str):
        """
        获取参数详细信息

        Args:
            name: 参数名称

        Returns:
            ParameterInfo 对象或 None
        """
        if not self.is_connected:
            return None

        return get_parameter_info(self._device.GetParameters(), name)

    def get_enum_entries(self, name: str) -> List[str]:
        """
        获取枚举参数的所有可选项

        Args:
            name: 枚举参数名称

        Returns:
            可选项字符串列表
        """
        if not self.is_connected:
            return []

        return get_enum_entries(self._device.GetParameters(), name)

    def get_payload_size(self) -> int:
        """获取当前负载大小"""
        if not self.is_connected:
            return 0

        return self._device.GetPayloadSize()

    def get_image_size(self) -> Tuple[int, int]:
        """
        获取当前图像尺寸

        Returns:
            (width, height) 元组
        """
        if not self.is_connected:
            return 0, 0

        success, width = self.get_parameter("Width")
        if not success:
            width = 0

        success, height = self.get_parameter("Height")
        if not success:
            height = 0

        return width, height

    def set_image_size(self, width: int, height: int) -> bool:
        """
        设置图像尺寸

        Args:
            width: 图像宽度
            height: 图像高度

        Returns:
            是否成功
        """
        if not self.is_connected:
            return False

        success_w = self.set_parameter("Width", width)
        success_h = self.set_parameter("Height", height)

        return success_w and success_h

    def get_exposure_time(self) -> Tuple[bool, float]:
        """获取曝光时间（微秒）"""
        return self.get_parameter("ExposureTime")

    def set_exposure_time(self, value: float) -> bool:
        """设置曝光时间（微秒）"""
        return self.set_parameter("ExposureTime", value)

    def get_gain(self) -> Tuple[bool, float]:
        """获取增益（dB）"""
        # 尝试不同的增益参数名称
        success, value = self.get_parameter("Gain")
        if not success:
            success, value = self.get_parameter("GainRaw")
        return success, value

    def set_gain(self, value: float) -> bool:
        """设置增益（dB）"""
        success = self.set_parameter("Gain", value)
        if not success:
            success = self.set_parameter("GainRaw", int(value))
        return success

    def get_device_info_string(self) -> str:
        """获取设备信息字符串"""
        if not self.is_connected:
            return "未连接"

        params = self._device.GetParameters()

        success, vendor = read_parameter(params, "DeviceVendorName")
        success, model = read_parameter(params, "DeviceModelName")
        success, serial = read_parameter(params, "DeviceSerialNumber")

        info_parts = []
        if vendor:
            info_parts.append(f"厂商: {vendor}")
        if model:
            info_parts.append(f"型号: {model}")
        if serial:
            info_parts.append(f"序列号: {serial}")

        return " | ".join(info_parts) if info_parts else "设备信息不可用"

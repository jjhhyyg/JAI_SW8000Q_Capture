"""
双通道采集工作线程 - 用于 JAI FS/SW 系列双 CMOS 相机

JAI FS/SW 系列相机特点:
- 没有 SourceSelector (单源设备)
- 但有两个 GigE Vision 流通道: Channel 0 (RGB) 和 Channel 1 (NIR)
- 通过 GevStreamChannelSelector 配置第二通道的目标地址
"""

import time
import numpy as np
import eBUS as eb
from typing import Optional, Dict, List
from dataclasses import dataclass
from PySide6.QtCore import QThread, Signal

from .device_manager import DeviceManager, StreamChannelInfo


@dataclass
class FrameData:
    """帧数据"""
    data: np.ndarray
    width: int
    height: int
    timestamp: int
    block_id: int
    channel_name: str
    pixel_type: int


class DualChannelStreamWorker(QThread):
    """
    双通道采集工作线程

    用于 JAI FS/SW 系列双 CMOS 相机，同时采集 RGB (Channel 0) 和 NIR (Channel 1)

    性能优化:
    - 以相机原始帧率采集所有帧
    - 以较低帧率更新显示 (避免 GUI 卡顿)
    - 始终保留最新帧用于拍照存储
    """

    # 信号定义
    rgb_frame_ready = Signal(dict)      # RGB 帧数据 (Channel 0) - 用于显示
    nir_frame_ready = Signal(dict)      # NIR 帧数据 (Channel 1) - 用于显示
    statistics_updated = Signal(dict)   # 统计信息更新
    error_occurred = Signal(str)        # 错误发生
    acquisition_started = Signal()      # 采集已启动
    acquisition_stopped = Signal()      # 采集已停止

    BUFFER_COUNT = 16

    # 显示帧率限制 (Hz) - 降低此值可减少 GUI 负担
    DISPLAY_FPS_LIMIT = 15  # 每秒最多更新 15 帧显示

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._running = False

        # 流和管道
        self._stream_rgb: Optional[eb.PvStreamGEV] = None
        self._stream_nir: Optional[eb.PvStreamGEV] = None
        self._pipeline_rgb: Optional[eb.PvPipeline] = None
        self._pipeline_nir: Optional[eb.PvPipeline] = None

        # 最新帧数据 (用于拍照保存 - 始终保持最新)
        self._latest_rgb_frame: Optional[FrameData] = None
        self._latest_nir_frame: Optional[FrameData] = None

        # 显示帧率控制
        self._display_interval = 1.0 / self.DISPLAY_FPS_LIMIT  # 显示更新间隔 (秒)
        self._last_rgb_display_time = 0.0
        self._last_nir_display_time = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def latest_rgb_frame(self) -> Optional[FrameData]:
        return self._latest_rgb_frame

    @property
    def latest_nir_frame(self) -> Optional[FrameData]:
        return self._latest_nir_frame

    def set_display_fps(self, fps: int):
        """
        设置显示帧率限制

        Args:
            fps: 目标显示帧率 (1-60)
        """
        fps = max(1, min(60, fps))
        self._display_interval = 1.0 / fps
        print(f"[DualChannelWorker] 显示帧率限制设置为 {fps} FPS")

    def _open_streams(self) -> bool:
        """打开双通道流"""
        if not self.device_manager.is_connected:
            self.error_occurred.emit("设备未连接")
            return False

        device = self.device_manager.device
        connection_id = self.device_manager.connection_id
        parameters = device.GetParameters()

        # 辅助函数: 将 PvString 转换为 Python 字符串
        def to_str(pv_val):
            if pv_val is None:
                return ""
            if hasattr(pv_val, 'GetAscii'):
                return pv_val.GetAscii()
            return str(pv_val)

        # 确保 connection_id 是字符串
        connection_id = to_str(connection_id)

        # ========== Channel 0: RGB/Visible ==========
        print("[DualChannelWorker] 打开 Channel 0 (RGB) 流...")

        self._stream_rgb = eb.PvStreamGEV()
        result = self._stream_rgb.Open(connection_id, 0, 0)  # channel 0
        if result.IsFailure():
            print(f"[DualChannelWorker] 打开 RGB 流失败: {result.GetCodeString()}")
            self.error_occurred.emit(f"打开 RGB 流失败: {result.GetCodeString()}")
            return False

        rgb_local_ip = to_str(self._stream_rgb.GetLocalIPAddress())
        rgb_local_port = self._stream_rgb.GetLocalPort()
        print(f"[DualChannelWorker] RGB 流本地地址: {rgb_local_ip}:{rgb_local_port}")

        # 设置 Channel 0 目标地址 (通常自动配置，但显式设置更可靠)
        if isinstance(device, eb.PvDeviceGEV):
            device.SetStreamDestination(rgb_local_ip, rgb_local_port, 0)
            print("[DualChannelWorker] 已设置 Channel 0 目标地址")

        # 创建 RGB 管道
        payload_size = device.GetPayloadSize()
        print(f"[DualChannelWorker] RGB payload_size = {payload_size}")

        self._pipeline_rgb = eb.PvPipeline(self._stream_rgb)
        self._pipeline_rgb.SetBufferSize(payload_size)
        self._pipeline_rgb.SetBufferCount(self.BUFFER_COUNT)

        # ========== Channel 1: NIR ==========
        if self.device_manager.is_dual_channel:
            print("[DualChannelWorker] 打开 Channel 1 (NIR) 流...")

            self._stream_nir = eb.PvStreamGEV()
            result = self._stream_nir.Open(connection_id, 0, 1)  # channel 1
            if result.IsFailure():
                print(f"[DualChannelWorker] 打开 NIR 流失败: {result.GetCodeString()}")
                self.error_occurred.emit(f"打开 NIR 流失败: {result.GetCodeString()}")
                self._close_streams()
                return False

            nir_local_ip = to_str(self._stream_nir.GetLocalIPAddress())
            nir_local_port = self._stream_nir.GetLocalPort()
            print(f"[DualChannelWorker] NIR 流本地地址: {nir_local_ip}:{nir_local_port}")

            # ========== 关键: 配置相机将 NIR 数据发送到我们的 Channel 1 流 ==========
            # 这是 JAI 双通道相机的核心配置
            print("[DualChannelWorker] 配置相机 TransportLayerControl...")

            # 选择 Channel 1
            gev_channel_selector = parameters.GetEnum("GevStreamChannelSelector")
            if gev_channel_selector:
                result = gev_channel_selector.SetValue(1)
                print(f"[DualChannelWorker] GevStreamChannelSelector=1: {result.GetCodeString()}")
            else:
                # 尝试整数方式
                result = parameters.SetIntegerValue("GevStreamChannelSelector", 1)
                print(f"[DualChannelWorker] GevStreamChannelSelector=1 (int): {result.GetCodeString()}")

            # 设置 Channel 1 目标端口
            result = parameters.SetIntegerValue("GevSCPHostPort", nir_local_port)
            print(f"[DualChannelWorker] GevSCPHostPort={nir_local_port}: {result.GetCodeString()}")

            # 设置 Channel 1 目标 IP 地址 (转换为整数)
            ip_parts = nir_local_ip.split('.')
            if len(ip_parts) == 4:
                ip_int = (int(ip_parts[0]) << 24) | (int(ip_parts[1]) << 16) | \
                         (int(ip_parts[2]) << 8) | int(ip_parts[3])
                result = parameters.SetIntegerValue("GevSCDA", ip_int)
                print(f"[DualChannelWorker] GevSCDA={nir_local_ip} ({ip_int}): {result.GetCodeString()}")

            # 恢复选择 Channel 0 (以便后续操作使用默认通道)
            if gev_channel_selector:
                gev_channel_selector.SetValue(0)
            else:
                parameters.SetIntegerValue("GevStreamChannelSelector", 0)

            # 创建 NIR 管道
            self._pipeline_nir = eb.PvPipeline(self._stream_nir)
            self._pipeline_nir.SetBufferSize(payload_size)
            self._pipeline_nir.SetBufferCount(self.BUFFER_COUNT)

            print("[DualChannelWorker] 双通道流配置完成")
        else:
            print("[DualChannelWorker] 单通道模式，不打开 NIR 流")

        return True

    def _close_streams(self):
        """关闭所有流"""
        print("[DualChannelWorker] 关闭流...")

        if self._pipeline_rgb:
            if self._pipeline_rgb.IsStarted():
                self._pipeline_rgb.Stop()
            self._pipeline_rgb = None

        if self._pipeline_nir:
            if self._pipeline_nir.IsStarted():
                self._pipeline_nir.Stop()
            self._pipeline_nir = None

        if self._stream_rgb:
            if self._stream_rgb.IsOpen():
                self._stream_rgb.Close()
            self._stream_rgb = None

        if self._stream_nir:
            if self._stream_nir.IsOpen():
                self._stream_nir.Close()
            self._stream_nir = None

        print("[DualChannelWorker] 流已关闭")

    def _start_pipelines(self) -> bool:
        """启动管道"""
        print("[DualChannelWorker] 启动管道...")

        if self._pipeline_rgb:
            result = self._pipeline_rgb.Start()
            if result.IsFailure():
                print(f"[DualChannelWorker] RGB 管道启动失败: {result.GetCodeString()}")
                return False
            print("[DualChannelWorker] RGB 管道已启动")

        if self._pipeline_nir:
            result = self._pipeline_nir.Start()
            if result.IsFailure():
                print(f"[DualChannelWorker] NIR 管道启动失败: {result.GetCodeString()}")
                return False
            print("[DualChannelWorker] NIR 管道已启动")

        return True

    def _stop_pipelines(self):
        """停止管道"""
        if self._pipeline_rgb and self._pipeline_rgb.IsStarted():
            self._pipeline_rgb.Stop()
        if self._pipeline_nir and self._pipeline_nir.IsStarted():
            self._pipeline_nir.Stop()

    def _start_acquisition(self) -> bool:
        """启动相机采集 (只需执行一次)"""
        print("[DualChannelWorker] 启动相机采集...")

        device = self.device_manager.device
        parameters = device.GetParameters()

        # 启用流
        device.StreamEnable()

        # 发送 AcquisitionStart 命令
        acq_start = parameters.Get("AcquisitionStart")
        if acq_start:
            result = acq_start.Execute()
            print(f"[DualChannelWorker] AcquisitionStart: {result.GetCodeString()}")
            return result.IsOK()

        return False

    def _stop_acquisition(self):
        """停止相机采集"""
        print("[DualChannelWorker] 停止相机采集...")

        device = self.device_manager.device
        parameters = device.GetParameters()

        # 发送 AcquisitionStop 命令
        acq_stop = parameters.Get("AcquisitionStop")
        if acq_stop:
            acq_stop.Execute()

        # 禁用流
        device.StreamDisable()

    def _retrieve_frame(self, pipeline: eb.PvPipeline, channel_name: str, timeout_ms: int = 50) -> Optional[FrameData]:
        """从管道检索帧"""
        if not pipeline or not pipeline.IsStarted():
            return None

        try:
            result, pvbuffer, op_result = pipeline.RetrieveNextBuffer(timeout_ms)

            if result.IsOK() and op_result.IsOK():
                payload_type = pvbuffer.GetPayloadType()

                if payload_type == eb.PvPayloadTypeImage:
                    image = pvbuffer.GetImage()
                    image_data = image.GetDataPointer()

                    # 复制数据
                    frame_data = FrameData(
                        data=image_data.copy(),
                        width=image.GetWidth(),
                        height=image.GetHeight(),
                        timestamp=pvbuffer.GetTimestamp(),
                        block_id=pvbuffer.GetBlockID(),
                        channel_name=channel_name,
                        pixel_type=image.GetPixelType()
                    )

                    pipeline.ReleaseBuffer(pvbuffer)
                    return frame_data

                pipeline.ReleaseBuffer(pvbuffer)

            return None

        except Exception as e:
            print(f"[DualChannelWorker] 检索 {channel_name} 帧时出错: {str(e)}")
            return None

    def run(self):
        """线程主循环"""
        try:
            # 打开流
            if not self._open_streams():
                return

            # 启动管道
            if not self._start_pipelines():
                self._close_streams()
                return

            # 启动采集
            if not self._start_acquisition():
                self.error_occurred.emit("启动采集失败")
                self._stop_pipelines()
                self._close_streams()
                return

            self._running = True
            self.acquisition_started.emit()

            # 帧计数器 (采集 vs 显示)
            rgb_capture_count = 0
            nir_capture_count = 0
            rgb_display_count = 0
            nir_display_count = 0
            last_stats_time = time.time()
            last_debug_time = time.time()

            print(f"[DualChannelWorker] 开始采集循环... (显示帧率限制: {self.DISPLAY_FPS_LIMIT} FPS)")

            # 主采集循环
            while self._running:
                current_time = time.time()

                # 检索 RGB 帧 (Channel 0)
                if self._pipeline_rgb:
                    frame = self._retrieve_frame(self._pipeline_rgb, "RGB", 50)
                    if frame:
                        rgb_capture_count += 1
                        # 始终保存最新帧 (用于拍照存储)
                        self._latest_rgb_frame = frame

                        # 帧率限制: 只在达到显示间隔时才发送显示信号
                        if current_time - self._last_rgb_display_time >= self._display_interval:
                            frame_dict = {
                                'data': frame.data,
                                'width': frame.width,
                                'height': frame.height,
                                'timestamp': frame.timestamp,
                                'block_id': frame.block_id,
                                'source_name': frame.channel_name,
                                'pixel_type': frame.pixel_type
                            }
                            self.rgb_frame_ready.emit(frame_dict)
                            self._last_rgb_display_time = current_time
                            rgb_display_count += 1

                # 检索 NIR 帧 (Channel 1)
                if self._pipeline_nir:
                    frame = self._retrieve_frame(self._pipeline_nir, "NIR", 50)
                    if frame:
                        nir_capture_count += 1
                        # 始终保存最新帧 (用于拍照存储)
                        self._latest_nir_frame = frame

                        # 帧率限制: 只在达到显示间隔时才发送显示信号
                        if current_time - self._last_nir_display_time >= self._display_interval:
                            frame_dict = {
                                'data': frame.data,
                                'width': frame.width,
                                'height': frame.height,
                                'timestamp': frame.timestamp,
                                'block_id': frame.block_id,
                                'source_name': frame.channel_name,
                                'pixel_type': frame.pixel_type
                            }
                            self.nir_frame_ready.emit(frame_dict)
                            self._last_nir_display_time = current_time
                            nir_display_count += 1

                # 每 5 秒输出帧统计
                if current_time - last_debug_time >= 5.0:
                    print(f"[DualChannelWorker] 帧统计: RGB 采集={rgb_capture_count} 显示={rgb_display_count}, "
                          f"NIR 采集={nir_capture_count} 显示={nir_display_count}")
                    last_debug_time = current_time

                # 定期更新统计信息 (每 0.5 秒)
                if current_time - last_stats_time >= 0.5:
                    stats = {}

                    if self._stream_rgb:
                        params = self._stream_rgb.GetParameters()
                        result, fps = params.GetFloatValue("AcquisitionRate")
                        result2, bandwidth = params.GetFloatValue("Bandwidth")
                        stats['RGB'] = {
                            'fps': fps if result.IsOK() else 0,
                            'bandwidth': bandwidth / 1000000.0 if result2.IsOK() else 0,
                            'frame_count': rgb_capture_count,
                            'display_count': rgb_display_count
                        }

                    if self._stream_nir:
                        params = self._stream_nir.GetParameters()
                        result, fps = params.GetFloatValue("AcquisitionRate")
                        result2, bandwidth = params.GetFloatValue("Bandwidth")
                        stats['NIR'] = {
                            'fps': fps if result.IsOK() else 0,
                            'bandwidth': bandwidth / 1000000.0 if result2.IsOK() else 0,
                            'frame_count': nir_capture_count,
                            'display_count': nir_display_count
                        }

                    if stats:
                        self.statistics_updated.emit(stats)

                    last_stats_time = current_time

        except Exception as e:
            print(f"[DualChannelWorker] 采集线程异常: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"采集线程异常: {str(e)}")

        finally:
            # 停止采集
            self._stop_acquisition()
            self._stop_pipelines()
            self._close_streams()

            self._running = False
            self.acquisition_stopped.emit()
            print("[DualChannelWorker] 采集线程结束")

    def stop(self):
        """停止采集"""
        print("[DualChannelWorker] 请求停止采集...")
        self._running = False
        self.wait(5000)

    def capture_single_frame(self) -> Dict[str, Optional[FrameData]]:
        """获取当前帧用于保存"""
        return {
            'rgb': self._latest_rgb_frame,
            'nir': self._latest_nir_frame
        }


# 保持向后兼容的别名
DualStreamWorker = DualChannelStreamWorker

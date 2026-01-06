# JAI SW-8000Q 采集软件

[English](README.md)

基于 PySide6 的 JAI SW-8000Q 四棱镜线扫相机采集软件，支持 RGB + NIR 双通道同步采集。

## 功能特性

- **设备发现**: 自动扫描网络上的 GigE Vision 相机
- **双通道采集**: 同时采集 RGB (Channel 0) 和 NIR (Channel 1) 图像
- **实时预览**: 支持可配置的显示帧率限制
- **四通道分离**: 将 RGB 流分离为 R、G、B 三通道，加上独立的 NIR 通道
- **参数控制**: 调节曝光时间、增益、行频、图像尺寸等参数
- **图像采集**: 支持 PNG/TIFF 格式保存，可分通道存储

## 系统要求

- Python 3.9
- [eBUS SDK](https://www.jai.com/support-software/jai-software/)
- [eBUS SDK Python API](https://www.jai.com/support-software/jai-software/) (应该与 eBUS SDK 版本兼容)
- PySide6
- NumPy
- OpenCV (cv2)

## 安装

1. 安装 eBUS SDK
2. 安装 eBUS SDK Python API
2. 安装 Python 依赖:

```bash
pip install PySide6 numpy opencv-python
```

3. 确保 eBUS Python 绑定在 Python 环境中可用

## 使用方法

```bash
python main.py
```

### 操作流程

1. **连接设备**: 点击"扫描设备"查找相机，选择后点击"连接"
2. **配置参数**: 在控制面板中调节曝光、增益、行频等参数
3. **开始采集**: 点击"开始采集"启动双通道流
4. **拍照保存**: 点击"拍照"保存当前帧

## 项目结构

```
sw8000q_capture/
├── main.py                 # 程序入口
├── camera/
│   ├── device_manager.py   # 设备管理和 GenICam 参数访问
│   ├── dual_stream_worker.py # 双通道采集工作线程
│   └── utils.py            # 参数读写工具函数
├── ui/
│   ├── main_window.py      # 主窗口
│   ├── device_selector.py  # 设备选择对话框
│   ├── control_panel.py    # 参数控制面板
│   ├── preview_widget.py   # 图像预览组件
│   └── channel_panel.py    # 四通道显示面板
└── utils/
    └── image_saver.py      # 图像保存工具
```

## 技术说明

### JAI SW-8000Q 相机

SW-8000Q 是一款四棱镜线扫相机，具有以下特点:
- 单 GenICam 源 (无 SourceSelector)
- 两个 GigE Vision 流通道:
  - Channel 0: RGB/可见光
  - Channel 1: NIR (近红外)
- 通过 `GevStreamChannelSelector` 配置多通道流

### 双通道配置

软件配置相机的传输层，将数据发送到:
- RGB 数据 → Channel 0 (默认)
- NIR 数据 → Channel 1 (需要通过 `GevSCPHostPort` 和 `GevSCDA` 显式配置目标地址)

### 性能优化

- 全帧率采集两个通道的图像数据
- 可配置的显示帧率限制 (默认 15 FPS)，减少 GUI 开销
- 始终保留最新帧用于拍照操作

## 构建安装程序

### 前置条件

1. [NSIS](https://nsis.sourceforge.io/) (Nullsoft Scriptable Install System)
2. [Nuitka](https://nuitka.net/) 用于创建 `main.dist/` 文件夹
3. eBUS SDK 安装程序放置在 `dependencies/` 文件夹中

### 构建步骤

1. 编译 Python 应用程序:
```bash
build_nuitka.bat
```

2. 将 eBUS SDK 安装程序放入 `dependencies/` 文件夹:
```
dependencies/eBUS SDK 64-bit for JAI.6.5.3.7155.exe
```

3. 构建安装程序:
```batch
build_installer.bat
```
或手动执行:
```batch
makensis installer.nsi
```

4. 输出文件: `JAI_SW8000Q_Capture_Setup.exe`

### 安装程序功能

- 检测 eBUS SDK 是否已安装 (通过 `PUREGEV_ROOT` 环境变量)
- 如未安装则提示安装 SDK
- 可选的桌面快捷方式
- 开始菜单快捷方式
- 完整的卸载支持（不包括eBUS SDK卸载）

## 许可证

本项目采用 **[GNU 通用公共许可证 v3.0](LICENSE)** (GNU General Public License) 进行许可。

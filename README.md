# JAI SW-8000Q Capture

A PySide6-based capture application for JAI SW-8000Q 4-CMOS prism line scan camera with dual-channel (RGB + NIR) streaming support.

## Features

- **Device Discovery**: Auto-detect GigE Vision cameras on the network
- **Dual-Channel Streaming**: Simultaneous RGB (Channel 0) and NIR (Channel 1) acquisition
- **Real-time Preview**: Live preview with configurable display frame rate limiting
- **4-Channel Separation**: Split RGB stream into individual R, G, B channels plus NIR
- **Parameter Control**: Adjust exposure time, gain, line rate, and image size
- **Image Capture**: Save individual frames as PNG/TIFF with channel separation

## Requirements

- Python 3.8+
- [eBUS SDK](https://www.pleora.com/products/ebus-sdk/) (Pleora)
- PySide6
- NumPy
- OpenCV (cv2)

## Installation

1. Install eBUS SDK from Pleora
2. Install Python dependencies:

```bash
pip install PySide6 numpy opencv-python
```

3. Ensure eBUS Python bindings are available in your Python environment

## Usage

```bash
python main.py
```

### Workflow

1. **Connect**: Click "Scan Devices" to find cameras, select one, and click "Connect"
2. **Configure**: Adjust parameters (exposure, gain, line rate) in the control panel
3. **Stream**: Click "Start Acquisition" to begin dual-channel streaming
4. **Capture**: Click "Capture" to save the current frame

## Project Structure

```
sw8000q_capture/
├── main.py                 # Application entry point
├── camera/
│   ├── device_manager.py   # Device discovery and GenICam parameter access
│   ├── dual_stream_worker.py # Dual-channel acquisition thread
│   └── utils.py            # Parameter read/write utilities
├── ui/
│   ├── main_window.py      # Main application window
│   ├── device_selector.py  # Device selection dialog
│   ├── control_panel.py    # Parameter control widgets
│   ├── preview_widget.py   # Image preview widget
│   └── channel_panel.py    # 4-channel display panel
└── utils/
    └── image_saver.py      # Image saving utilities
```

## Technical Notes

### JAI SW-8000Q Camera

The SW-8000Q is a 4-CMOS prism line scan camera with:
- Single GenICam source (no SourceSelector)
- Two GigE Vision stream channels:
  - Channel 0: RGB/Visible light
  - Channel 1: NIR (Near-Infrared)
- Configured via `GevStreamChannelSelector` for multi-channel streaming

### Dual-Channel Configuration

The application configures the camera's Transport Layer to send:
- RGB data to Channel 0 (default)
- NIR data to Channel 1 (requires explicit destination address configuration via `GevSCPHostPort` and `GevSCDA`)

### Performance Optimization

- Full frame rate capture for both channels
- Configurable display frame rate limiting (default 15 FPS) to reduce GUI overhead
- Latest frames always retained for capture operations

## License

This project is provided as a sample application for eBUS SDK.

## Acknowledgments

- [Pleora Technologies](https://www.pleora.com/) for the eBUS SDK
- [JAI](https://www.jai.com/) for the SW-8000Q camera

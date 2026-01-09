# RacerTech RT1809/RT9806 固件升级工具

## 项目简介

RacerTech 固件升级工具是一个集成化的固件烧录和升级解决方案，支持通过 UART（ISP模式）和 USB（OTA模式）两种方式对 RacerTech RT1809 和 RT9806 芯片进行固件升级。

## 功能特性

### 1. ISP 烧录功能
- 通过 UART 串口进行固件烧录
- 支持多种波特率（115200、307200）
- 实时显示烧录进度和地址信息
- 支持烧录过程取消操作
- 自动检测串口占用状态

### 2. OTA 升级功能
- **RT1809 芯片支持**：
  - 固件升级（Firmware OTA）
  - 影像资源升级（Resource OTA）
  - 设备信息获取（屏数量、分辨率、图像数）
  - 视频转BIN文件工具
- **RT9806 芯片支持**：
  - 固件升级（Firmware OTA）
  - 支持驱动模式和libusb模式自动切换

### 3. 影像转换工具
- 视频文件转BIN格式
- 支持帧提取和图像处理
- 生成用于OTA升级的BIN文件和头文件

## 系统要求

### 操作系统
- Windows 10/11

### Python 环境（开发模式）
- Python 3.7 或更高版本

### 依赖库
```bash
# 核心依赖
pyserial          # 串口通信
pyusb             # USB通信

# 影像转换工具依赖（可选）
opencv-python     # 视频处理
pillow            # 图像处理
numpy             # 数值计算
```

### 硬件要求
- USB 接口（用于OTA升级）
- UART 串口（用于ISP烧录）
- 支持的设备：
  - RT1809（VID: 0x34C7, PID: 0x8888）
  - RT9806（VID: 0x34C7, PID: 0x9806）

## 项目结构

```
RT1809_Tools/
├── rt1809_tools_main.py          # 主程序入口
├── rt1809_tools_gui.py           # GUI主界面
├── rt1809_tools_config.py        # 配置和常量定义
├── rt1809_tools_isp_programmer.py    # ISP烧录器实现
├── rt1809_tools_isp_protocol.py      # ISP协议实现
├── rt1809_tools_isp_crc.py            # ISP CRC计算
├── rt1809_tools_ota_func.py           # OTA功能函数
├── rt1809_tools_video_converter.py    # 视频转换工具
├── rt1809_tools_release_version.py    # 版本管理工具
├── rt1809_tools_ultils.py             # 工具函数
├── rt1809_tools_build.spec            # PyInstaller打包配置
├── rt1809_tools_version.txt           # 版本信息
├── Isp_bin/                            # ISP固件文件目录
│   ├── ISP_WriterCMD.bin
│   └── ISP_DriverCode.bin
├── example_*.py                         # 示例和测试文件
├── test_*.py                            # 测试脚本
├── *.dll                                # 动态链接库文件
└── *.ico                                # 图标文件
```

## 安装与使用

### 开发模式运行

1. **克隆或下载项目**
```bash
cd RT1809_Tools
```

2. **安装依赖**
```bash
pip install pyserial pyusb
# 如果需要使用影像转换工具
pip install opencv-python pillow numpy
```

3. **运行程序**
```bash
python -m rt1809_tools_main
# 或
python rt1809_tools_main.py
```

### 打包为可执行文件

1. **安装 PyInstaller**
```bash
pip install pyinstaller
```

2. **执行打包**
```bash
python -m PyInstaller rt1809_tools_build.spec
```

3. **获取可执行文件**
打包后的可执行文件位于 `./dist/` 目录下

### 更新版本号

修改rt1809_tools_configpy文件中的变量 __version__ ，然后执行 
```bash
python -m rt1809_tools_release_version
```

## 使用说明

### ISP 烧录

1. 连接设备到串口
2. 选择正确的串口和波特率
3. 选择要烧录的固件文件（.bin格式）
4. 点击"开始烧录"
5. 等待烧录完成

**注意事项**：
- 确保串口未被其他程序占用
- 烧录过程中请勿断开连接
- 支持烧录过程中取消操作

### OTA 升级

#### RT1809 芯片

1. 通过USB连接设备
2. 选择芯片类型为"RT1809"
3. 点击"获取设备信息"查看屏信息
4. 选择升级模式：
   - **固件升级**：用于升级MCU固件
   - **影像升级**：用于升级显示资源
5. 选择要升级的文件
6. 点击"开始OTA"

#### RT9806 芯片

1. 通过USB连接设备
2. 选择芯片类型为"RT9806"
3. 选择固件文件（RT9806仅支持固件升级）
4. 点击"开始OTA"

**注意事项**：
- 确保设备已正确连接并识别
- OTA过程中请勿断开USB连接
- 升级过程中不要断电

### 影像转换工具

1. 在OTA升级界面点击"影像转换工具"按钮
2. 选择视频文件和输出路径
3. 设置提取参数（帧数量等）
4. 确保视频分辨率与设备信息匹配
5. 生成BIN文件用于OTA升级

**注意**：此功能仅支持RT1809芯片

## 技术架构

### 核心模块

1. **GUI模块** (`rt1809_tools_gui.py`)
   - 基于 tkinter 的图形界面
   - 双选项卡设计（ISP/OTA）
   - 多线程处理，避免界面冻结
   - 实时进度显示和状态更新

2. **ISP模块**
   - `rt1809_tools_isp_programmer.py`: ISP烧录器主类
   - `rt1809_tools_isp_protocol.py`: 串口通信协议
   - `rt1809_tools_isp_crc.py`: CRC校验计算

3. **OTA模块** (`rt1809_tools_ota_func.py`)
   - USB通信控制
   - 加密传输支持（ECIES加密）
   - 进度回调机制
   - 多芯片支持（RT1809/RT9806）

4. **配置模块** (`rt1809_tools_config.py`)
   - 芯片参数配置
   - USB VID/PID定义
   - ISP协议参数
   - 命令和响应枚举

### 通信协议

- **ISP协议**：基于串口的自定义协议，支持波特率切换、扇区擦除、块擦除、编程、校验等操作
- **OTA协议**：基于USB Control Transfer和Bulk Transfer，支持加密传输

## 版本信息

- **当前版本**: 1.0.1
- **作者**: RacerTech
- **更新日期**: 2025

## 常见问题

### Q: 串口无法识别或打开失败？
A: 
- 检查串口驱动是否已安装
- 确认串口未被其他程序占用
- 尝试刷新串口列表

### Q: USB设备无法识别？
A:
- 检查USB驱动是否正确安装
- 确认设备VID/PID是否匹配
- 对于RT9806，检查是否支持驱动模式

### Q: OTA升级失败？
A:
- 确认设备已进入OTA模式
- 检查文件格式是否正确
- 查看错误提示信息
- 尝试重新连接设备

### Q: 影像转换工具无法使用？
A:
- 确认已安装 opencv-python、pillow、numpy
- 检查视频文件格式是否支持
- 确认芯片类型为RT1809（RT9806不支持）

## 开发说明

### 代码规范
- 使用Python类型提示
- 模块化设计，功能分离
- 异常处理和错误提示完善

### 扩展开发
- 添加新芯片支持：在 `rt1809_tools_config.py` 中添加芯片定义
- 添加新功能：在对应模块中扩展，GUI中集成

## 许可证

Copyright © 2025 RacerTech. All rights reserved.

## 技术支持

如有问题或建议，请联系 RacerTech 技术支持团队。

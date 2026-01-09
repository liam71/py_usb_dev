"""配置和常量定义"""

from enum import IntEnum

#开启GUI
USE_GUI = True

# 版本信息
__version__ = "1.0.2"
__author__ = "RacerTech"

APP_ICON = "app.ico"

# OTA测试路径
OTA_FILE_PATH = None
OTA_RES_FILE_PATH = None

# 测试模式
OTA = 1
OTA_RES = 2
APP_model_ = OTA_RES

# 芯片类型
CHIP_RT1809 = "RT1809"
CHIP_RT9806 = "RT9806"

# OTA固件大小
FW_SIZE = 64 * 1024
OTA_TxBLOCK_SIZE = 2048

# USB设备VID/PID
USB_VID_RT1809 = 0x34C7
USB_PID_RT1809 = 0x8888
USB_VID_RT9806 = 0x34C7
USB_PID_RT9806 = 0x9806


class ISPConfig:
    """ISP配置参数"""
    INITIAL_BAUDRATE = 38400
    ISP_BAUDRATE = 115200
    NEW_BAUDRATE = 307200
    BLOCK_SIZE = 0x10000  # 64K
    PROGRAM_SIZE = 0x0800  # 2KB
    START_CODE = 0xA5
    DEVICE_ID = b"GPCM2100A"
    ISP_CMD_FILE = "Isp_bin/ISP_WriterCMD.bin"
    ISP_DRIVER_FILE = "Isp_bin/ISP_DriverCode.bin"


class Command(IntEnum):
    """ISP命令定义"""
    BAUDRATE = 0x00
    EXIT_ISP_MODE = 0x01
    BOOT_UPDATE_EN = 0x02
    CHECK_ID = 0x03
    SECTOR_ERASE = 0x10
    BLOCK_ERASE = 0x11
    PROGRAM = 0x20
    VERIFY = 0x21


class Response(IntEnum):
    """IC应答定义"""
    ACK = 0x0A
    ERROR = 0xE0
    RECEIVE_TIMEOUT = 0xE1
    DATA_LENGTH_ERROR = 0xE2
    START_CODE_ERROR = 0xE3
    COMMAND_NOT_RECOGNIZED = 0xE4
    CHECKSUM_FAIL = 0xE5
    ILLEGAL_ADDRESS = 0xE6
    CODE_CHECKSUM_FAIL = 0xE7
    PROGRAM_LENGTH_ERROR = 0xE8
    HARDWARE_ID_FAIL = 0xE9
    FLASH_ID_FAIL = 0xEA
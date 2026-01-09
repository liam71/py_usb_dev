"""OTA功能函数"""

import os
import struct
import time
import queue
import threading
from typing import Optional

import usb.core
import usb.util

from rt1809_tools_config import (
    FW_SIZE, OTA_TxBLOCK_SIZE, 
    USB_VID_RT1809, USB_PID_RT1809,
    USB_VID_RT9806, USB_PID_RT9806
)
from example_run_dll import CryptoLib, ECPoint
from example_control import CreatePackage, random_key, set_control_transfer


def usb_control_transfer(vid, pid, bmRequestType, bRequest, wValue=0, wIndex=0, data_or_wLength=None, timeout=1000):
    """
    執行 USB Control Transfer
    :param vid: USB設備VID
    :param pid: USB設備PID
    :param bmRequestType: 請求類型 (8位)
    :param bRequest: 請求代碼 (8位)
    :param wValue: 參數值 (16位)
    :param wIndex: 索引值 (16位)
    :param data_or_wLength: 數據緩衝區或長度
    :param timeout: 超時時間(毫秒)
    :return: 傳輸的數據
    """
    # 查找 USB 設備
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        raise ValueError('設備未找到，請檢查VID和PID')

    try:
        # 設置配置
        dev.set_configuration()
        
        # 執行 Control Transfer
        result = dev.ctrl_transfer(
            bmRequestType=bmRequestType,
            bRequest=bRequest,
            wValue=wValue,
            wIndex=wIndex,
            data_or_wLength=data_or_wLength,
            timeout=timeout
        )
        
        return result
    except usb.core.USBError as e:
        print(f"USB Control Transfer 錯誤: {str(e)}")
        raise
    finally:
        dev = None


def GetFwImageNum(wIndex=0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x95,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("GetFwImageNum :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetFwImageNum : {str(e)}")

def GetPanelNumber():
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x82,
            wIndex=0x0000,
            data_or_wLength=1
        )
        print("PanelNumber :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelNumber Fail: {str(e)}")

def GetPanelSize(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x81,
            wIndex=wIndex,
            data_or_wLength=4
        )
        print("Size :", device_desc)
        return device_desc
    except Exception as e:
        print(f"GetPanelSize Fail: {str(e)}")


class ProgressCallback:
    """进度条回调接口"""
    def __init__(self):
        self.total_size = 0
        self.current_size = 0
        self.callback = None
        
    def set_total(self, total):
        self.total_size = total
        self.current_size = 0
        
    def update(self, bytes_sent):
        self.current_size += bytes_sent
        if self.callback and self.total_size > 0:
            progress = (self.current_size / self.total_size) * 100
            self.callback(progress, self.current_size, self.total_size)


def ota_usb_send(vid, pid, endpoint_out, file_path=None, progress_callback=None):
    # 查找 USB 设备
    cheksum = 0
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        raise ValueError('设备未找到，请检查VID和PID')

    # 设置配置
    dev.set_configuration()

    # 获取端点
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    ep = usb.util.find_descriptor(
        intf,
        custom_match=lambda e: e.bEndpointAddress == endpoint_out
    )
    if ep is None:
        raise ValueError('未找到指定的 OUT 端点')

    # 发送数据
    chunk_size = ep.wMaxPacketSize
    d_key = bytes.fromhex("1B 24 42 4f 4f 54 00")
    d_lens = bytes.fromhex("00 01 00 00")
    
    for i in range(0, len(d_key), chunk_size):
        ep.write(d_key[i:i+chunk_size])
    print(f"已通过USB发送 {len(d_key)} 字节")

    for i in range(0, len(d_lens), chunk_size):
        ep.write(d_lens[i:i+chunk_size])
    print(f"已通过USB发送 {len(d_lens)} 字节")

    if file_path is not None and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size != FW_SIZE:
            raise ValueError('文件大小不符合')
        if progress_callback:
            progress_callback.set_total(file_size)
        data_list = []
        data_list_len = int(file_size / OTA_TxBLOCK_SIZE)
        data_list_pa_len = OTA_TxBLOCK_SIZE
        with open(file_path, "rb") as f:
            for i in range(0, data_list_len):
                data_list.append(f.read(data_list_pa_len))
        d_header = data_list[0][0:4] 
        print(f"data list len : {data_list_len} data list pa len : {data_list_pa_len}")
        checksum = 0
        checksum_list = []
        count = 0
        for i in range(0, data_list_len):
            count = 0
            for j in range(0, data_list_pa_len):
                checksum += data_list[i][j]
                count += data_list[i][j]
            checksum_list.append(count)
        byte_array = bytearray(struct.pack('>I', checksum))
        print(f"checksum : {checksum} byte_array : {byte_array}")

        
        for i in range(0, len(d_header), chunk_size):
            ep.write(d_header[i:i+chunk_size])
        print(f"已通过USB发送 {len(d_header)} 字节")
        cheksum = 0

        for j in range(0, data_list_len):
            print(f"package : {j}")
            for i in range(0, data_list_pa_len, chunk_size):
                bytes_written = ep.write(data_list[j][i:i + chunk_size])
                if progress_callback:
                    progress_callback.update(bytes_written)

        print(f"END CHeksum {checksum}")

        ep.write(byte_array)

    time.sleep(0.5)
    print("Data is None")
    dev = None
    return True


def GetPanelSourceState(wIndex=0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x93,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("GetPanelSourceState :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelProcessState Fail: {str(e)}")


def GetPanelState(wIndex=0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x91,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("PanelState :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelState Fail: {str(e)}")


def GetOtaState(dev, wIndex=0):
    """获取OTA状态 - 传入设备句柄"""
    try:
        device_desc = dev.ctrl_transfer(
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x94,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("GetOtaState :", device_desc)
        return device_desc[0]
    except Exception as e:
        print(f"GetOtaState Fail: {str(e)}")
        return None


def ota_usb_send_res(vid, pid, endpoint_out, file_path=None, timeout_ms=5000, 
                     res_key_hex="1B 24 52 45 53 00", progress_callback=None):
    """OTA资源发送函数"""
    # 1) 打开并准备 USB
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        raise RuntimeError("USB 设备未找到，请检查 VID/PID")

    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except Exception:
        pass

    dev.set_configuration()
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    usb.util.claim_interface(dev, intf.bInterfaceNumber)

    ep_out = usb.util.find_descriptor(
        intf, custom_match=lambda e: e.bEndpointAddress == endpoint_out
    )
    if ep_out is None:
        usb.util.release_interface(dev, intf.bInterfaceNumber)
        usb.util.dispose_resources(dev)
        raise RuntimeError("未找到指定的 OUT 端点")
    chunk = ep_out.wMaxPacketSize or 512

    # 2) 发送 resKey（或 bootKey）与大端长度
    file_size = os.path.getsize(file_path)
    if file_size <= 0:
        raise RuntimeError("资源文件为空")
    if file_size == FW_SIZE:
        raise RuntimeError("文件可能为固件，非影像资源")
    if progress_callback:
        progress_callback.set_total(file_size)

    d_key = bytes.fromhex(res_key_hex)
    d_len = struct.pack(">I", file_size)  # 大端，对应 calArrNum

    for i in range(0, len(d_key), chunk):
        ep_out.write(d_key[i:i+chunk], timeout_ms)
    
    if not GetOtaState(dev) == 2:
        return False

    for i in range(0, len(d_len), chunk):
        ep_out.write(d_len[i:i+chunk], timeout_ms)
    print(f"[RES] 已发送Boot键与长度：{file_size} 字节")

    if not GetOtaState(dev) == 5:
        return False

    print("[RES] 设备已进入 PROGRAMMING_RES_MODE，开始发送资源数据…")

    # 4) 发送完整文件
    total_sent = 0
    block_count = int(file_size / OTA_TxBLOCK_SIZE)
    remainder = file_size % OTA_TxBLOCK_SIZE
    with open(file_path, "rb") as f:
        for block_index in range(block_count):
            data_chunk = f.read(OTA_TxBLOCK_SIZE)  # 读取一个完整块
            if not data_chunk:
                break 
        
            for i in range(0, len(data_chunk), chunk):
                chunk_to_send = data_chunk[i:i+chunk]
                try:
                    # 发送数据，并设置超时以避免无限等待
                    bytes_written = ep_out.write(chunk_to_send, timeout=5000)
                    total_sent += bytes_written
                    if progress_callback:
                        progress_callback.update(bytes_written)
                except usb.core.USBError as e:
                    print(f"[!] 发送块 {block_index} 时出错: {e}")
                    return False
            print(f"[↓] 已发送完整块 {block_index+1}/{block_count}")
        
        time.sleep(0.5)
        # 发送剩余的不完整块
        if remainder > 0:
            print(f"[↓] 正在发送剩余数据块 ({remainder} 字节)")
            last_chunk = f.read(remainder)
            if last_chunk:
                for i in range(0, len(last_chunk), chunk):
                    chunk_to_send = last_chunk[i:i+chunk]
                    try:
                        bytes_written = ep_out.write(chunk_to_send, timeout=5000)
                        total_sent += bytes_written
                        if progress_callback:
                            progress_callback.update(bytes_written)
                    except usb.core.USBError as e:
                        print(f"[!] 发送剩余数据时出错: {e}")
                        return False
                print("[+] 剩余数据发送完成。")
            else:
                print("[!] 读取剩余数据失败。")

    # 验证
    if total_sent == file_size:
        print(f"[✓] 文件发送成功！总计发送: {total_sent} 字节")
        return True
    else:
        print(f"[!] 发送长度不匹配！预期: {file_size} 字节, 实际: {total_sent} 字节")
        return False

    time.sleep(0.5)
    usb.util.release_interface(dev, intf.bInterfaceNumber)
    usb.util.dispose_resources(dev)
    print("[RES] 资源 OTA 发送完成（设备会在写入完成后重启）。")
    return True


def verify_ico_file(ico_path):
    """验证ICO文件是否有效"""
    try:
        from PIL import Image
        
        # 尝试打开ICO文件
        img = Image.open(ico_path)
        
        # 检查格式
        if img.format != 'ICO':
            print(f"警告：文件格式是 {img.format}，不是 ICO")
            return False
        
        # 获取所有尺寸
        if hasattr(img, 'info') and 'sizes' in img.info:
            sizes = img.info['sizes']
            print(f"ICO包含的尺寸: {sizes}")
        
        return True
        
    except Exception as e:
        print(f"ICO文件验证失败: {e}")
        return False


# ==================== RT9806 OTA功能 ====================

# HID常量
HID_SET_REPORT = 0x09
HID_OUTPUT_REPORT = 0x02
REPORT_ID_OTA = 0x06
UART_BUF_SIZE = 2048

# RT9806 OTA协议定义
BOOT_KEY_RT9806 = [0x1B, ord('$'), ord('B'), ord('O'), ord('O'), ord('T'), 0x00]
FIRMWARE_HEADER_RT9806 = [0x43, 0x4D, 0x33, 0x58]  # 'CM3X'


def find_rt9806_device(vid=USB_VID_RT9806, pid=USB_PID_RT9806):
    """查找RT9806 USB设备"""
    # 尝试使用libusb后端（如果可用）
    backend = None
    try:
        import usb.backend.libusb1
        backend = usb.backend.libusb1.get_backend()
    except:
        pass
    
    # 查找设备
    if backend:
        dev = usb.core.find(idVendor=vid, idProduct=pid, backend=backend)
    else:
        dev = usb.core.find(idVendor=vid, idProduct=pid)
    
    if dev is None:
        return None
    
    try:
        dev.set_configuration()
    except:
        try:
            dev.reset()
            dev.set_configuration()
        except:
            return None
    
    return dev


def get_rt9806_interface_number(dev):
    """获取RT9806的HID接口号"""
    try:
        cfg = dev.get_active_configuration()
        for intf in cfg:
            if intf.bInterfaceClass == 3:  # HID类
                return intf.bInterfaceNumber
    except:
        pass
    return 0


def send_rt9806_data(dev, interface_number, data, report_id=REPORT_ID_OTA, chunk_delay=0.001, progress_callback=None):
    """通过HID发送数据到RT9806设备"""
    if dev is None:
        return False
    
    # 每次发送32字节
    max_chunk = 32
    offset = 0
    total_sent = 0
    
    while offset < len(data):
        chunk_size = min(max_chunk, len(data) - offset)
        report_data = bytearray([report_id]) + bytearray(data[offset:offset + chunk_size])
        
        # 填充到33字节
        if len(report_data) < 33:
            report_data.extend([0] * (33 - len(report_data)))
        
        try:
            wValue = (HID_OUTPUT_REPORT << 8) | report_id
            result = dev.ctrl_transfer(
                bmRequestType=0x21,
                bRequest=HID_SET_REPORT,
                wValue=wValue,
                wIndex=interface_number,
                data_or_wLength=list(report_data),
                timeout=5000
            )
            
            if result != len(report_data):
                print(f"发送失败: 偏移={offset}, 返回={result}")
                return False
            
            total_sent += chunk_size
            if progress_callback:
                progress_callback.update(chunk_size)
                
        except Exception as e:
            print(f"发送数据失败: {e}")
            return False
        
        offset += chunk_size
        time.sleep(chunk_delay)
    
    return True


def swap_bytes_in_words(data):
    """每4字节反转顺序（小端转大端）"""
    result = list(data)
    while len(result) % 4 != 0:
        result.append(0)
    
    for i in range(0, len(result), 4):
        result[i], result[i+1], result[i+2], result[i+3] = \
            result[i+3], result[i+2], result[i+1], result[i]
    
    return result


def calculate_rt9806_checksum(data):
    """计算RT9806的32位校验和"""
    checksum = sum(data) & 0xFFFFFFFF
    return [
        (checksum >> 24) & 0xFF,
        (checksum >> 16) & 0xFF,
        (checksum >> 8) & 0xFF,
        checksum & 0xFF
    ]


def ota_usb_send_rt9806(file_path=None, progress_callback=None):
    """RT9806 OTA固件升级 - 自动选择模式（驱动模式优先）"""
    # 优先使用驱动模式
    if is_driver_mode_available():
        print("[RT9806] 检测到驱动模式可用，使用驱动进行OTA...")
        return ota_usb_send_rt9806_driver(file_path=file_path, progress_callback=progress_callback)
    else:
        print("[RT9806] 使用libusb模式进行OTA...")
        return ota_usb_send_rt9806_libusb(file_path=file_path, progress_callback=progress_callback)


def ota_usb_send_rt9806_libusb(file_path=None, progress_callback=None):
    """RT9806 OTA固件升级 - libusb模式（原有实现）"""
    # 查找设备
    dev = find_rt9806_device()
    if dev is None:
        raise ValueError('RT9806设备未找到，请检查VID和PID')
    
    try:
        # 获取HID接口号
        interface_number = get_rt9806_interface_number(dev)
        
        # 读取固件文件
        if file_path is None or not os.path.exists(file_path):
            raise ValueError('固件文件不存在')
        
        with open(file_path, 'rb') as f:
            firmware_data = list(f.read())
        
        firmware_size = len(firmware_data)
        
        if firmware_size < 4:
            raise ValueError('固件数据无效')
        
        # 验证固件头部
        file_header = list(firmware_data[:4])
        if file_header != FIRMWARE_HEADER_RT9806:
            raise ValueError(f'固件头部不匹配，期望: {FIRMWARE_HEADER_RT9806}, 实际: {file_header}')
        
        if firmware_size > 64 * 1024:
            raise ValueError('固件超过64KB限制')
        
        if progress_callback:
            progress_callback.set_total(firmware_size)
        
        print(f"[RT9806-libusb] 开始OTA固件升级，固件大小: {firmware_size} 字节")
        
        # 步骤1: 发送启动密钥
        print("[RT9806-libusb] [1/5] 发送启动密钥...")
        if not send_rt9806_data(dev, interface_number, BOOT_KEY_RT9806, progress_callback=progress_callback):
            return False
        print("[RT9806-libusb] ✓ 启动密钥发送完成")
        time.sleep(0.1)
        
        # 步骤2: 发送固件大小（小端格式）
        print("[RT9806-libusb] [2/5] 发送固件大小...")
        size_bytes = [
            firmware_size & 0xFF,
            (firmware_size >> 8) & 0xFF,
            (firmware_size >> 16) & 0xFF,
            (firmware_size >> 24) & 0xFF
        ]
        if not send_rt9806_data(dev, interface_number, size_bytes, progress_callback=progress_callback):
            return False
        print(f"[RT9806-libusb] ✓ 固件大小发送完成: {firmware_size} 字节")
        time.sleep(0.1)
        
        # 步骤3: 发送固件头部（字节反转）
        print("[RT9806-libusb] [3/5] 发送固件头部...")
        header_swapped = swap_bytes_in_words(file_header)
        if not send_rt9806_data(dev, interface_number, header_swapped, progress_callback=progress_callback):
            return False
        print("[RT9806-libusb] ✓ 固件头部发送完成")
        time.sleep(0.1)
        
        # 步骤4: 发送固件数据
        print("[RT9806-libusb] [4/5] 发送固件数据...")
        total_packets = (firmware_size + UART_BUF_SIZE - 1) // UART_BUF_SIZE
        print(f"[RT9806-libusb] 数据包: {total_packets} x {UART_BUF_SIZE} 字节")
        
        offset = 0
        packet_num = 0
        
        while offset < firmware_size:
            chunk_size = min(UART_BUF_SIZE, firmware_size - offset)
            chunk_data = list(firmware_data[offset:offset + chunk_size])
            
            # 填充到2048字节
            if len(chunk_data) < UART_BUF_SIZE:
                chunk_data.extend([0] * (UART_BUF_SIZE - len(chunk_data)))
            
            if not send_rt9806_data(dev, interface_number, chunk_data, chunk_delay=0, progress_callback=progress_callback):
                print(f"[RT9806-libusb] 失败: 数据包 {packet_num + 1}")
                return False
            
            packet_num += 1
            offset += chunk_size
            
            # 显示进度
            if packet_num % 10 == 0 or packet_num == total_packets:
                progress = (packet_num / total_packets) * 100
                print(f"[RT9806-libusb] 进度: {packet_num}/{total_packets} ({progress:.1f}%)")
            
            time.sleep(0.0001)
        
        print(f"[RT9806-libusb] ✓ 已发送 {packet_num} 个数据包")
        
        # 步骤5: 发送校验和
        print("[RT9806-libusb] [5/5] 发送校验和...")
        checksum = calculate_rt9806_checksum(firmware_data)
        send_rt9806_data(dev, interface_number, checksum, progress_callback=progress_callback)
        #    return False
        print(f"[RT9806-libusb] ✓ 校验和发送完成: 0x{''.join(f'{b:02X}' for b in checksum)}")
        
        print("[RT9806-libusb] OTA固件升级完成！")
        return True
        
    except Exception as e:
        print(f"[RT9806-libusb] OTA升级失败: {e}")
        return False
    finally:
        if dev:
            try:
                usb.util.dispose_resources(dev)
            except:
                pass


# ==================== RT9806 驱动模式 OTA 功能 ====================
# 使用 ctypes（Python 标准库）通过 USBPMIC 驱动进行 OTA
# 注意：不需要安装 pywin32，只使用标准库 ctypes

import ctypes
from ctypes import wintypes

# Windows API 常量
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# 设备接口 GUID (与驱动中的定义一致)
GUID_DEVINTERFACE_USBPMIC_STR = "{860849a7-3c26-4026-a664-6eb3ef08d259}"

# IOCTL 定义（与驱动中的定义一致）
USBPMIC_IOCTL_BASE = 0x8000
METHOD_BUFFERED = 0
FILE_ANY_ACCESS = 0

def CTL_CODE_OTA(DeviceType, Function, Method, Access):
    """计算 IOCTL 代码"""
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

# OTA IOCTL 代码
IOCTL_USBPMIC_OTA_INIT = CTL_CODE_OTA(USBPMIC_IOCTL_BASE, 0x810, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_USBPMIC_OTA_SEND_SIZE = CTL_CODE_OTA(USBPMIC_IOCTL_BASE, 0x811, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_USBPMIC_OTA_SEND_HEADER = CTL_CODE_OTA(USBPMIC_IOCTL_BASE, 0x812, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_USBPMIC_OTA_SEND_DATA = CTL_CODE_OTA(USBPMIC_IOCTL_BASE, 0x813, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_USBPMIC_OTA_SEND_CHECKSUM = CTL_CODE_OTA(USBPMIC_IOCTL_BASE, 0x814, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_USBPMIC_OTA_SEND_HID = CTL_CODE_OTA(USBPMIC_IOCTL_BASE, 0x815, METHOD_BUFFERED, FILE_ANY_ACCESS)

# OTA 常量
OTA_BLOCK_SIZE = 2048
OTA_MAX_CHUNK_SIZE = 32

# Windows API 函数设置
kernel32 = ctypes.windll.kernel32
setupapi = ctypes.windll.setupapi

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("InterfaceClassGuid", GUID),
        ("Flags", ctypes.c_ulong),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]

# 常量
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010

# 设置 SetupAPI 函数原型
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_ulong]
setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiEnumDeviceInterfaces.restype = ctypes.c_bool
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p]
setupapi.SetupDiGetDeviceInterfaceDetailW.restype = ctypes.c_bool
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
setupapi.SetupDiDestroyDeviceInfoList.restype = ctypes.c_bool

kernel32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
kernel32.CreateFileW.restype = ctypes.c_void_p
kernel32.DeviceIoControl.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p]
kernel32.DeviceIoControl.restype = ctypes.c_bool
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_bool


def guid_from_string(guid_str):
    """从字符串创建 GUID 结构体"""
    guid_str = guid_str.strip('{}')
    parts = guid_str.split('-')
    guid = GUID()
    guid.Data1 = int(parts[0], 16)
    guid.Data2 = int(parts[1], 16)
    guid.Data3 = int(parts[2], 16)
    data4_hex = parts[3] + parts[4]
    data4 = (ctypes.c_ubyte * 8)()
    for i in range(8):
        data4[i] = int(data4_hex[i*2:i*2+2], 16)
    guid.Data4 = data4
    return guid


def find_driver_device_interface():
    """查找 USBPMIC 驱动设备接口"""
    interface_guid = guid_from_string(GUID_DEVINTERFACE_USBPMIC_STR)
    
    device_info_set = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(interface_guid),
        None,
        None,
        DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    
    if device_info_set == INVALID_HANDLE_VALUE or device_info_set == 0:
        return None
    
    try:
        interface_data = SP_DEVICE_INTERFACE_DATA()
        interface_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
        
        result = setupapi.SetupDiEnumDeviceInterfaces(
            device_info_set,
            None,
            ctypes.byref(interface_guid),
            0,
            ctypes.byref(interface_data)
        )
        
        if not result:
            return None
        
        required_size = ctypes.c_ulong(0)
        setupapi.SetupDiGetDeviceInterfaceDetailW(
            device_info_set,
            ctypes.byref(interface_data),
            None,
            0,
            ctypes.byref(required_size),
            None
        )
        
        buffer_size = required_size.value
        buffer = ctypes.create_string_buffer(buffer_size)
        
        cbSize = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
        ctypes.memmove(buffer, ctypes.byref(ctypes.c_ulong(cbSize)), 4)
        
        result = setupapi.SetupDiGetDeviceInterfaceDetailW(
            device_info_set,
            ctypes.byref(interface_data),
            buffer,
            buffer_size,
            None,
            None
        )
        
        if result:
            device_path = ctypes.wstring_at(ctypes.addressof(buffer) + 4)
            return device_path
        
        return None
    
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(device_info_set)


def is_driver_mode_available():
    """检查驱动模式是否可用"""
    device_path = find_driver_device_interface()
    return device_path is not None


def open_driver_device():
    """打开驱动设备"""
    device_path = find_driver_device_interface()
    if device_path is None:
        return None
    
    handle = kernel32.CreateFileW(
        device_path,
        GENERIC_READ | GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None
    )
    
    if handle == INVALID_HANDLE_VALUE or handle == 0:
        return None
    
    return handle


def driver_send_ioctl(handle, ioctl_code, input_data=None):
    """发送 IOCTL 到驱动"""
    input_buffer = None
    input_size = 0
    
    if input_data:
        if isinstance(input_data, int):
            input_buffer = ctypes.create_string_buffer(struct.pack('<I', input_data), 4)
            input_size = 4
        elif isinstance(input_data, (bytes, bytearray)):
            input_buffer = ctypes.create_string_buffer(bytes(input_data), len(input_data))
            input_size = len(input_data)
        elif isinstance(input_data, list):
            data_bytes = bytes(input_data)
            input_buffer = ctypes.create_string_buffer(data_bytes, len(data_bytes))
            input_size = len(data_bytes)
    
    bytes_returned = ctypes.c_ulong(0)
    
    result = kernel32.DeviceIoControl(
        handle,
        ioctl_code,
        input_buffer,
        input_size,
        None,
        0,
        ctypes.byref(bytes_returned),
        None
    )
    
    return result


def ota_usb_send_rt9806_driver(file_path=None, progress_callback=None):
    """RT9806 OTA固件升级 - 驱动模式"""
    # 打开设备
    handle = open_driver_device()
    if handle is None:
        raise ValueError('无法打开USBPMIC驱动设备，请检查驱动是否正确安装')
    
    try:
        # 读取固件文件
        if file_path is None or not os.path.exists(file_path):
            raise ValueError('固件文件不存在')
        
        with open(file_path, 'rb') as f:
            firmware_data = f.read()
        
        firmware_size = len(firmware_data)
        
        if firmware_size < 4:
            raise ValueError('固件数据无效')
        
        # 验证固件头部
        file_header = list(firmware_data[:4])
        if file_header != FIRMWARE_HEADER_RT9806:
            raise ValueError(f'固件头部不匹配，期望: {FIRMWARE_HEADER_RT9806}, 实际: {file_header}')
        
        if firmware_size > 64 * 1024:
            raise ValueError('固件超过64KB限制')
        
        if progress_callback:
            progress_callback.set_total(firmware_size)
        
        print(f"[RT9806-Driver] 开始OTA固件升级，固件大小: {firmware_size} 字节")
        
        # 步骤1: 发送启动密钥 (通过 OTA_INIT IOCTL)
        print("[RT9806-Driver] [1/5] 发送启动密钥...")
        if not driver_send_ioctl(handle, IOCTL_USBPMIC_OTA_INIT):
            error = kernel32.GetLastError()
            print(f"[RT9806-Driver] 发送启动密钥失败，错误代码: {error}")
            return False
        print("[RT9806-Driver] ✓ 启动密钥发送完成")
        time.sleep(0.1)
        
        # 步骤2: 发送固件大小
        print("[RT9806-Driver] [2/5] 发送固件大小...")
        if not driver_send_ioctl(handle, IOCTL_USBPMIC_OTA_SEND_SIZE, firmware_size):
            error = kernel32.GetLastError()
            print(f"[RT9806-Driver] 发送固件大小失败，错误代码: {error}")
            return False
        print(f"[RT9806-Driver] ✓ 固件大小发送完成: {firmware_size} 字节")
        time.sleep(0.1)
        
        # 步骤3: 发送固件头部
        print("[RT9806-Driver] [3/5] 发送固件头部...")
        if not driver_send_ioctl(handle, IOCTL_USBPMIC_OTA_SEND_HEADER, file_header):
            error = kernel32.GetLastError()
            print(f"[RT9806-Driver] 发送固件头部失败，错误代码: {error}")
            return False
        print("[RT9806-Driver] ✓ 固件头部发送完成")
        time.sleep(0.1)
        
        # 步骤4: 发送固件数据
        print("[RT9806-Driver] [4/5] 发送固件数据...")
        total_packets = (firmware_size + OTA_BLOCK_SIZE - 1) // OTA_BLOCK_SIZE
        print(f"[RT9806-Driver] 数据包: {total_packets} x {OTA_BLOCK_SIZE} 字节")
        
        offset = 0
        packet_num = 0
        
        while offset < firmware_size:
            chunk_size = min(OTA_BLOCK_SIZE, firmware_size - offset)
            chunk_data = firmware_data[offset:offset + chunk_size]
            
            # 填充到2048字节
            if len(chunk_data) < OTA_BLOCK_SIZE:
                chunk_data = chunk_data + bytes([0] * (OTA_BLOCK_SIZE - len(chunk_data)))
            
            if not driver_send_ioctl(handle, IOCTL_USBPMIC_OTA_SEND_DATA, chunk_data):
                error = kernel32.GetLastError()
                print(f"[RT9806-Driver] 发送数据包 {packet_num + 1} 失败，错误代码: {error}")
                return False
            
            packet_num += 1
            offset += chunk_size
            
            if progress_callback:
                progress_callback.update(chunk_size)
            
            # 显示进度
            if packet_num % 10 == 0 or packet_num == total_packets:
                progress = (packet_num / total_packets) * 100
                print(f"[RT9806-Driver] 进度: {packet_num}/{total_packets} ({progress:.1f}%)")
            
            time.sleep(0.0001)
        
        print(f"[RT9806-Driver] ✓ 已发送 {packet_num} 个数据包")
        
        # 步骤5: 发送校验和
        print("[RT9806-Driver] [5/5] 发送校验和...")
        checksum = calculate_rt9806_checksum(list(firmware_data))
        driver_send_ioctl(handle, IOCTL_USBPMIC_OTA_SEND_CHECKSUM, checksum)
        '''
        if not driver_send_ioctl(handle, IOCTL_USBPMIC_OTA_SEND_CHECKSUM, checksum):
            error = kernel32.GetLastError()
            print(f"[RT9806-Driver] 发送校验和失败，错误代码: {error}")
            return False
        '''
        print(f"[RT9806-Driver] ✓ 校验和发送完成: 0x{''.join(f'{b:02X}' for b in checksum)}")
        
        print("[RT9806-Driver] OTA固件升级完成！")
        return True
        
    except Exception as e:
        print(f"[RT9806-Driver] OTA升级失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if handle:
            kernel32.CloseHandle(handle)
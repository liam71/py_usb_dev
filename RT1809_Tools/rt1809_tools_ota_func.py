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
    """RT9806 OTA固件升级"""
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
        
        print(f"[RT9806] 开始OTA固件升级，固件大小: {firmware_size} 字节")
        
        # 步骤1: 发送启动密钥
        print("[RT9806] [1/5] 发送启动密钥...")
        if not send_rt9806_data(dev, interface_number, BOOT_KEY_RT9806, progress_callback=progress_callback):
            return False
        print("[RT9806] ✓ 启动密钥发送完成")
        time.sleep(0.1)
        
        # 步骤2: 发送固件大小（小端格式）
        print("[RT9806] [2/5] 发送固件大小...")
        size_bytes = [
            firmware_size & 0xFF,
            (firmware_size >> 8) & 0xFF,
            (firmware_size >> 16) & 0xFF,
            (firmware_size >> 24) & 0xFF
        ]
        if not send_rt9806_data(dev, interface_number, size_bytes, progress_callback=progress_callback):
            return False
        print(f"[RT9806] ✓ 固件大小发送完成: {firmware_size} 字节")
        time.sleep(0.1)
        
        # 步骤3: 发送固件头部（字节反转）
        print("[RT9806] [3/5] 发送固件头部...")
        header_swapped = swap_bytes_in_words(file_header)
        if not send_rt9806_data(dev, interface_number, header_swapped, progress_callback=progress_callback):
            return False
        print("[RT9806] ✓ 固件头部发送完成")
        time.sleep(0.1)
        
        # 步骤4: 发送固件数据
        print("[RT9806] [4/5] 发送固件数据...")
        total_packets = (firmware_size + UART_BUF_SIZE - 1) // UART_BUF_SIZE
        print(f"[RT9806] 数据包: {total_packets} x {UART_BUF_SIZE} 字节")
        
        offset = 0
        packet_num = 0
        
        while offset < firmware_size:
            chunk_size = min(UART_BUF_SIZE, firmware_size - offset)
            chunk_data = list(firmware_data[offset:offset + chunk_size])
            
            # 填充到2048字节
            if len(chunk_data) < UART_BUF_SIZE:
                chunk_data.extend([0] * (UART_BUF_SIZE - len(chunk_data)))
            
            if not send_rt9806_data(dev, interface_number, chunk_data, chunk_delay=0, progress_callback=progress_callback):
                print(f"[RT9806] 失败: 数据包 {packet_num + 1}")
                return False
            
            packet_num += 1
            offset += chunk_size
            
            # 显示进度
            if packet_num % 10 == 0 or packet_num == total_packets:
                progress = (packet_num / total_packets) * 100
                print(f"[RT9806] 进度: {packet_num}/{total_packets} ({progress:.1f}%)")
            
            time.sleep(0.0001)
        
        print(f"[RT9806] ✓ 已发送 {packet_num} 个数据包")
        
        # 步骤5: 发送校验和
        print("[RT9806] [5/5] 发送校验和...")
        checksum = calculate_rt9806_checksum(firmware_data)
        send_rt9806_data(dev, interface_number, checksum, progress_callback=progress_callback)
        #    return False
        print(f"[RT9806] ✓ 校验和发送完成: 0x{''.join(f'{b:02X}' for b in checksum)}")
        
        print("[RT9806] OTA固件升级完成！")
        return True
        
    except Exception as e:
        print(f"[RT9806] OTA升级失败: {e}")
        return False
    finally:
        if dev:
            try:
                usb.util.dispose_resources(dev)
            except:
                pass
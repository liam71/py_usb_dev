import usb.core 
import usb.util
import numpy as np
import cv2
import time
import os
from example_run_dll import CryptoLib,ECPoint
from example_KeyPackage import KeyPackage
from typing import overload, Union
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

def get_control_transfer(mValue : int, dataLen : int):

    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=mValue,
            wIndex=0x0000,
            data_or_wLength=dataLen
        )
        print("res :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"獲取設備描述符失敗: {str(e)}")

def set_control_transfer(mValue : int , data : bytes):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0x40,
            bRequest=0x50,
            wValue=mValue,
            wIndex=0x0001,
            data_or_wLength=data
        )
        print("設備描述符:", device_desc)
    except Exception as e:
        print(f"獲取設備描述符失敗: {str(e)}")

# 使用示例
def example_control_transfer():
    # 示例1: 獲取設備描述符
    # bmRequestType = 0x80 (設備到主機, 標準請求, 設備)
    # bRequest = 0x06 (GET_DESCRIPTOR)
    # wValue = 0x0100 (設備描述符)
    # wIndex = 0x0000 (語言ID)
    # wLength = 18 (設備描述符長度)
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x0100,
            wIndex=0x0000,
            data_or_wLength=1
        )
        print("設備描述符:", device_desc)
    except Exception as e:
        print(f"獲取設備描述符失敗: {str(e)}")

    # 示例2: 發送自定義控制命令
    # bmRequestType = 0x40 (主機到設備, 廠商請求, 設備)
    # bRequest = 0x01 (自定義請求)
    # wValue = 0x0001 (自定義值)
    # wIndex = 0x0000 (自定義索引)
    data_to_send = b'\x01\x02\x03\x04'
    try:
        custom_cmd = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0x01,
            wValue=0x0001,
            wIndex=0x0000,
            data_or_wLength=4
        )
        print("自定義命令執行結果:", custom_cmd)
    except Exception as e:
        print(f"執行自定義命令失敗: {str(e)}")
    
    try:
        custom_cmd = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0x40,
            bRequest=0x01,
            wValue=0x0001,
            wIndex=0x0000,
            data_or_wLength=data_to_send
        )
        print("自定義命令執行結果:", custom_cmd)
    except Exception as e:
        print(f"執行自定義命令失敗: {str(e)}")

@overload
def CreatePackage(cmd : int, payload : int) ->bytes : ...
@overload
def CreatePackage(cmd : int, payload : list) ->bytes : ...

def CreatePackage(cmd : int, payload : Union[int, list]) ->bytes :
    payload_list = None
    if isinstance(payload, int):
        payload_list = list(payload.to_bytes(4, byteorder='big'))
    else:
        payload_list = payload
    pkg = KeyPackage(
    header=0x05,
    cmd=cmd,
    payload=payload_list,
    tail=0x2e
    )
    checksum = pkg.calculate_checksum()
    #print(f"Calculated checksum: 0x{checksum:02X}")

    raw_data = pkg.to_bytes_with_checksum()
    #print("封包 bytes:", raw_data.hex(' '))
    return raw_data

random_key = 0x4EF3920E

# 測試代碼
if __name__ == "__main__":
    #example_control_transfer()
    #get_control_transfer(0x02, 1)
    # get_control_transfer(0x03, 8)
    
    # package = CreatePackage(0x32, random_key)
    # CryptoLib.config_key_function(random_key)
    # set_control_transfer(0x01 , package)
    # start = "star"
    # ascii_list = [ord(c) for c in start]
    #print(ascii_list)  # [72, 101, 108, 108, 111]
    # ciphertext = CryptoLib.ecies_encrypt(ascii_list)
    # package = CreatePackage(0x11, ciphertext)
    # set_control_transfer(0x01 , package)
     get_control_transfer(0x81, 4)
    # set_control_transfer(0x05 , b'\x0a\x06')
    # set_control_transfer(0x01 , b'\x05\x11\x49\x37\x34\x35\x45\x2e')
    # set_control_transfer(0x02 , b'\x00')
    # set_control_transfer(0x03 , b'\x09\x08\x07\x07\x04\x00\x07\x03')
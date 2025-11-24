import os
import sys
os.environ['PATH'] = os.getcwd() + ';' + os.environ.get('PATH', '')
import usb.core 
import usb.util
import numpy as np
import cv2
import time
import struct
from model_dual import *
from example_run_dll import CryptoLib,ECPoint
from example_control import CreatePackage, random_key, set_control_transfer, get_control_transfer

DUALPANEL = 4
APP_model_ = DUALPANEL
IMAGE_PATH = "image/01.png"
imgdata = None
dev = None
cfg = None
ep = None
intf = None

def image_to_rgb565_bin(image_path, output_path):
    """
    将图像转换为RGB565格式并保存为BIN文件
    :param image_path: 输入图片路径
    :param output_path: 输出BIN文件路径
    """
    # 读取图像
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    
    # 转换为RGB格式
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 提取RGB分量
    r = rgb_img[:, :, 0]
    g = rgb_img[:, :, 1]
    b = rgb_img[:, :, 2]
    
    # 转换为RGB565格式
    # RGB565: R(5位) G(6位) B(5位)
    r_5bit = (r >> 3).astype(np.uint16)  # 取高5位
    g_6bit = (g >> 2).astype(np.uint16)  # 取高6位
    b_5bit = (b >> 3).astype(np.uint16)  # 取高5位
    
    # 组合为RGB565格式 (16位)
    rgb565 = (r_5bit << 11) | (g_6bit << 5) | b_5bit
    
    # 转换为大端序 (如果需要)
    rgb565_big_endian = rgb565.byteswap()
    
    # 保存为BIN文件
    with open(output_path, 'wb') as f:
        f.write(rgb565_big_endian.tobytes())
    
    print(f"已转换图像为RGB565格式并保存到: {output_path}")
    print(f"图像尺寸: {img.shape}, BIN文件大小: {os.path.getsize(output_path)} 字节")
    
    return rgb565_big_endian

def send_bin_over_usb(vid, pid, endpoint_out, bin_file_path):
    """
    将BIN文件通过USB发送
    :param vid: USB设备VID
    :param pid: USB设备PID
    :param endpoint_out: USB输出端点
    :param bin_file_path: BIN文件路径
    """
    global dev, ep
    
    # 检查BIN文件是否存在
    if not os.path.exists(bin_file_path):
        raise FileNotFoundError(f"BIN文件不存在: {bin_file_path}")
    
    # 查找USB设备
    if dev is None:
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise ValueError('设备未找到，请检查VID和PID')
        # 设置配置
        dev.set_configuration()
    
    # 获取端点
    if ep is None:
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]
        ep = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: e.bEndpointAddress == endpoint_out
        )
        if ep is None:
            raise ValueError('未找到指定的OUT端点')
    
    # 读取BIN文件
    with open(bin_file_path, 'rb') as f:
        bin_data = f.read()
    
    # 发送数据
    chunk_size = ep.wMaxPacketSize
    d_start = bytes.fromhex("FF 01")
    d_end = bytes.fromhex("FF 02")
    
    print(f"开始发送BIN数据，文件大小: {len(bin_data)} 字节")
    
    # 发送开始标记
    ep.write(d_start)
    
    # 分块发送数据
    total_sent = 0
    for i in range(0, len(bin_data), chunk_size):
        chunk = bin_data[i:i+chunk_size]
        ep.write(chunk)
        total_sent += len(chunk)
        
        # 显示进度
        if i % (chunk_size * 100) == 0:  # 每100个包显示一次进度
            progress = (i / len(bin_data)) * 100
            print(f"发送进度: {progress:.1f}%")
    
    # 发送结束标记
    ep.write(d_end)
    
    print(f"BIN数据发送完成，总共发送: {total_sent} 字节")
    
    # 清理资源
    usb.util.dispose_resources(dev)
    ep = None
    dev = None

def send_image_directly_over_usb(vid, pid, endpoint_out, image_path):
    """
    直接将图像转换为RGB565并通过USB发送（不保存为BIN文件）
    :param vid: USB设备VID
    :param pid: USB设备PID
    :param endpoint_out: USB输出端点
    :param image_path: 图像文件路径
    """
    global dev, ep
    
    # 读取并转换图像
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    
    # 转换为RGB格式
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 提取RGB分量并转换为RGB565
    r = rgb_img[:, :, 0]
    g = rgb_img[:, :, 1]
    b = rgb_img[:, :, 2]
    
    r_5bit = (r >> 3).astype(np.uint16)
    g_6bit = (g >> 2).astype(np.uint16)
    b_5bit = (b >> 3).astype(np.uint16)
    
    rgb565 = (r_5bit << 11) | (g_6bit << 5) | b_5bit
    rgb565_big_endian = rgb565.byteswap()
    bin_data = rgb565_big_endian.tobytes()
    
    # 查找USB设备
    if dev is None:
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise ValueError('设备未找到，请检查VID和PID')
        dev.set_configuration()
    
    # 获取端点
    if ep is None:
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]
        ep = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: e.bEndpointAddress == endpoint_out
        )
        if ep is None:
            raise ValueError('未找到指定的OUT端点')
    
    # 发送数据
    chunk_size = ep.wMaxPacketSize
    d_start = bytes.fromhex("FF 01")
    d_end = bytes.fromhex("FF 02")
    
    print(f"开始直接发送图像数据，大小: {len(bin_data)} 字节")
    
    # 发送开始标记
    ep.write(d_start)
    
    # 分块发送数据
    total_sent = 0
    for i in range(0, len(bin_data), chunk_size):
        chunk = bin_data[i:i+chunk_size]
        ep.write(chunk)
        total_sent += len(chunk)
    
    # 发送结束标记
    ep.write(d_end)
    
    print(f"图像数据发送完成，总共发送: {total_sent} 字节")
    
    # 清理资源
    usb.util.dispose_resources(dev)
    ep = None
    dev = None

# DUALPANEL模式主逻辑
if APP_model_ == DUALPANEL:
    # 流程:
    # 1. 检测面板状态
    # 2. 获取面板信息
    # 3. 配置加密密钥
    # 4. 发送开始命令
    # 5. 转换图像为BIN并发送
    # 6. 切换面板并重复
    
    index = 0
    max_retries = 10
        
    # 步骤1: 检测面板状态
    print("步骤1: 检测面板状态...")
    for i in range(1, max_retries + 1):
        if GetPanelSourceState() == 1 and GetPanelState(index) == 1:
            print(f"面板 {index} 已就绪")
            break
        time.sleep(0.5)
        if i == max_retries:
            print("错误: 无法检测到面板状态")
            sys.exit(1)
        
    # 步骤2: 设置选择面板并获取面板信息
    print("步骤2: 获取面板信息...")
    SetSelectPanel(index)
    
    panel_num = GetPanelNumber()
    panel_size = GetPanelSize(index)
    
    if panel_size is not None:
        height = panel_size[0] + (panel_size[1] * 256)  # 修正计算方式
        width = panel_size[2] + (panel_size[3] * 256)
        print(f"面板 {index} 信息:")
        print(f"  面板编号: {panel_num}")
        print(f"  分辨率: {width} x {height}")
    
    panel_direct = GetPanelDirect(index)
    panel_shape = GetPanelShape(index)
    
    # 步骤3: 配置加密密钥
    print("步骤3: 配置加密密钥...")
    package = CreatePackage(0x32, random_key)
    CryptoLib.config_key_function(random_key)
    SetCmdKeyAndCiphertext(package)
    
    # 步骤4: 发送开始命令
    print("步骤4: 发送开始命令...")
    start = "star"
    ascii_list = [ord(c) for c in start]
    ciphertext = CryptoLib.ecies_encrypt(ascii_list)
    package = CreatePackage(0x11, ciphertext)
    SetCmdKeyAndCiphertext(package)
    
    # 步骤5: 检查面板处理状态并发送图像数据
    print("步骤5: 检查面板处理状态...")
    GetPanelProcessState(index)
    
    for i in range(1, max_retries + 1):
        if GetPanelState(index) == 1:
            print("面板处理状态就绪，开始发送图像数据...")
            
            # 方法1: 先转换为BIN文件再发送
            bin_file_path = "temp_image.bin"
            try:
                # 将图像转换为BIN文件
                image_to_rgb565_bin(IMAGE_PATH, bin_file_path)
                
                # 发送BIN文件数据
                send_bin_over_usb(
                    vid=0x34C7, 
                    pid=0x8888, 
                    endpoint_out=0x02, 
                    bin_file_path=bin_file_path
                )
                
                # 可选: 清理临时文件
                # os.remove(bin_file_path)
                
            except Exception as e:
                print(f"BIN文件方式发送失败: {e}")
                print("尝试直接发送图像数据...")
                
                # 方法2: 直接发送图像数据（不保存为BIN文件）
                try:
                    send_image_directly_over_usb(
                        vid=0x34C7,
                        pid=0x8888,
                        endpoint_out=0x02,
                        image_path=IMAGE_PATH
                    )
                except Exception as e2:
                    print(f"直接发送图像数据也失败: {e2}")
                    break
            
            # 步骤6: 切换面板
            print("步骤6: 切换面板...")
            other_index = 0 if index == 1 else 1
            SetSelectPanel(other_index)
            
            # 检查另一个面板状态并发送
            if GetPanelState(other_index) == 1:
                print(f"面板 {other_index} 已就绪，开始发送数据...")
                
                try:
                    # 为另一个面板发送数据
                    send_image_directly_over_usb(
                        vid=0x34C7,
                        pid=0x8888,
                        endpoint_out=0x02,
                        image_path=IMAGE_PATH  # 可以使用不同的图像
                    )
                except Exception as e:
                    print(f"第二个面板发送失败: {e}")
            
            break
        else:
            print(f"等待面板处理状态... ({i}/{max_retries})")
            time.sleep(0.5)
    
    print("DUALPANEL模式执行完成")

    
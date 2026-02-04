import os
import sys
os.environ['PATH'] = os.getcwd() + ';' + os.environ.get('PATH', '')
import usb.core 
import usb.util
import numpy as np
import cv2
import time
from model_dual import *
from example_run_dll import CryptoLib
from example_control import CreatePackage, random_key

# ================== 模式定义 ==================
DISPLAY = 0
TOUCH = 1
APP_model_ = TOUCH

# ================== 全局变量 ==================
imgdata = None
dev = None
cfg = None
ep = None
intf = None
index = 0  # 面板索引

# ================== USB参数 ==================
USB_VID = 0x34C7
USB_PID = 0x8888
REPORT_ID_TP = 0xFA
# 接口定义（单接口设计，接口0同时支持触摸和显示）
INTERFACE_MAIN = 0        # 接口0: 同时支持触摸和显示 (Vendor Specific类，包含EP1 Bulk IN和EP2 Bulk OUT)
# 端点定义
EP_IN_BULK = 0x81        # EP1 IN - Bulk传输 (触摸数据，接口0)
EP_OUT_BULK = 0x02       # EP2 OUT - Bulk传输 (图像数据，接口0)

# ================== 手势码定义 ==================
GESTURE_NAMES = {
    0x00: "无手势",
    0x01: "上滑",
    0x02: "下滑",
    0x03: "左滑",
    0x04: "右滑",
    0x05: "单击",
    0x0B: "双击",
    0x0C: "长按",
}

# ================== 函数定义 ==================

def get_gesture_name(gesture_code):
    """获取手势名称"""
    return GESTURE_NAMES.get(gesture_code, f"未知(0x{gesture_code:02X})")

def parse_touch_data(data):
    """
    解析触摸数据
    
    数据格式:
        [0] Report ID (0xFA)
        [1] finger   - 手指数量 (0=抬起, 1=按下)
        [2] gesture  - 手势类型
        [3] X_H      - X坐标高字节
        [4] X_L      - X坐标低字节
        [5] Y_H      - Y坐标高字节
        [6] Y_L      - Y坐标低字节
        [7-11]       - 保留
    """
    if len(data) < 7:
        return None
    
    # 检查 Report ID
    report_id = data[0]
    if report_id != REPORT_ID_TP:
        return None
    
    finger = data[1]
    gesture = data[2]
    x = (data[3] << 8) | data[4]
    y = (data[5] << 8) | data[6]
    
    return {
        'report_id': report_id,
        'finger': finger,
        'gesture': gesture,
        'gesture_name': get_gesture_name(gesture),
        'x': x,
        'y': y
    }

def setup_touch_device():
    """
    配置触摸设备（使用接口0，该接口同时支持触摸和显示）
    
    Returns:
        device: USB设备对象 或 None（如果失败）
    """
    try:
        # 查找设备
        device = usb.core.find(idVendor=USB_VID, idProduct=USB_PID)
        if device is None:
            print(f"[错误] 未找到触摸设备 (VID=0x{USB_VID:04X}, PID=0x{USB_PID:04X})")
            return None
        
        print(f"[成功] 找到触摸设备")
        
        # Windows/Linux: 检查并分离内核驱动（接口0）
        try:
            if device.is_kernel_driver_active(INTERFACE_MAIN):
                print("[信息] 分离内核驱动（接口0）...")
                device.detach_kernel_driver(INTERFACE_MAIN)
        except (usb.core.USBError, NotImplementedError):
            pass  # Windows可能不支持此操作
        
        # 设置配置
        try:
            device.set_configuration()
            print("[成功] 设备配置完成")
        except usb.core.USBError as e:
            print(f"[警告] 设置配置失败: {e}")
        
        # 声明接口0（该接口同时支持触摸和显示）
        try:
            usb.util.claim_interface(device, INTERFACE_MAIN)
            print(f"[成功] 接口{INTERFACE_MAIN}（触摸和显示接口）已声明")
        except usb.core.USBError as e:
            print(f"[警告] 声明接口{INTERFACE_MAIN}失败: {e}")
        
        return device
        
    except Exception as e:
        print(f"[错误] 设备初始化失败: {e}")
        return None

def read_touch_data(device, timeout=100):
    """
    从Bulk IN端点读取触摸数据
    
    Args:
        device: USB设备对象
        timeout: 超时时间(ms)
    
    Returns:
        bytes或None
    """
    try:
        # 读取数据（Bulk传输，最大64字节，实际数据7字节）
        data = device.read(EP_IN_BULK, 64, timeout=timeout)
        data_bytes = bytes(data)
        
        # 验证数据长度（至少需要7字节：Report ID + 6字节数据）
        if len(data_bytes) < 7:
            return None
        
        return data_bytes
    except usb.core.USBTimeoutError:
        return None
    except usb.core.USBError as e:
        if "timeout" in str(e).lower():
            return None
        print(f"[错误] USB读取失败: {e}")
        return None

def cleanup_touch_device(device):
    """
    清理和释放触摸设备资源（接口0）
    """
    if device is not None:
        try:
            # 释放接口0
            usb.util.release_interface(device, INTERFACE_MAIN)
            print(f"[成功] 接口{INTERFACE_MAIN}（触摸和显示接口）已释放")
        except:
            pass
        # 释放设备资源
        usb.util.dispose_resources(device)
        print("[信息] 设备资源已释放")

def touch_data_receiver():
    """
    触摸数据接收主函数
    """
    print("=" * 60)
    print("      触摸数据接收模式")
    print("=" * 60)
    
    # 设置触摸设备
    touch_dev = setup_touch_device()
    if touch_dev is None:
        print("[错误] 无法初始化触摸设备，退出TOUCH模式")
        return
    
    print("\n开始接收触摸数据 (按 Ctrl+C 退出)")
    print("-" * 60)
    print(f"{'时间':<12} {'手指':<6} {'手势':<12} {'X':<8} {'Y':<8}")
    print("-" * 60)
    
    last_data = None
    touch_count = 0
    
    try:
        while True:
            # 从Bulk IN端点读取数据
            data = read_touch_data(touch_dev, timeout=100)
            
            if data:
                # 解析数据
                touch = parse_touch_data(data)
                
                if touch:
                    # 避免重复打印相同数据
                    current_data = (touch['finger'], touch['gesture'], touch['x'], touch['y'])
                    if current_data != last_data:
                        timestamp = time.strftime("%H:%M:%S")
                        finger_str = "按下" if touch['finger'] else "抬起"
                        print(f"{timestamp:<12} {finger_str:<6} {touch['gesture_name']:<12} {touch['x']:<8} {touch['y']:<8}")
                        
                        # 统计触摸事件
                        if touch['finger'] and touch['gesture'] != 0x00:
                            touch_count += 1
                            print(f"[统计] 第{touch_count}次有效触摸事件")
                        
                        last_data = current_data
            
            time.sleep(0.01)  # 10ms 轮询间隔
            
    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print(f"  用户中断，共检测到{touch_count}次有效触摸事件")
        print("  程序退出TOUCH模式")
        print("=" * 60)
    except Exception as e:
        print(f"[错误] 触摸数据接收异常: {e}")
    finally:
        # 清理设备资源
        cleanup_touch_device(touch_dev)

def save_image_rgb565_bin(image_path, output_path):
    """
    读取图片，转换为RGB565格式，并保存为bin文件。
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    rgb = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    r = (rgb[..., 0] >> 3).astype(np.uint16)
    g = (rgb[..., 1] >> 2).astype(np.uint16)
    b = (rgb[..., 2] >> 3).astype(np.uint16)
    rgb565 = (b << 8) | (g << 13) | (r << 3) | (g >> 3)
    rgb565 = rgb565.flatten()
    with open(output_path, 'wb') as f:
        f.write(rgb565.tobytes()) 

def send_bytes_over_usb(vid, pid, endpoint_out, directory_path):
    """
    读取指定目录下所有的bin文件并通过USB发送（使用接口0）
    """
    global dev, ep
    dev = None
    ep = None
    
    try:
        # 查找设备
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise ValueError('设备未找到，请检查VID和PID')
        
        # 设置配置（如果尚未设置）
        try:
            dev.set_configuration()
        except usb.core.USBError as e:
            # 如果配置已经设置，忽略此错误
            if "already" not in str(e).lower() and "busy" not in str(e).lower():
                raise
        
        # Windows/Linux: 检查并分离内核驱动（接口0）
        try:
            if dev.is_kernel_driver_active(INTERFACE_MAIN):
                print("[信息] 分离内核驱动（接口0）...")
                dev.detach_kernel_driver(INTERFACE_MAIN)
        except (usb.core.USBError, NotImplementedError):
            pass  # Windows可能不支持此操作
        
        # 声明接口0（该接口同时支持触摸和显示）
        try:
            usb.util.claim_interface(dev, INTERFACE_MAIN)
            print(f"[成功] 接口{INTERFACE_MAIN}（触摸和显示接口）已声明")
        except usb.core.USBError as e:
            print(f"[警告] 声明接口{INTERFACE_MAIN}失败: {e}")
            raise
        
        # 获取端点
        cfg = dev.get_active_configuration()
        # 使用接口0（触摸和显示接口）
        intf = cfg[(INTERFACE_MAIN, 0)]
        ep = usb.util.find_descriptor(
            intf,
            custom_match = lambda e: e.bEndpointAddress == endpoint_out
        )
        if ep is None:
            raise ValueError(f'未找到指定的 OUT 端点 (接口{INTERFACE_MAIN})')

        # 获取目录下所有的bin文件
        bin_files = [f for f in os.listdir(directory_path) if f.endswith('.bin')]
        if not bin_files:
            raise ValueError(f'在目录 {directory_path} 中没有找到.bin文件')

        chunk_size = ep.wMaxPacketSize
        d_start = bytes.fromhex("FF 01")
        d_end = bytes.fromhex("FF 02")

        # 发送所有bin文件
        for bin_file in bin_files:
            file_path = os.path.join(directory_path, bin_file)
            print(f"正在发送文件: {bin_file}")
            
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # 发送数据包：开始标记 + 数据 + 结束标记
                ep.write(d_start)
                for i in range(0, len(data), chunk_size):
                    ep.write(data[i:i+chunk_size])
                ep.write(d_end)
                print(f"已通过USB发送 {len(data)} 字节")
                time.sleep(0.5)
            except Exception as e:
                print(f"[错误] 发送文件 {bin_file} 失败: {e}")
                raise
    
    except Exception as e:
        print(f"[错误] USB发送过程出错: {e}")
        raise
    finally:
        # 确保释放接口和资源
        if dev is not None:
            try:
                # 释放接口0（触摸和显示接口）
                usb.util.release_interface(dev, INTERFACE_MAIN)
                print(f"[成功] 接口{INTERFACE_MAIN}（触摸和显示接口）已释放")
            except:
                pass
            
            try:
                # 释放设备资源
                usb.util.dispose_resources(dev)
            except:
                pass
        
        # 清理全局变量
        ep = None
        dev = None

# ================== 清理函数 ==================
def cleanup_all_usb_resources():
    """
    清理所有USB资源，确保设备处于干净状态
    用于模式切换前清理资源
    """
    try:
        # 查找设备
        dev = usb.core.find(idVendor=USB_VID, idProduct=USB_PID)
        if dev is not None:
            # 释放接口0（单接口设计）
            try:
                usb.util.release_interface(dev, INTERFACE_MAIN)
            except:
                pass
            
            # 释放设备资源
            try:
                usb.util.dispose_resources(dev)
            except:
                pass
            
            # 等待设备恢复
            time.sleep(0.5)
            print("[信息] USB资源已清理")
    except Exception as e:
        print(f"[警告] 清理USB资源时出错: {e}")

# ================== 初始化代码 ==================
# [ control trans ]
# 在初始化前清理可能的残留资源
cleanup_all_usb_resources()

# 等待设备就绪（增加错误处理）
print("等待设备就绪...")
device_ready = False
for i in range(1, 10):
    try:
        source_state = GetPanelSourceState()
        if source_state is not None and source_state >= 1:
            print("Device ready")
            device_ready = True
            break
    except Exception as e:
        print(f"尝试 {i}/9 失败: {e}")
        # 如果是Pipe error，增加延迟
        if "pipe" in str(e).lower() or "errno 32" in str(e).lower():
            time.sleep(1.0)  # Pipe error时增加延迟
        else:
            time.sleep(0.5)

if not device_ready:
    print("[警告] 设备未就绪，继续执行...")

# 获取面板信息（添加None检查）
panel_num = GetPanelNumber()
if panel_num is None:
    panel_num = 0
print(f"Panel count: {panel_num}")

index = 0
print(f"Using panel index: {index}")

SetSelectPanel(index)

panel_size = GetPanelSize(index)
if(panel_size is not None):
    height = (panel_size[0]) + (panel_size[1] * 256)
    width = (panel_size[2]) + (panel_size[3] * 256)
    print(f"Panel {index} size: {width}x{height}")
else:
    print(f"[警告] 无法获取面板 {index} 尺寸")

panel_direct = GetPanelDirect(index)
panel_shape = GetPanelShape(index)

# 配置加密
package = CreatePackage(0x32, random_key)
CryptoLib.config_key_function(random_key)
SetCmdKeyAndCiphertext(package)

start = "star"
ascii_list = [ord(c) for c in start]
ciphertext = CryptoLib.ecies_encrypt(ascii_list)
package = CreatePackage(0x11, ciphertext)
SetCmdKeyAndCiphertext(package)

# 获取处理状态并等待就绪
GetPanelProcessState(index)

for i in range(1, 10):
    panel_state = GetPanelState(index)
    if panel_state is not None and panel_state == 1:
        print(f"Panel {index} ready, state: {panel_state}")
        break
    time.sleep(0.5)

# ================== 模式执行 ==================
if APP_model_ == DISPLAY:
    # [ 接口0: Bulk传输 - 图像数据发送 ]
    print("=" * 60)
    print("进入DISPLAY模式 - 发送图像数据")
    print("=" * 60)
    print(f"使用接口{INTERFACE_MAIN}（触摸和显示接口）")
    print(f"图像端点: 0x{EP_OUT_BULK:02X} (OUT, Bulk)")
    print()
    print(f"Encryption verified, sending image to panel {index}...")
    save_image_rgb565_bin("image/SCN.png", "test1.bin")
    send_bytes_over_usb(vid=0x34C7, pid=0x8888, endpoint_out=0x02, directory_path=".")
    print("Image sent successfully!")
    
    # DISPLAY模式执行完成后，等待设备恢复，避免影响后续操作
    print("[信息] 等待设备恢复...")
    time.sleep(1.0)  # 给设备时间恢复状态

elif APP_model_ == TOUCH:
    # [ 接口0: Bulk传输 - 触摸数据接收 ]
    print("=" * 60)
    print("进入TOUCH模式 - 开始接收触摸数据")
    print("=" * 60)
    print(f"使用接口{INTERFACE_MAIN}（触摸和显示接口）")
    print(f"触摸端点: 0x{EP_IN_BULK:02X} (IN, Bulk)")
    print()
    
    # 启动触摸数据接收
    touch_data_receiver()
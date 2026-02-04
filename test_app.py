import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
os.environ['PATH'] = os.getcwd() + ';' + os.environ.get('PATH', '')
import usb.core 
import usb.util
import numpy as np
import cv2
import time
from model_dual import *
from example_run_dll import CryptoLib #GetPanelSize, GetPanelNumber, SetSelectPanel
from example_control import CreatePackage, random_key
from pathlib import Path
import threading
from PIL import Image, ImageTk

# ================== 同步锁 ==================
# 用于防止图片传输和触摸数据读取之间的冲突
# 
# 设备端实现细节（参考 usb_p.c）：
# - EP1 (0x81): Bulk IN 端点，用于发送触摸数据到PC
# - EP2 (0x02): Bulk OUT 端点，用于接收图片数据从PC
# - 这两个端点在硬件层面是互斥的：
#   * 接收图片时：禁用EP1，启用EP2（ServiceLoop函数）
#   * 发送触摸数据时：禁用EP2，启用EP1（USB_TP_Report函数）
# 
# PC端同步策略：
# - 图片传输期间持有锁，阻止触摸数据读取
# - 触摸数据读取时，如果锁被占用则跳过本次读取（非阻塞）
# - 这样可以确保图片传输不被触摸数据读取中断
image_transfer_lock = threading.Lock()  # 图片传输锁

# ================== USB参数 ==================
USB_VID = 0x34C7
USB_PID = 0x8888
REPORT_ID_TP = 0xFA
INTERFACE_MAIN = 0
EP_IN_BULK = 0x81
EP_OUT_BULK = 0x02

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

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif'}

# ================== 全局变量 ==================
dev = None
ep = None
current_image_index = 0
image_files = []
folder_path = ""
gesture_listener_thread = None
listening = False
touch_start_pos = None
touch_gestures = []  # 记录一次触摸过程中的所有手势
device_width = None  # 设备分辨率宽度
device_height = None  # 设备分辨率高度

# ================== 函数定义 ==================

def get_gesture_name(gesture_code):
    """获取手势名称"""
    return GESTURE_NAMES.get(gesture_code, f"未知(0x{gesture_code:02X})")

def parse_touch_data(data):
    """解析触摸数据"""
    if len(data) < 7:
        return None
    
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

def setup_usb_device():
    """设置USB设备"""
    global dev, ep
    try:
        dev = usb.core.find(idVendor=USB_VID, idProduct=USB_PID)
        if dev is None:
            return False, "未找到USB设备"
        
        try:
            dev.set_configuration()
        except usb.core.USBError as e:
            if "already" not in str(e).lower() and "busy" not in str(e).lower():
                return False, f"设置配置失败: {e}"
        
        try:
            if dev.is_kernel_driver_active(INTERFACE_MAIN):
                dev.detach_kernel_driver(INTERFACE_MAIN)
        except (usb.core.USBError, NotImplementedError):
            pass
        
        try:
            usb.util.claim_interface(dev, INTERFACE_MAIN)
        except usb.core.USBError as e:
            return False, f"声明接口失败: {e}"
        
        cfg = dev.get_active_configuration()
        intf = cfg[(INTERFACE_MAIN, 0)]
        ep = usb.util.find_descriptor(
            intf,
            custom_match = lambda e: e.bEndpointAddress == EP_OUT_BULK
        )
        if ep is None:
            return False, "未找到OUT端点"
        
        return True, "设备初始化成功"
    except Exception as e:
        return False, f"设备初始化失败: {e}"

def cleanup_usb_device():
    """清理USB设备"""
    global dev, ep
    if dev is not None:
        try:
            usb.util.release_interface(dev, INTERFACE_MAIN)
        except:
            pass
        try:
            usb.util.dispose_resources(dev)
        except:
            pass
    dev = None
    ep = None

def cleanup_all_usb_resources():
    """清理所有USB资源，确保设备处于干净状态"""
    try:
        dev = usb.core.find(idVendor=USB_VID, idProduct=USB_PID)
        if dev is not None:
            try:
                usb.util.release_interface(dev, INTERFACE_MAIN)
            except:
                pass
            try:
                usb.util.dispose_resources(dev)
            except:
                pass
            time.sleep(0.5)
    except Exception:
        pass

def convert_image_to_rgb565(image_path, target_width=None, target_height=None, status_callback=None):
    """将图片转换为RGB565格式的字节数据
    
    Args:
        image_path: 图片路径
        target_width: 目标宽度（如果为None则不缩放）
        target_height: 目标高度（如果为None则不缩放）
        status_callback: 状态回调函数
    
    Returns:
        RGB565格式的字节数据
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片: {image_path}")
    
    original_height, original_width = img.shape[:2]
    
    # 如果需要缩放且目标尺寸已指定
    if target_width is not None and target_height is not None:
        if original_width != target_width or original_height != target_height:
            if status_callback:
                status_callback(f"图片尺寸 {original_width}x{original_height} 不匹配设备 {target_width}x{target_height}，进行缩放...")
            # 使用高质量插值算法进行缩放
            img = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
    
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    r = (rgb[..., 0] >> 3).astype(np.uint16)
    g = (rgb[..., 1] >> 2).astype(np.uint16)
    b = (rgb[..., 2] >> 3).astype(np.uint16)
    rgb565 = (b << 8) | (g << 13) | (r << 3) | (g >> 3)
    rgb565 = rgb565.flatten()
    return rgb565.tobytes()

def send_image_to_device(image_path, status_callback=None, target_width=None, target_height=None):
    """发送图片到设备
    
    Args:
        image_path: 图片路径
        status_callback: 状态回调函数
        target_width: 目标分辨率宽度（如果为None则使用全局变量）
        target_height: 目标分辨率高度（如果为None则使用全局变量）
    
    注意：此函数使用锁来防止与触摸数据读取冲突，并在发送前等待触摸数据传输完成
    """
    global dev, ep, device_width, device_height
    
    if dev is None or ep is None:
        raise ValueError("USB设备未初始化")
    
    # 使用传入的分辨率或全局分辨率
    if target_width is None:
        target_width = device_width
    if target_height is None:
        target_height = device_height
    
    # 获取图片传输锁，防止触摸数据读取干扰
    # 设备端的EP1（触摸）和EP2（图片）是互斥的
    image_transfer_lock.acquire()
    try:
        # 关键改进：在发送图片前，清空触摸数据缓冲区并等待设备端完成触摸数据传输
        # 设备端ServiceLoop会主动检查并恢复EP2（如果EP1传输完成或超时3ms）
        # 注意：此操作在锁保护下进行，触摸数据读取线程已被阻塞，不会干扰
        
        # 等待一段时间，让设备端的ServiceLoop有机会恢复EP2
        # 如果EP1正在传输，这个等待时间可以让它完成；如果已完成，ServiceLoop会恢复EP2
        time.sleep(0.04)  # 40ms，足够ServiceLoop执行多次并检测EP1传输状态（3ms超时）
        
        # 快速清空触摸数据缓冲区（最多读取2次）
        for _ in range(2):
            try:
                # 尝试读取触摸数据（短超时，20ms）
                data = dev.read(EP_IN_BULK, 64, timeout=20)
                # 如果读取成功，说明有触摸数据，继续清空
            except (usb.core.USBTimeoutError, usb.core.USBError):
                # 超时，说明没有更多触摸数据了
                break
            except Exception:
                # 其他异常，忽略并继续
                break
        
        # 转换图片为RGB565格式（如果需要则进行缩放）
        image_data = convert_image_to_rgb565(image_path, target_width, target_height, status_callback)
        
        chunk_size = ep.wMaxPacketSize
        d_start = bytes.fromhex("FF 01")
        d_end = bytes.fromhex("FF 02")
        
        # 发送开始标记
        # 由于设备端ServiceLoop会主动检查并恢复EP2，需要等待一段时间
        # 但为了更可靠，使用重试机制：如果第一次失败，等待后重试
        max_retries = 5
        for retry in range(max_retries):
            try:
                # 尝试发送开始标记
                ep.write(d_start, timeout=500)  # 500ms超时
                break
            except (usb.core.USBTimeoutError, usb.core.USBError) as e:
                if retry < max_retries - 1:
                    # 重试前等待，让设备端ServiceLoop有机会恢复EP2
                    wait_time = 0.05 * (retry + 1)  # 递增等待时间：50ms, 100ms, 150ms...
                    time.sleep(wait_time)
                    if status_callback:
                        status_callback(f"等待EP2恢复... ({retry + 1}/{max_retries})")
                else:
                    # 最后一次重试失败，抛出异常
                    if status_callback:
                        status_callback(f"发送开始标记失败: EP2可能仍被禁用")
                    raise
        
        if status_callback:
            status_callback(f"发送图片: {os.path.basename(image_path)} ({len(image_data)} 字节)")
        
        # 发送图片数据
        for i in range(0, len(image_data), chunk_size):
            ep.write(image_data[i:i+chunk_size])
        
        # 发送结束标记
        ep.write(d_end)
        
        if status_callback:
            status_callback(f"图片发送完成: {os.path.basename(image_path)}")
        
        return True
    except Exception as e:
        if status_callback:
            status_callback(f"发送图片失败: {e}")
        raise
    finally:
        # 确保锁被释放，即使发生异常
        image_transfer_lock.release()

def read_touch_data(timeout=100):
    """读取触摸数据
    
    注意：如果图片传输正在进行中，此函数会立即返回None，避免端点冲突
    设备端的EP1（触摸）和EP2（图片）是互斥的，不能同时使用
    
    此函数使用非阻塞方式检查锁，如果图片传输正在进行则跳过读取
    """
    global dev
    
    if dev is None:
        return None
    
    # 检查图片传输锁，如果被占用则跳过这次读取
    # 使用非阻塞方式检查锁，避免阻塞触摸数据读取线程
    lock_acquired = image_transfer_lock.acquire(blocking=False)
    if not lock_acquired:
        # 锁被占用，说明正在传输图片，跳过这次读取以避免端点冲突
        return None
    
    try:
        # 锁可用，进行读取（持有锁的时间尽可能短）
        data = dev.read(EP_IN_BULK, 64, timeout=timeout)
        data_bytes = bytes(data)
        if len(data_bytes) < 7:
            return None
        return parse_touch_data(data_bytes)
    except usb.core.USBTimeoutError:
        return None
    except usb.core.USBError as e:
        if "timeout" in str(e).lower():
            return None
        return None
    except Exception:
        return None
    finally:
        # 确保释放锁
        if lock_acquired:
            image_transfer_lock.release()

def is_valid_swipe_gesture(start_pos, end_pos, device_gesture=None):
    """验证滑动手势是否有效
    
    Args:
        start_pos: 触摸起始位置 {'x': int, 'y': int}
        end_pos: 触摸结束位置 {'x': int, 'y': int}
        device_gesture: 设备返回的手势值（可选），0x01=上滑, 0x02=下滑
    
    Returns:
        (is_valid, gesture_code): 是否有效，手势代码（0x01=上滑, 0x02=下滑）
    """
    # 检查位置数据
    if not start_pos or not end_pos:
        return False, None
    
    # 计算按下到抬起的距离
    dx = end_pos['x'] - start_pos['x']
    dy = end_pos['y'] - start_pos['y']
    abs_dx = abs(dx)
    abs_dy = abs(dy)
    distance = int((abs_dx**2 + abs_dy**2)**0.5)
    
    # 距离必须>50像素
    if distance <= 50:
        return False, None
    
    # 基于坐标变化判断方向
    # 如果垂直移动距离大于水平移动距离，则是垂直滑动
    coordinate_gesture = None
    if abs_dy > abs_dx:
        if dy < 0:  # Y坐标减小，向上滑动
            coordinate_gesture = 0x01  # GESTURE_SWIPE_UP
        else:  # Y坐标增大，向下滑动
            coordinate_gesture = 0x02  # GESTURE_SWIPE_DOWN
    else:
        # 水平滑动，不处理
        return False, None
    
    # 如果提供了设备手势值，需要验证是否与坐标判断一致
    if device_gesture is not None:
        # 设备手势值：0x01=上滑, 0x02=下滑
        if device_gesture == coordinate_gesture:
            # 坐标判断和设备手势值一致，手势有效
            return True, coordinate_gesture
        else:
            # 坐标判断和设备手势值不一致，手势无效
            return False, None
    else:
        # 没有设备手势值，仅基于坐标判断
        return True, coordinate_gesture

# ================== GUI应用类 ==================

class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片浏览器 - USB触摸控制")
        self.root.geometry("750x750")
        
        # 变量
        self.image_files = []
        self.current_index = 0
        self.folder_path = ""
        
        # 创建界面
        self.create_widgets()
        
        # 注意：USB设备初始化将在main()函数配置加密后再进行
    
    def create_widgets(self):
        # 文件夹选择区域
        folder_frame = ttk.Frame(self.root, padding="10")
        folder_frame.pack(fill=tk.X)
        
        ttk.Button(folder_frame, text="选择图片文件夹", command=self.select_folder).pack(side=tk.LEFT, padx=5)
        self.folder_label = ttk.Label(folder_frame, text="未选择文件夹", foreground="gray")
        self.folder_label.pack(side=tk.LEFT, padx=10)
        
        # 图片信息区域
        info_frame = ttk.Frame(self.root, padding="10")
        info_frame.pack(fill=tk.X)
        
        self.info_label = ttk.Label(info_frame, text="当前图片: 无", font=("Arial", 12))
        self.info_label.pack()
        
        self.count_label = ttk.Label(info_frame, text="图片总数: 0")
        self.count_label.pack()
        
        # 图片预览区域
        preview_frame = ttk.Frame(self.root, padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(preview_frame, text="图片预览:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # 创建三个预览画布的容器
        preview_container = ttk.Frame(preview_frame)
        preview_container.pack(pady=5)
        
        # 预览画布尺寸（每个预览图）
        preview_width = 200
        preview_height = 150
        
        # 上一张预览
        prev_frame = ttk.Frame(preview_container)
        prev_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(prev_frame, text="上一张", font=("Arial", 9)).pack()
        self.prev_preview_canvas = tk.Canvas(prev_frame, width=preview_width, height=preview_height, 
                                             bg="lightgray", relief=tk.SUNKEN, borderwidth=1)
        self.prev_preview_canvas.pack(pady=2)
        self.prev_preview_label = ttk.Label(prev_frame, text="无", foreground="gray", font=("Arial", 8))
        self.prev_preview_label.pack()
        self.prev_preview_image = None
        
        # 当前预览（突出显示）
        current_frame = ttk.Frame(preview_container)
        current_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(current_frame, text="当前", font=("Arial", 9, "bold"), foreground="blue").pack()
        self.preview_canvas = tk.Canvas(current_frame, width=preview_width, height=preview_height, 
                                        bg="lightblue", relief=tk.RAISED, borderwidth=3)
        self.preview_canvas.pack(pady=2)
        self.preview_label = ttk.Label(current_frame, text="暂无图片", foreground="gray", font=("Arial", 8))
        self.preview_label.pack()
        self.current_preview_image = None
        
        # 下一张预览
        next_frame = ttk.Frame(preview_container)
        next_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(next_frame, text="下一张", font=("Arial", 9)).pack()
        self.next_preview_canvas = tk.Canvas(next_frame, width=preview_width, height=preview_height, 
                                             bg="lightgray", relief=tk.SUNKEN, borderwidth=1)
        self.next_preview_canvas.pack(pady=2)
        self.next_preview_label = ttk.Label(next_frame, text="无", foreground="gray", font=("Arial", 8))
        self.next_preview_label.pack()
        self.next_preview_image = None
        
        # 控制按钮区域
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="发送当前图片", command=self.send_current_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="上一张", command=self.previous_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="下一张", command=self.next_image).pack(side=tk.LEFT, padx=5)
        
        # 状态区域（调整高度）
        status_frame = ttk.Frame(self.root, padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(status_frame, text="状态信息:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.status_text = tk.Text(status_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.config(yscrollcommand=scrollbar.set)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 手势监听控制
        gesture_frame = ttk.Frame(self.root, padding="10")
        gesture_frame.pack(fill=tk.X)
        
        self.listen_button = ttk.Button(gesture_frame, text="开始手势监听", command=self.toggle_gesture_listening)
        self.listen_button.pack(side=tk.LEFT, padx=5)
        
        self.gesture_status_label = ttk.Label(gesture_frame, text="手势监听: 未启动", foreground="gray")
        self.gesture_status_label.pack(side=tk.LEFT, padx=10)
    
    def log_status(self, message):
        """添加状态信息"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update()
    
    def select_folder(self):
        """选择图片文件夹"""
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder:
            self.folder_path = folder
            image_files_set = set()  # 使用set避免重复
            
            # 查找所有图片文件（使用set去重，因为Windows文件系统不区分大小写）
            for ext in IMAGE_EXTENSIONS:
                image_files_set.update(Path(folder).glob(f"*{ext}"))
                image_files_set.update(Path(folder).glob(f"*{ext.upper()}"))
            
            # 按文件名排序并转换为字符串列表
            self.image_files = sorted([str(f) for f in image_files_set])
            
            if self.image_files:
                self.current_index = 0
                self.folder_label.config(text=f"已选择: {os.path.basename(folder)} ({len(self.image_files)} 张图片)")
                self.update_image_info()
                self.log_status(f"找到 {len(self.image_files)} 张图片")
            else:
                self.folder_label.config(text="未找到图片文件")
                messagebox.showwarning("警告", "选择的文件夹中没有找到图片文件")
    
    def update_image_info(self):
        """更新图片信息显示"""
        if self.image_files:
            current_file = os.path.basename(self.image_files[self.current_index])
            self.info_label.config(text=f"当前图片 ({self.current_index + 1}/{len(self.image_files)}): {current_file}")
            self.count_label.config(text=f"图片总数: {len(self.image_files)}")
            # 更新图片预览
            self.update_image_preview()
        else:
            self.info_label.config(text="当前图片: 无")
            self.count_label.config(text="图片总数: 0")
            self.clear_image_preview()
    
    def update_image_preview(self):
        """更新图片预览（上一张、当前、下一张）"""
        if not self.image_files:
            self.clear_image_preview()
            return
        
        # 更新当前图片预览
        self.update_single_preview(self.current_index, self.preview_canvas, self.preview_label, 
                                   "current_preview_image", is_current=True, is_prev=False, is_next=False)
        
        # 更新上一张图片预览（向左倾斜）
        if len(self.image_files) > 1:
            prev_index = (self.current_index - 1) % len(self.image_files)
            self.update_single_preview(prev_index, self.prev_preview_canvas, self.prev_preview_label, 
                                      "prev_preview_image", is_current=False, is_prev=True, is_next=False)
        else:
            self.clear_single_preview(self.prev_preview_canvas, self.prev_preview_label, "prev_preview_image")
        
        # 更新下一张图片预览（向右倾斜）
        if len(self.image_files) > 1:
            next_index = (self.current_index + 1) % len(self.image_files)
            self.update_single_preview(next_index, self.next_preview_canvas, self.next_preview_label, 
                                      "next_preview_image", is_current=False, is_prev=False, is_next=True)
        else:
            self.clear_single_preview(self.next_preview_canvas, self.next_preview_label, "next_preview_image")
    
    def update_single_preview(self, index, canvas, label, attr_name, is_current=True, is_prev=False, is_next=False):
        """更新单个预览图"""
        try:
            image_path = self.image_files[index]
            
            # 使用PIL加载图片
            pil_image = Image.open(image_path)
            
            # 转换为RGB（如果需要）
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 获取画布大小
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # 如果画布还没有大小，使用默认大小
            if canvas_width <= 1:
                canvas_width = 200
            if canvas_height <= 1:
                canvas_height = 150
            
            # 计算缩放比例，保持纵横比
            img_width, img_height = pil_image.size
            scale_w = canvas_width / img_width
            scale_h = canvas_height / img_height
            scale = min(scale_w, scale_h, 1.0)  # 不放大，只缩小
            
            # 缩放图片
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 所有图片都正常显示，不做3D变换
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # 清除画布
            canvas.delete("all")
            
            # 计算居中位置
            final_width, final_height = pil_image.size
            x = (canvas_width - final_width) // 2
            y = (canvas_height - final_height) // 2
            
            # 在画布上显示图片
            canvas.create_image(x, y, anchor=tk.NW, image=photo)
            
            # 保存引用（防止垃圾回收）
            setattr(self, attr_name, photo)
            
            # 更新标签
            filename = os.path.basename(image_path)
            if is_current:
                label.config(text=f"{filename}\n({img_width}x{img_height})")
            else:
                label.config(text=f"{filename}")
            
        except Exception as e:
            self.clear_single_preview(canvas, label, attr_name)
            label.config(text=f"预览失败")
    
    def clear_single_preview(self, canvas, label, attr_name):
        """清除单个预览图"""
        canvas.delete("all")
        setattr(self, attr_name, None)
        label.config(text="无")
    
    def clear_image_preview(self):
        """清除所有图片预览"""
        self.clear_single_preview(self.preview_canvas, self.preview_label, "current_preview_image")
        self.clear_single_preview(self.prev_preview_canvas, self.prev_preview_label, "prev_preview_image")
        self.clear_single_preview(self.next_preview_canvas, self.next_preview_label, "next_preview_image")
    
    def previous_image(self):
        """上一张图片"""
        if self.image_files:
            self.current_index = (self.current_index - 1) % len(self.image_files)
            self.update_image_info()
            self.log_status(f"切换到上一张: {os.path.basename(self.image_files[self.current_index])}")
    
    def next_image(self):
        """下一张图片"""
        if self.image_files:
            self.current_index = (self.current_index + 1) % len(self.image_files)
            self.update_image_info()
            self.log_status(f"切换到下一张: {os.path.basename(self.image_files[self.current_index])}")
    
    def send_current_image(self):
        """发送当前图片到设备"""
        if not self.image_files:
            messagebox.showwarning("警告", "请先选择包含图片的文件夹")
            return
        
        if dev is None or ep is None:
            messagebox.showerror("错误", "USB设备未连接或未初始化")
            return
        
        try:
            image_path = self.image_files[self.current_index]
            send_image_to_device(image_path, self.log_status)
        except Exception as e:
            messagebox.showerror("错误", f"发送图片失败: {e}")
            self.log_status(f"发送图片失败: {e}")
    
    def init_usb_device(self):
        """初始化USB设备（分辨率已在main()函数中获取）"""
        global device_width, device_height
        
        success, message = setup_usb_device()
        if success:
            self.log_status("USB设备初始化成功")
            if device_width is not None and device_height is not None:
                self.log_status(f"设备分辨率: {device_width}x{device_height}")
            else:
                self.log_status("[警告] 设备分辨率未获取，将使用原始图片尺寸")
        else:
            self.log_status(f"USB设备初始化失败: {message}")
            messagebox.showwarning("警告", f"USB设备初始化失败: {message}\n请检查设备连接")
    
    def toggle_gesture_listening(self):
        """切换手势监听状态"""
        global listening
        
        if not listening:
            if not self.image_files:
                messagebox.showwarning("警告", "请先选择包含图片的文件夹")
                return
            
            if dev is None or ep is None:
                messagebox.showerror("错误", "USB设备未连接或未初始化")
                return
            
            # 启动手势监听
            listening = True
            self.listen_button.config(text="停止手势监听")
            self.gesture_status_label.config(text="手势监听: 运行中", foreground="green")
            self.log_status("开始手势监听...")
            
            # 发送第一张图片
            try:
                self.current_index = 0
                self.update_image_info()
                send_image_to_device(self.image_files[self.current_index], self.log_status)
                time.sleep(0.5)  # 等待图片发送完成
            except Exception as e:
                self.log_status(f"发送第一张图片失败: {e}")
            
            # 启动手势监听线程
            self.gesture_thread = threading.Thread(target=self.gesture_listener_loop, daemon=True)
            self.gesture_thread.start()
        else:
            # 停止手势监听
            listening = False
            self.listen_button.config(text="开始手势监听")
            self.gesture_status_label.config(text="手势监听: 已停止", foreground="gray")
            self.log_status("手势监听已停止")
    
    def gesture_listener_loop(self):
        """手势监听循环（在单独线程中运行）"""
        global listening, touch_start_pos
        
        touch_start_pos = None
        
        self.root.after(0, self.log_status, "等待触摸手势（上滑/下滑）...")
        
        while listening:
            try:
                touch_data = read_touch_data(timeout=100)
                
                if touch_data:
                    finger = touch_data['finger']
                    x = touch_data['x']
                    y = touch_data['y']
                    
                    # 手指按下，记录起始位置
                    if finger == 1 and touch_start_pos is None:
                        touch_start_pos = {'x': x, 'y': y}
                        self.root.after(0, self.log_status, f"触摸按下: ({x}, {y})")
                    
                    # 手指抬起，验证手势（需要坐标判断和设备手势值都符合）
                    elif finger == 0 and touch_start_pos is not None:
                        touch_end_pos = {'x': x, 'y': y}
                        device_gesture = touch_data.get('gesture', None)  # 获取设备返回的手势值
                        
                        # 验证手势有效性（坐标判断 + 设备手势值验证）
                        is_valid, valid_gesture = is_valid_swipe_gesture(
                            touch_start_pos, touch_end_pos, device_gesture
                        )
                        
                        if is_valid:
                            # 手势有效，坐标判断和设备手势值都符合，切换图片
                            gesture_name = "上滑" if valid_gesture == 0x01 else "下滑"
                            distance = int(((touch_end_pos['x']-touch_start_pos['x'])**2 + (touch_end_pos['y']-touch_start_pos['y'])**2)**0.5)
                            self.root.after(0, self.log_status, 
                                f"检测到有效手势: {gesture_name} (距离: {distance}像素, 设备手势: 0x{device_gesture:02X})")
                            
                            if valid_gesture == 0x01:  # 上滑
                                self.root.after(0, self.handle_swipe_up)
                            elif valid_gesture == 0x02:  # 下滑
                                self.root.after(0, self.handle_swipe_down)
                        else:
                            # 手势无效（距离不足50像素、主要是水平移动、或坐标判断与设备手势值不一致）
                            distance = int(((touch_end_pos['x']-touch_start_pos['x'])**2 + (touch_end_pos['y']-touch_start_pos['y'])**2)**0.5)
                            if device_gesture is not None:
                                self.root.after(0, self.log_status, 
                                    f"手势无效（距离: {distance}像素, 设备手势: 0x{device_gesture:02X}, 坐标判断与设备手势不一致或距离不足）")
                            else:
                                self.root.after(0, self.log_status, 
                                    f"手势无效（距离: {distance}像素，需要>50像素且主要是垂直移动）")
                        
                        # 重置触摸状态
                        touch_start_pos = None
                
                time.sleep(0.01)  # 10ms轮询间隔
                
            except Exception as e:
                if listening:
                    self.root.after(0, self.log_status, f"手势监听错误: {e}")
                time.sleep(0.1)
    
    def handle_swipe_up(self):
        """处理上滑手势"""
        if not self.image_files:
            return
        
        self.log_status("检测到有效的上滑手势 -> 切换到上一张")
        self.previous_image()
        
        try:
            # send_image_to_device内部已经包含了等待触摸数据传输完成的逻辑
            send_image_to_device(self.image_files[self.current_index], self.log_status)
            time.sleep(0.3)  # 等待图片发送完成（减少等待时间，因为内部已有保护）
            self.log_status("等待下一个手势...")
        except Exception as e:
            self.log_status(f"发送图片失败: {e}")
    
    def handle_swipe_down(self):
        """处理下滑手势"""
        if not self.image_files:
            return
        
        self.log_status("检测到有效的下滑手势 -> 切换到下一张")
        self.next_image()
        
        try:
            # send_image_to_device内部已经包含了等待触摸数据传输完成的逻辑
            send_image_to_device(self.image_files[self.current_index], self.log_status)
            time.sleep(0.3)  # 等待图片发送完成（减少等待时间，因为内部已有保护）
            self.log_status("等待下一个手势...")
        except Exception as e:
            self.log_status(f"发送图片失败: {e}")

# ================== 主程序 ==================

def main():
    # 初始化加密相关（如果需要）
    try:
        cleanup_all_usb_resources()
        time.sleep(0.5)
        
        # 辅助函数：统一获取返回值的第一个元素（兼容 int 和 array）
        def get_value(result, index=0):
            if result is None:
                return None
            if isinstance(result, int):
                return result
            try:
                return result[index]
            except (TypeError, IndexError):
                return result
        
        # 等待设备就绪（参考main.py的DUALPANEL模式）
        # GetPanelSourceState 返回值: 0=logo, 1=background, 2=usb
        # 返回值 > 0 表示设备已初始化
        for i in range(1, 10):
            try:
                source_state = GetPanelSourceState()
                state_val = get_value(source_state)
                if state_val is not None and state_val > 0:
                    print(f"Device ready, source state: {state_val}")
                    break
            except Exception as e:
                if "pipe" in str(e).lower() or "errno 32" in str(e).lower():
                    time.sleep(1.0)
                else:
                    time.sleep(0.5)
        
        # 获取屏幕数量，决定使用的索引（参考main.py的DUALPANEL模式）
        panel_num = GetPanelNumber()
        num_panels = get_value(panel_num) if panel_num is not None else 1
        print(f"Panel count: {num_panels}")
        
        # 重要：索引从 0 开始，单屏时只有 index=0 有效
        # 单屏模式: index=0, 双屏模式: index=0 或 1
        if num_panels == 1:
            index = 0  # 单屏模式，必须用 index 0
        else:
            index = 0  # 双屏模式，使用 index 0
        print(f"Using panel index: {index}")
        
        # 选择屏幕
        SetSelectPanel(index)
        
        # 获取当前屏幕尺寸（在加密配置之前获取，这是关键！）
        panel_size = GetPanelSize(index)
        if panel_size is not None:
            # 16位小端序: h = [0]+[1]*256, w = [2]+[3]*256
            height = get_value(panel_size, 0) + (get_value(panel_size, 1) * 256)
            width = get_value(panel_size, 2) + (get_value(panel_size, 3) * 256)
            print(f"Panel {index} size: {width}x{height}")
            # 保存到全局变量
            global device_width, device_height
            device_width = width
            device_height = height
        else:
            print(f"[警告] 无法获取面板 {index} 尺寸")
            device_width = None
            device_height = None
        
        # 配置加密密钥（在获取分辨率之后）
        package = CreatePackage(0x32, random_key)
        CryptoLib.config_key_function(random_key)
        SetCmdKeyAndCiphertext(package)
        
        # 发送启动命令
        start = "star"
        ascii_list = [ord(c) for c in start]
        ciphertext = CryptoLib.ecies_encrypt(ascii_list)
        package = CreatePackage(0x11, ciphertext)
        SetCmdKeyAndCiphertext(package)
        
        # 检查处理状态 (ProcessState == 1 表示加密验证通过)
        process_state = GetPanelProcessState(index)
        process_val = get_value(process_state)
        print(f"Process state (encryption verify): {process_val}")
        
        # 等待面板状态就绪
        for i in range(1, 10):
            try:
                panel_state = GetPanelState(index)
                state_val = get_value(panel_state)
                if state_val == 1:
                    break
            except Exception as e:
                pass
            time.sleep(0.5)
    except Exception as e:
        print(f"初始化警告: {e}")
    
    # 创建GUI应用
    root = tk.Tk()
    app = ImageViewerApp(root)
    
    # 在加密配置完成后，初始化USB设备并获取分辨率
    app.init_usb_device()
    
    # 设置关闭事件处理
    def on_closing():
        global listening
        listening = False
        cleanup_usb_device()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 运行GUI
    root.mainloop()

if __name__ == "__main__":
    main()


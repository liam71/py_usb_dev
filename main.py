import usb.core 
import usb.util
import numpy as np
import cv2
import time
import os
import struct
import tkinter as tk
from model_dual import *
from tkinter import messagebox, ttk, filedialog
from PIL import Image, ImageTk
from example_run_dll import CryptoLib,ECPoint
from example_control import CreatePackage, random_key, set_control_transfer, get_control_transfer
AUO = 0
WIDGET = 1
NOTIKINTER = 2
OTA = 3
DUALPANEL = 4
APP_model_ = DUALPANEL#NOTIKINTER
imgdata = None
dev = None
cfg = None
ep = None
intf = None
isPUM = False
isModel = None
def save_image_as_bytes(image_path, output_path, format='.png'):
    """
    读取图片并以字节格式保存到文件。
    :param image_path: 输入图片路径
    :param output_path: 输出字节文件路径
    :param format: 图片编码格式，默认'.png'
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    success, buffer = cv2.imencode(format, img)
    if not success:
        raise ValueError("图片编码失败")
    with open(output_path, 'wb') as f:
        f.write(buffer.tobytes()) 

def save_image_rgb_bytes(image_path, output_path):
    """
    读取图片并将其RGB原始数据保存为二进制文件。
    :param image_path: 输入图片路径
    :param output_path: 输出字节文件路径
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with open(output_path, 'wb') as f:
        f.write(rgb_img.tobytes()) 

def save_image_rgb565_bin(image_path, output_path):
    """
    读取图片，转换为RGB565格式，并保存为bin文件。
    :param image_path: 输入图片路径
    :param output_path: 输出bin文件路径
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")
    rgb = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    r = (rgb[..., 0] >> 3).astype(np.uint16)
    g = (rgb[..., 1] >> 2).astype(np.uint16)
    b = (rgb[..., 2] >> 3).astype(np.uint16)
    # r
    rgb565 = (b << 8) | (g << 13) | (r << 3) | (g >> 3)
    rgb565 = rgb565.flatten()
    with open(output_path, 'wb') as f:
        f.write(rgb565.tobytes()) 

def get_state(dev):
    result = 0
    try:
        # 執行 Control Transfer
        result = dev.ctrl_transfer(
            bmRequestType=0xC0,
            bRequest=0x01,
            wValue=0x100,
            wIndex=0x0000,
            data_or_wLength=1,
            timeout=10
        )

        return result[0]
    except usb.core.USBError as e:
        print(f"USB Control Transfer 錯誤: {str(e)}")
        raise
    return result

def send_bytes_over_usb(vid, pid, endpoint_out, directory_path):
    """
    读取指定目录下所有的bin文件并通过USB发送
    :param vid: USB设备VID
    :param pid: USB设备PID
    :param endpoint_out: USB输出端点
    :param directory_path: 包含bin文件的目录路径
    """
    global dev , ep
    # 查找 USB 设备
    if(dev is None):
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise ValueError('设备未找到，请检查VID和PID')
        # 设置配置
        dev.set_configuration()
    # 获取端点
    if(ep is None):
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]
        ep = usb.util.find_descriptor(
            intf,
            custom_match = lambda e: e.bEndpointAddress == endpoint_out
        )
        if ep is None:
            raise ValueError('未找到指定的 OUT 端点')

    # 获取目录下所有的bin文件
    bin_files = [f for f in os.listdir(directory_path) if f.endswith('.bin')]
    if not bin_files:
        raise ValueError(f'在目录 {directory_path} 中没有找到.bin文件')

    # 发送数据
    chunk_size = ep.wMaxPacketSize
    d_start = bytes.fromhex("FF 01")
    d_clear = bytes.fromhex("FF 04")
    d_end = bytes.fromhex("FF 02")

    ep.write(d_clear)
    for bin_file in bin_files:
        file_path = os.path.join(directory_path, bin_file)
        print(f"正在发送文件: {bin_file}")
        
        # 读取文件数据
        with open(file_path, 'rb') as f:
            data = f.read()
        data_len = len(data)
        data_count = 0
        # 发送数据
        #ep.write(d_clear)
        ep.write(d_start)
        indexss = 100
        data_array = None        
        for i in range(0, len(data), chunk_size):
            ep.write(data[i:i+chunk_size])
        ep.write(d_end)
        print(f"已通过USB发送 {len(data)} 字节")
        
        # 可选：在文件之间添加短暂延迟
        time.sleep(0.5)
    usb.util.dispose_resources(dev)
    ep = None
    dev = None
    
    


def crcCalculate(crc : bytearray):
    pass

def openDeviceIS(vid, pid):
    pass

def edit2textProcess(dataLinst):
    text = dataLinst.split()
    text = [int(x) for x in text]
    data_one = list()
    data_two = list()
    if(len(text) != 4):
        return False, data_one, data_two
        
    if(((text[0] + text[2] ) < 1920 ) and ((text[1] + text[3]) < 1080)):
        data_one.append(text[0] >> 4)
        data_one.append(((text[0] & 0xf) << 4) | (text[1] >> 8))
        data_one.append(text[1] & 0xff)
        data_one.append(text[2] >> 4)
        data_two.append(((text[2] & 0xf) << 4) | (text[3] >> 8))
        data_two.append(text[3] & 0xff);
        data_two.append(0x00)
        data_two.append(0x00)
        return True , data_one, data_two
    return False, data_one, data_two

def send_USB_data(vid, pid, endpoint_out,mode:str, data = None):
    global dev, cfg, ep, intf
    if dev is None:
        print("dev is none")
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if dev is None:
            raise ValueError('设备未找到，请检查VID和PID')
        dev.set_configuration()
    
    # 设置配置
    #dev.set_configuration()

    # 获取端点
    if cfg is None:
        cfg = dev.get_active_configuration()
    if intf is None:
        intf = cfg[(0,0)]
    if ep is None:
        ep = usb.util.find_descriptor(
            intf,
            custom_match = lambda e: e.bEndpointAddress == endpoint_out
        )

    if ep is None:
        raise ValueError('未找到指定的 OUT 端点')

    # 发送数据
    chunk_size = ep.wMaxPacketSize
    d_start = bytes.fromhex("FF 01")
    d_clear = bytes.fromhex("FF 04")
    d_end = bytes.fromhex("FF 02")
    
    d_m0 = bytes.fromhex("FF 04 00 fd")
    d_m1 = bytes.fromhex("FF 04 01 fc")
    d_m2 = bytes.fromhex("FF 04 02 fb")
    d_m3 = bytes.fromhex("FF 04 03 fa")
    d_m4 = bytes.fromhex("FF 04 04 f9")
    
    if mode == "M0":
        ep.write(d_m0)
    elif mode == "M1":
        ep.write(d_m1)
    elif mode == "M2":
        ep.write(data)
    elif mode == "M3":
        ep.write(d_m3)
    elif mode == "M4":        
        ep.write(data)
    
    print(type(d_m2))

    #dev = None

def button_click(button_name):
    global isPUM, isModel
    """更新輸入欄位為當前按鈕名稱"""

    if button_name == "M2" or button_name == "M4":
        entry_var.set("輸入更新區域")
        if button_name == "M2":
            isModel = "M2"
        else:
            isModel = "M4"
        isPUM = True
    elif button_name is "確認":
        print("C")
    if button_name == "M0":
        print("M0")
        send_USB_data(vid=0x34C7, pid=0x8888, endpoint_out= 0x02 ,mode= "M0")
    elif button_name == "M1":
        print("M1")
        send_USB_data(vid=0x34C7, pid=0x8888, endpoint_out= 0x02 ,mode= "M1")
    elif button_name == "M3":
        print("M3")
        send_USB_data(vid=0x34C7, pid=0x8888, endpoint_out= 0x02 ,mode= "M3")

def process_text():
    global isPUM,isModel
    if isPUM == False:
        return
    """獲取輸入欄位文字並進行處理"""
    input_text = entry.get().strip()  # 獲取並清除前後空白


    if not input_text:
        messagebox.showinfo("訊息", "輸入欄位為空！")
        return

    state, data_one, data_two = edit2textProcess(input_text)
    if state == False:
        return
    send_data = None
    if isModel == "M2":
        send_data = bytearray([255, 4, 2, 251])
    elif isModel == "M4":
        send_data = bytearray("FF 04 02 f9")
    send_data.extend(data_one)
    send_data.extend(data_two)
    final = bytes(send_data)
    send_USB_data(vid=0x34C7, pid=0x8888, endpoint_out= 0x02 ,mode= isModel, data= final)
    #if state == True:
    # 這可以添加任何自定義處理邏輯
    # processed_text = f"處理結果: {input_text.upper()} (長度: {len(input_text)})"
    # # 顯示處理結果
    # messagebox.showinfo("處理完成", processed_text)
    # 清空輸入欄位（可選）

class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("圖片處理工具")
        self.root.geometry("800x600")
        
        # 初始化變量
        self.image_path = None
        self.palette_index = 0
        self.palettes = ["RGB", "灰度", "暖色", "冷色", "自定義"]
        self.modes = ["標準模式", "編輯模式", "預覽模式", "分析模式"]
        
        # 創建 UI 框架
        self.create_widgets()
    
    def create_widgets(self):
        # 頂部控制面板
        control_frame = ttk.LabelFrame(self.root, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 按鈕
        ttk.Button(control_frame, text="選擇圖片", command=self.select_image).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="選擇目錄", command=self.select_directory).grid(row=0, column=1, padx=5, pady=5)
        
        # 調色盤切換
        ttk.Label(control_frame, text="調色盤:").grid(row=0, column=2, padx=(20, 5))
        self.palette_combo = ttk.Combobox(control_frame, values=self.palettes, state="readonly", width=10)
        self.palette_combo.grid(row=0, column=3, padx=5)
        self.palette_combo.current(0)
        self.palette_combo.bind("<<ComboboxSelected>>", self.change_palette)
        
        # 模式選擇
        ttk.Label(control_frame, text="模式:").grid(row=0, column=4, padx=(20, 5))
        self.mode_combo = ttk.Combobox(control_frame, values=self.modes, state="readonly", width=12)
        self.mode_combo.grid(row=0, column=5, padx=5)
        self.mode_combo.current(0)
        
        # 顯示區域
        display_frame = ttk.LabelFrame(self.root, text="圖片顯示", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 圖片畫布
        self.canvas = tk.Canvas(display_frame, bg="#f0f0f0", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 狀態欄
        self.status = ttk.Label(self.root, text="就緒", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, padx=10, pady=5)
    
    def select_image(self):
        filetypes = (
            ("圖片文件", "*.jpg *.jpeg *.png *.bmp *.gif"),
            ("所有文件", "*.*")
        )
        path = filedialog.askopenfilename(title="選擇圖片", filetypes=filetypes)
        if path:
            self.image_path = path
            self.display_image()
            self.status.config(text=f"已選擇圖片: {os.path.basename(path)}")
    
    def select_directory(self):
        path = filedialog.askdirectory(title="選擇目錄")
        if path:
            self.status.config(text=f"已選擇目錄: {path}")
    
    def display_image(self):
        if not self.image_path:
            return
            
        try:
            # 清除畫布
            self.canvas.delete("all")
            
            # 載入圖片
            img = Image.open(self.image_path)
            
            # 調整圖片大小以適應畫布
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img.thumbnail((canvas_width - 20, canvas_height - 20))
            
            # 應用調色盤
            palette = self.palette_combo.get()
            if palette == "灰度":
                img = img.convert("L")
            elif palette == "暖色":
                img = self.apply_warm_filter(img)
            elif palette == "冷色":
                img = self.apply_cool_filter(img)
            
            # 顯示圖片
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.create_image(
                canvas_width // 2, 
                canvas_height // 2, 
                anchor=tk.CENTER, 
                image=self.tk_img
            )
            
            # 顯示文件名
            self.canvas.create_text(
                10, 10, 
                anchor=tk.NW, 
                text=os.path.basename(self.image_path),
                fill="white",
                font=("Arial", 10, "bold"),
                stroke_width=2,
                stroke_fill="black"
            )
            
        except Exception as e:
            self.status.config(text=f"錯誤: {str(e)}")
    
    def change_palette(self, event=None):
        if self.image_path:
            self.display_image()
            self.status.config(text=f"已切換調色盤: {self.palette_combo.get()}")
    
    def apply_warm_filter(self, img):
        # 簡單的暖色過濾器示例
        r, g, b = img.split()
        r = r.point(lambda i: min(i + 30, 255))
        return Image.merge("RGB", (r, g, b))
    
    def apply_cool_filter(self, img):
        # 簡單的冷色過濾器示例
        r, g, b = img.split()
        b = b.point(lambda i: min(i + 30, 255))
        return Image.merge("RGB", (r, g, b))
    
    def run(self):
        # 定期檢查畫布大小變化
        self.check_canvas_size()
        self.root.mainloop()
    
    def check_canvas_size(self):
        if self.image_path:
            # 如果畫布大小改變，重新顯示圖片
            current_width = self.canvas.winfo_width()
            current_height = self.canvas.winfo_height()
            
            if (current_width > 1 and current_height > 1 and 
                (current_width != self.last_canvas_width or 
                 current_height != self.last_canvas_height)):
                self.display_image()
        
        self.last_canvas_width = self.canvas.winfo_width()
        self.last_canvas_height = self.canvas.winfo_height()
        self.root.after(500, self.check_canvas_size)

def ota_usb_send(vid, pid, endpoint_out, file_path = None):
    # 查找 USB 设备
    cheksum = 0
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        raise ValueError('设备未找到，请检查VID和PID')

    # 设置配置
    dev.set_configuration()

    # 获取端点
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]
    ep = usb.util.find_descriptor(
        intf,
        custom_match = lambda e: e.bEndpointAddress == endpoint_out
    )
    if ep is None:
        raise ValueError('未找到指定的 OUT 端点')

    # 发送数据
    chunk_size = ep.wMaxPacketSize
    d_key = bytes.fromhex("1B 24 42 4f 4f 54 00")
    d_lens = bytes.fromhex("00 01 00 00")
    #d_header = bytes.fromhex("43 4D 33 58")
    
    for i in range(0, len(d_key), chunk_size):
        ep.write(d_key[i:i+chunk_size])
    print(f"已通过USB发送 {len(d_key)} 字节")

    for i in range(0, len(d_lens), chunk_size):
        ep.write(d_lens[i:i+chunk_size])
    print(f"已通过USB发送 {len(d_lens)} 字节")

    if file_path is not None and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        data_list = []
        data_list_len = int(file_size / 2048)
        data_list_pa_len = 2048
        with open(file_path, "rb") as f:
            for i in range(0 , data_list_len):
                data_list.append(f.read(data_list_pa_len))
        d_header = data_list[0][0:4] 
        print(f"data list len : {data_list_len} data list pa len : {data_list_pa_len}")
        checksum = 0
        checksum_list = []
        count = 0;
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
                ep.write(data_list[j][i:i + chunk_size])
            #time.sleep(0.5)

        print(f"END CHeksum {checksum}")

                

        ep.write(byte_array)

    time.sleep(0.5)
    print("Data is None")
    dev = None

if APP_model_ == AUO:
    # 創建主視窗
    root = tk.Tk()
    root.title("按鈕功能示範")
    root.geometry("400x300")
    # 輸入欄位變數
    entry_var = tk.StringVar()
    # 創建輸入欄位
    entry = tk.Entry(root, textvariable=entry_var, font=('Arial', 14), width=30, justify='center')
    entry.pack(pady=20)
    # 按鈕框架 (放置6個功能按鈕)
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    # 按鈕名稱列表
    button_names = [
        "M0", "M1", "M2",
        "M3", "M4", "無功能"
    ]
    # 創建6個功能按鈕 (2行3列)
    for i, name in enumerate(button_names):
        row = i // 3  # 計算行位置 (0或1)
        col = i % 3   # 計算列位置 (0,1或2)
        btn = tk.Button(
            button_frame,
            text=name,
            width=10,
            height=2,
            command=lambda n=name: button_click(n)  # 綁定按鈕名稱
        )
        btn.grid(row=row, column=col, padx=5, pady=5)
    # 創建確認按鈕
    confirm_btn = tk.Button(
        root,
        text="ENTER",
        width=15,
        height=2,
        command=process_text # 綁定按鈕名稱
    )
    confirm_btn.pack(pady=15)
    # 運行主循環
    root.mainloop()
elif APP_model_ == WIDGET:
    root = tk.Tk()
    app = ImageViewerApp(root)
    app.run()
elif APP_model_ == NOTIKINTER:
    for i in range(1, 10):
        if(GetPanelSourceState() == 1):
            if(GetPanelState() == 1):
                break
        time.sleep(0.5)
    package = CreatePackage(0x32, random_key)
    print("Config pp Key")
    CryptoLib.config_key_function(random_key)
    set_control_transfer(0x01 , package)
    start = "star" # [115, 116, 97, 114]
    ascii_list = [ord(c) for c in start]
    ciphertext = CryptoLib.ecies_encrypt(ascii_list)
    package = CreatePackage(0x11, ciphertext)
    print("SEND Message") 
    set_control_transfer(0x01 , package)
    save_image_rgb565_bin("image/three.png", "test1.bin")
    send_bytes_over_usb(vid=0x34C7, pid=0x8888, endpoint_out=0x02, directory_path=".")

elif APP_model_ == OTA:
    for i in range(1, 10):
        if(GetPanelSourceState() == 1):
            if(GetPanelState() == 1):
                break
        time.sleep(0.5)
    package = CreatePackage(0x32, random_key)
    print("Config pp Key")
    CryptoLib.config_key_function(random_key)
    set_control_transfer(0x01 , package)
    start = "star" # [115, 116, 97, 114]
    ascii_list = [ord(c) for c in start]
    ciphertext = CryptoLib.ecies_encrypt(ascii_list)
    package = CreatePackage(0x11, ciphertext)
    print("SEND Message") 
    set_control_transfer(0x01 , package)
    otar = "otaR" 
    ascii_list = [ord(c) for c in otar]
    ciphertext = CryptoLib.ecies_encrypt(ascii_list)
    package = CreatePackage(0x11, ciphertext)
    print("SEND Message") 
    set_control_transfer(0x01 , package)
    ota_usb_send(vid=0x34C7, pid=0x8888, endpoint_out=0x02, file_path="1809_bin/GPCM2_CM3_strip_Trans_b.bin")

elif APP_model_ == DUALPANEL:
    # Flow
    # Step 1 GetPanelNumber
    # Step 2 GetPanelSize
    # Step 3 GetPanelDirect
    # Step 4 GetPanelShape
    # Step 5 SelectPanel
    # Step 6 SendStartCmd
    # Step 7 SendData
    # Step 8 SendEndCmd
    index = 1
    for i in range(1, 10):
        if(GetPanelSourceState() == 1):
            if(GetPanelState(index) == 1):
                break
        time.sleep(0.5)
    panel_num = GetPanelNumber()
    panel_size = GetPanelSize(index)
    if(panel_size is not None):
        print(f"高 : ",(panel_size[0]) + (panel_size[1] * 16 * 16))
        print(f"寬 : ",(panel_size[2]) + (panel_size[3] * 16 * 16))
    panel_direct = GetPanelDirect(index)
    panel_shape = GetPanelShape(index)
    package = CreatePackage(0x32, random_key)
    CryptoLib.config_key_function(random_key)
    SetCmdKeyAndCiphertext(package)
    start = "star"
    ascii_list = [ord(c) for c in start]
    ciphertext = CryptoLib.ecies_encrypt(ascii_list)
    package = CreatePackage(0x11, ciphertext)
    SetCmdKeyAndCiphertext(package)
    GetPanelProcessState(index)
    for i in range(1,10):
        if (GetPanelState(index) == 1):
            save_image_rgb565_bin("image/SCN.png", "test1.bin")
            send_bytes_over_usb(vid=0x34C7, pid=0x8888, endpoint_out=0x02, directory_path=".")
            SetSelectPanel(0 if index == 1 else 1) 
            if(GetPanelState(index) == 1):
                send_bytes_over_usb(vid=0x34C7, pid=0x8888, endpoint_out=0x02, directory_path=".")
            break
    

    
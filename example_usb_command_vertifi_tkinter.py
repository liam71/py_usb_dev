import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import usb.core
import usb.util
import threading
import time
import re
from array import array
class USBControlTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB Control Transfer 测试工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设备变量
        self.devices = []
        self.selected_device = None
        
        # 创建界面
        self.create_widgets()
        
        # 初始加载设备
        self.refresh_devices()
        
        # 设置主题
        self.set_theme()
        
        # 设置图标
        try:
            self.root.iconbitmap("usb_icon.ico")
        except:
            pass

    def set_theme(self):
        # 设置颜色主题
        self.root.configure(bg="#f0f0f0")
        style = ttk.Style()
        style.theme_use("clam")
        
        # 配置样式
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10), padding=5)
        style.configure("TCombobox", padding=5)
        style.configure("TEntry", padding=5)
        style.map("TButton", background=[('active', '#d9d9d9')])
        
        # 标题样式
        style.configure("Title.TLabel", font=("Arial", 14, "bold"), foreground="#2c3e50")

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(main_frame, text="USB Control Transfer 测试工具", style="Title.TLabel")
        title_label.pack(pady=(0, 15))
        
        # 设备选择区域
        device_frame = ttk.LabelFrame(main_frame, text="USB 设备选择")
        device_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(device_frame, text="选择设备:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.device_combo = ttk.Combobox(device_frame, state="readonly", width=70)
        self.device_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        refresh_btn = ttk.Button(device_frame, text="刷新设备列表", command=self.refresh_devices)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # 设备信息区域
        info_frame = ttk.LabelFrame(main_frame, text="设备信息")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.device_info = scrolledtext.ScrolledText(info_frame, height=6, font=("Consolas", 9))
        self.device_info.pack(fill=tk.X, padx=5, pady=5)
        self.device_info.insert(tk.END, "请从上方选择USB设备...")
        self.device_info.config(state=tk.DISABLED)
        
        # 控制传输参数区域
        params_frame = ttk.LabelFrame(main_frame, text="控制传输参数")
        params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建参数输入字段
        params = [
            ("bmRequestType", "请求类型 (十六进制):", "0x80"),
            ("bRequest", "请求代码 (十六进制):", "0x06"),
            ("wValue", "值 (十六进制):", "0x0100"),
            ("wIndex", "索引 (十六进制):", "0x0000"),
            ("wLength", "数据长度 (十进制):", "64"),
            ("timeout", "超时时间 (ms):", "1000")
        ]
        
        self.param_entries = {}
        for i, (name, label, default) in enumerate(params):
            ttk.Label(params_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky=tk.W)
            entry = ttk.Entry(params_frame, width=20)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
            entry.insert(0, default)
            self.param_entries[name] = entry
        
        # 数据传输方向
        ttk.Label(params_frame, text="数据传输方向:").grid(row=0, column=2, padx=20, pady=5, sticky=tk.W)
        self.direction_var = tk.StringVar(value="IN")
        ttk.Radiobutton(params_frame, text="设备到主机 (IN)", variable=self.direction_var, value="IN").grid(
            row=0, column=3, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(params_frame, text="主机到设备 (OUT)", variable=self.direction_var, value="OUT").grid(
            row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        # 数据输入区域
        data_frame = ttk.LabelFrame(main_frame, text="传输数据 (十六进制)")
        data_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.data_entry = scrolledtext.ScrolledText(data_frame, height=4, font=("Consolas", 9))
        self.data_entry.pack(fill=tk.X, padx=5, pady=5)
        self.data_entry.insert(tk.END, "00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F")
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.execute_btn = ttk.Button(button_frame, text="执行控制传输", command=self.execute_transfer, state=tk.DISABLED)
        self.execute_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="清除日志", command=self.clear_log)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="传输日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.insert(tk.END, "就绪。请选择USB设备并配置参数。\n")
        self.log_text.config(state=tk.DISABLED)
        
        # 绑定事件
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_select)

    def refresh_devices(self):
        self.log("正在扫描USB设备...")
        self.devices = []
        self.device_combo.set('')
        self.device_combo.configure(values=())
        try:
            # 查找所有USB设备
            devices = usb.core.find(find_all=True, idVendor = 0x34C7)
            
            for dev in devices:
                print(dev)
                try:
                    # 获取设备信息
                    vid = dev.idVendor
                    pid = dev.idProduct
                    bus = dev.bus
                    address = dev.address
                    manufacturer = usb.util.get_string(dev, dev.iManufacturer) or "未知制造商"
                    product = usb.util.get_string(dev, dev.iProduct) or "未知产品"
                    
                    device_info = {
                        "device": dev,
                        "vid": vid,
                        "pid": pid,
                        "bus": bus,
                        "address": address,
                        "manufacturer": manufacturer,
                        "product": product
                    }
                    self.devices.append(device_info)
                    # 添加到下拉框
                    display_text = f"{manufacturer} {product} (VID: 0x{vid:04X}, PID: 0x{pid:04X}, 总线: {bus}, 地址: {address})"
                    self.device_combo['values'] = (*self.device_combo['values'], display_text)
                    
                except usb.core.USBError as e:
                    self.log(f"读取设备信息错误: {str(e)}")
            
            if self.devices:
                self.log(f"找到 {len(self.devices)} 个USB设备")
                self.device_combo.current(0)
                self.on_device_select()
            else:
                self.log("未找到USB设备")
                self.execute_btn.config(state=tk.DISABLED)
                
        except Exception as e:
            self.log(f"扫描设备时出错: {str(e)}")
            messagebox.showerror("错误", f"无法扫描USB设备: {str(e)}")

    def on_device_select(self, event=None):
        index = self.device_combo.current()
        if index >= 0 and index < len(self.devices):
            self.selected_device = self.devices[index]
            self.display_device_info()
            self.execute_btn.config(state=tk.NORMAL)
        else:
            self.selected_device = None
            self.device_info.config(state=tk.NORMAL)
            self.device_info.delete(1.0, tk.END)
            self.device_info.insert(tk.END, "请选择USB设备...")
            self.device_info.config(state=tk.DISABLED)
            self.execute_btn.config(state=tk.DISABLED)

    def display_device_info(self):
        if not self.selected_device:
            return
            
        dev_info = self.selected_device
        info_text = (
            f"制造商: {dev_info['manufacturer']}\n"
            f"产品: {dev_info['product']}\n"
            f"VID: 0x{dev_info['vid']:04X}  PID: 0x{dev_info['pid']:04X}\n"
            f"总线: {dev_info['bus']}  地址: {dev_info['address']}\n"
            f"设备句柄: {dev_info['device']}"
        )
        
        self.device_info.config(state=tk.NORMAL)
        self.device_info.delete(1.0, tk.END)
        self.device_info.insert(tk.END, info_text)
        self.device_info.config(state=tk.DISABLED)

    def execute_transfer(self):
        if not self.selected_device:
            self.log("错误: 未选择设备")
            return
            
        # 获取参数
        try:
            bmRequestType = int(self.param_entries["bmRequestType"].get(), 0)
            bRequest = int(self.param_entries["bRequest"].get(), 0)
            wValue = int(self.param_entries["wValue"].get(), 0)
            wIndex = int(self.param_entries["wIndex"].get(), 0)
            wLength = int(self.param_entries["wLength"].get(), 0)
            timeout = int(self.param_entries["timeout"].get(), 0)
            
            direction = self.direction_var.get()
            data_hex = self.data_entry.get("1.0", tk.END).strip()
            
            # 解析数据
            data_bytes = None
            if direction == "OUT":
                if not data_hex:
                    raise ValueError("OUT传输需要提供数据")
                # 移除所有非十六进制字符
                data_hex = re.sub(r'[^0-9A-Fa-f]', '', data_hex)
                if len(data_hex) % 2 != 0:
                    raise ValueError("十六进制数据长度应为偶数")
                data_bytes = bytes.fromhex(data_hex)
                wLength = len(data_bytes)  # 覆盖参数中的长度
                
            # 在日志中显示传输信息
            self.log("\n" + "="*50)
            self.log(f"开始控制传输 [方向: {direction}]")
            self.log(f"参数: bmRequestType=0x{bmRequestType:02X}, bRequest=0x{bRequest:02X}, "
                  f"wValue=0x{wValue:04X}, wIndex=0x{wIndex:04X}, wLength={wLength}, timeout={timeout}ms")
            
            if data_bytes and direction == "OUT":
                self.log(f"发送数据 ({len(data_bytes)} 字节): {data_bytes.hex(' ', 1).upper()}")
            
            # 在新线程中执行传输
            thread = threading.Thread(
                target=self.perform_control_transfer,
                args=(bmRequestType, bRequest, wValue, wIndex, wLength, timeout, direction, data_bytes),
                daemon=True
            )
            thread.start()
            
        except ValueError as e:
            self.log(f"参数错误: {str(e)}")
            messagebox.showerror("参数错误", str(e))
        except Exception as e:
            self.log(f"执行传输时出错: {str(e)}")
            messagebox.showerror("错误", str(e))

    def perform_control_transfer(self, bmRequestType, bRequest, wValue, wIndex, wLength, timeout, direction, data_bytes):
        try:
            device = self.selected_device["device"]
            
            # 执行控制传输
            start_time = time.time()
            data = None
            if direction == "IN":
                # IN 传输 (设备到主机)
                result = device.ctrl_transfer(
                    bmRequestType=bmRequestType,
                    bRequest=bRequest,
                    wValue=wValue,
                    wIndex=wIndex,
                    data_or_wLength=wLength,
                    timeout=timeout
                )
                elapsed = (time.time() - start_time) * 1000
                print(result)
                print(type(result))
                # 处理结果
                if isinstance(result, bytes):
                    data = result
                elif isinstance(result, list):
                    data = bytes(result)
                elif isinstance(result, array):
                    data = result.tobytes()
                else:
                    data = bytes()
                
                self.log(f"传输成功! 接收 {len(data)} 字节 (耗时: {elapsed:.2f}ms)")
                
                # 格式化显示数据
                if data:
                    hex_data = data.hex(' ', 1).upper()
                    self.log("接收数据:")
                    self.log(hex_data)
                    
                    # 在UI中显示数据
                    self.data_entry.delete("1.0", tk.END)
                    self.data_entry.insert(tk.END, hex_data)
                else:
                    self.log("未接收到数据")
                    
            else:  # OUT 传输
                # 执行OUT传输
                bytes_written = device.ctrl_transfer(
                    bmRequestType=bmRequestType,
                    bRequest=bRequest,
                    wValue=wValue,
                    wIndex=wIndex,
                    data_or_wLength=data_bytes,
                    timeout=timeout
                )
                elapsed = (time.time() - start_time) * 1000
                
                self.log(f"传输成功! 发送 {bytes_written} 字节 (耗时: {elapsed:.2f}ms)")
                
        except usb.core.USBError as e:
            self.log(f"USB错误: {str(e)}")
        except Exception as e:
            self.log(f"传输过程中出错: {str(e)}")

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log("日志已清除")

if __name__ == "__main__":
    root = tk.Tk()
    app = USBControlTransferApp(root)
    root.mainloop()
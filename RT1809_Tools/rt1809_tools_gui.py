"""主应用程序GUI"""

import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from typing import Optional


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rt1809_tools_config import (
    __version__, __author__, APP_ICON, OTA, OTA_RES,
    CHIP_RT1809, CHIP_RT9806
)
from rt1809_tools_isp_programmer import ISPProgrammer
from rt1809_tools_ota_func import (
    GetFwImageNum, GetPanelSourceState, GetPanelState, GetPanelNumber, GetPanelSize,
    ProgressCallback, ota_usb_send, ota_usb_send_res, ota_usb_send_rt9806,
    CreatePackage, CryptoLib, random_key, set_control_transfer
)


class MainApplication:
    """主应用程序 - 整合ISP和OTA功能"""
    
    def __init__(self, get_resource_path_func):
        self.get_resource_path = get_resource_path_func
        self.root = tk.Tk()
        self.root.title(f"RacerTech 固件升级工具 v{__version__}")
        self.root.geometry("550x350")
        self.root.resizable(False, False)

        # 添加烧录时间记录
        self.isp_start_time = None
        self.isp_end_time = None

        # 初始化变量
        self.is_running = False
        self.progress_queue = queue.Queue()
        self.isp_programmer: Optional[ISPProgrammer] = None
        self.ota_thread = None
        self.isp_burn_thread = None
        self.isp_burn_cancel = False
        self.last_isp_progress = 0
        self.chip_type = tk.StringVar(value=CHIP_RT1809)  # 芯片类型，默认RT1809

        # 设置图标
        self.setup_icon()
        
        # 创建菜单栏
        self.setup_menubar()
        
        # 创建主界面
        self.setup_main_interface()
        
        # 启动进度监控
        self.start_ota_progress_monitor()
    
    def create_new_isp_programmer(self):
        """创建新的ISP编程器实例"""
        # 如果存在旧实例，先清理
        if self.isp_programmer:
            try:
                self.isp_programmer.protocol.close_port()
            except:
                pass
            self.isp_programmer = None
            
        # 创建新实例
        self.isp_programmer = ISPProgrammer(self.append_isp_log, self.update_isp_address_display, self.get_resource_path)
        return self.isp_programmer
        
    def setup_icon(self):
        """设置应用程序图标"""
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, APP_ICON)
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), APP_ICON)
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置图标失败: {e}")

    def setup_menubar(self):
        """设置菜单栏 - 只保留帮助菜单"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 只保留帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="使用说明", command=self.show_help)

    def setup_main_interface(self):
        """设置主界面"""
        # 创建选项卡控件
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建ISP选项卡
        self.isp_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.isp_frame, text="ISP烧录")
        self.setup_isp_tab()
        
        # 创建OTA选项卡
        self.ota_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.ota_frame, text="OTA升级")
        self.setup_ota_tab()

    def setup_isp_tab(self):
        """设置ISP烧录选项卡"""
        # 控制面板
        control_frame = ttk.LabelFrame(self.isp_frame, text="控制面板", padding=8)
        control_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 串口选择
        port_frame = ttk.Frame(control_frame)
        port_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(port_frame, text="串口:").pack(side=tk.LEFT, padx=(0, 5))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, width=15)
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.refresh_btn = ttk.Button(port_frame, text="刷新", command=self.refresh_ports, width=6)
        self.refresh_btn.pack(side=tk.LEFT)
        
        # 固件选择
        firmware_frame = ttk.Frame(control_frame)
        firmware_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(firmware_frame, text="固件:").pack(side=tk.LEFT, padx=(0, 5))
        self.firmware_var = tk.StringVar()
        self.firmware_entry = ttk.Entry(firmware_frame, textvariable=self.firmware_var, width=40)
        self.firmware_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        self.browse_btn = ttk.Button(firmware_frame, text="浏览", command=self.browse_firmware, width=6)
        self.browse_btn.pack(side=tk.LEFT)
        
        # 操作按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=8)
        
        self.isp_burn_btn = ttk.Button(button_frame, text="开始烧录", command=self.start_isp_burn, width=12)
        self.isp_burn_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.isp_stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_isp_burn, state=tk.DISABLED, width=8)
        self.isp_stop_btn.pack(side=tk.LEFT)
        
        # 进度条
        progress_frame = ttk.LabelFrame(self.isp_frame, text="烧录进度", padding=8)
        progress_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.isp_progress_var = tk.IntVar()
        self.isp_progress_bar = ttk.Progressbar(progress_frame, variable=self.isp_progress_var, maximum=100)
        self.isp_progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # 状态信息 - 只有两边的Label
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X)
        
        # 左边的Label：显示Verify/Erase/Program Address
        self.isp_address_label = ttk.Label(status_frame, text="", font=("Arial", 9), foreground="blue")
        self.isp_address_label.pack(side=tk.LEFT)
        
        # 右边的Label：显示进度百分比和状态
        self.isp_status_label = ttk.Label(status_frame, text="0% 就绪", foreground="green", font=("Arial", 9))
        self.isp_status_label.pack(side=tk.RIGHT)
        
        # 初始化串口列表
        self.refresh_ports()

    def setup_ota_tab(self):
        """设置OTA升级选项卡 """
        # 主容器 - 使用网格布局
        main_container = ttk.Frame(self.ota_frame)
        main_container.pack(fill="both", expand=True)
        
        # 配置网格权重
        main_container.columnconfigure(0, weight=1)  # 左列
        main_container.columnconfigure(1, weight=1)  # 右列
        main_container.rowconfigure(0, weight=0)     # 芯片选择
        main_container.rowconfigure(1, weight=0)     # 文件路径
        main_container.rowconfigure(2, weight=0)     # OTA模式
        main_container.rowconfigure(3, weight=1)     # 传输进度
        main_container.rowconfigure(4, weight=0)     # 状态和按钮
        
        # ===== 第一行 - 芯片选择 =====
        chip_frame = ttk.Frame(main_container)
        chip_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        
        ttk.Label(chip_frame, text="芯片:").pack(side="left", padx=(0, 5))
        self.chip_combo = ttk.Combobox(chip_frame, textvariable=self.chip_type, 
                                       values=[CHIP_RT1809, CHIP_RT9806], 
                                       state="readonly", width=10)
        self.chip_combo.pack(side="left")
        self.chip_combo.bind("<<ComboboxSelected>>", lambda e: self.on_chip_type_changed())
        
        # ===== 第二行 - 文件路径 =====
        file_frame = ttk.Frame(main_container)
        file_frame.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        file_frame.columnconfigure(1, weight=1)  # 文件输入框可扩展
        
        ttk.Label(file_frame, text="文件:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_var)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(file_frame, text="浏览", command=self.browse_ota_file, width=6).grid(row=0, column=2)
        
        # ===== 第三行 - OTA模式 =====
        mode_frame = ttk.LabelFrame(main_container, text="OTA模式", padding=6)
        mode_frame.grid(row=2, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        
        mode_inner_frame = ttk.Frame(mode_frame)
        mode_inner_frame.pack(fill="x", pady=3)
        
        self.mode_var = tk.IntVar(value=OTA)
        self.firmware_radio = ttk.Radiobutton(mode_inner_frame, text="固件升级", 
                        variable=self.mode_var, value=OTA)
        self.firmware_radio.pack(side="left", padx=(10, 20))
        self.resource_radio = ttk.Radiobutton(mode_inner_frame, text="影像升级", 
                        variable=self.mode_var, value=OTA_RES)
        self.resource_radio.pack(side="left")
        
        # ===== 第四行 - 传输进度 =====
        progress_frame = ttk.LabelFrame(main_container, text="传输进度", padding=6)
        progress_frame.grid(row=3, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        
        # 进度条
        self.ota_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.ota_progress.pack(fill="x", pady=(0, 3))
        
        # 进度详情
        detail_frame = ttk.Frame(progress_frame)
        detail_frame.pack(fill="x")
        
        self.ota_progress_detail = ttk.Label(detail_frame, text="0 / 0 Byte (0%)", font=("Arial", 8))
        self.ota_progress_detail.pack(side="left")
        
        self.ota_speed_label = ttk.Label(detail_frame, text="0 KB/s", font=("Arial", 8))
        self.ota_speed_label.pack(side="right")
        
        # ===== 第五行 - 状态和开始按钮 =====
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        
        self.ota_status_label = ttk.Label(bottom_frame, text="就绪", foreground="green", font=("Arial", 9))
        self.ota_status_label.pack(side="left", pady=5)
        
        self.ota_start_btn = ttk.Button(bottom_frame, text="开始OTA", 
                                        command=self.start_ota, width=12)
        self.ota_start_btn.pack(side="right")
        
        # ===== 右侧区域 - 设备信息 =====
        device_frame = ttk.LabelFrame(main_container, text="设备信息", padding=8)
        device_frame.grid(row=0, column=1, rowspan=5, sticky="nsew", padx=(5, 0))
        
        # 设备信息内部使用紧凑布局
        device_inner_frame = ttk.Frame(device_frame)
        device_inner_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 按钮框架 - 水平排列两个按钮
        button_frame = ttk.Frame(device_inner_frame)
        button_frame.pack(fill="x", pady=(0, 10))
        
        self.get_info_btn = ttk.Button(button_frame, text="获取设备信息", 
                                       command=self.get_fw_image_number, width=14)
        self.get_info_btn.pack(side="left", padx=(0, 5))
        
        # 新增影像转换工具按钮
        self.video_tool_btn = ttk.Button(button_frame, text="影像转换工具", 
                                         command=self.open_video_converter, width=14)
        self.video_tool_btn.pack(side="left")
        
        # 屏信息显示区域
        panels_frame = ttk.Frame(device_inner_frame)
        panels_frame.pack(fill="both", expand=True)
        
        # 屏1信息
        panel1_frame = ttk.LabelFrame(panels_frame, text="屏 1", padding=6)
        panel1_frame.pack(fill="x", pady=(0, 8))
        
        self.panel1_res_label = ttk.Label(panel1_frame, text="分辨率: --", font=("Arial", 9))
        self.panel1_res_label.pack(anchor="w", pady=2)
        
        self.panel1_img_label = ttk.Label(panel1_frame, text="图像数: --", font=("Arial", 9))
        self.panel1_img_label.pack(anchor="w", pady=2)
        
        # 屏2信息
        panel2_frame = ttk.LabelFrame(panels_frame, text="屏 2", padding=6)
        panel2_frame.pack(fill="x")
        
        self.panel2_res_label = ttk.Label(panel2_frame, text="None", font=("Arial", 9), foreground="gray")
        self.panel2_res_label.pack(anchor="w", pady=2)
        
        self.panel2_img_label = ttk.Label(panel2_frame, text="", font=("Arial", 9))
        self.panel2_img_label.pack(anchor="w", pady=2)
        
        # 初始化芯片类型变更处理（在所有控件创建完成后调用）
        self.on_chip_type_changed()

    def open_video_converter(self):
        """打开视频转换工具窗口"""
        # 检查芯片类型，RT9806不支持此功能
        chip = self.chip_type.get()
        if chip == CHIP_RT9806:
            messagebox.showwarning("提示", "RT9806芯片不支持影像转换工具功能")
            return
        
        try:
            # 动态导入视频转换工具
            from rt1809_tools_video_converter import VideoFrameExtractor
            
            # 检查必要的库是否已安装
            import cv2
            import numpy as np
            from PIL import Image
            import struct
        except ImportError as e:
            messagebox.showerror("错误", f"缺少必要的库: {e}\n\n请安装以下库:\n- opencv-python\n- pillow\n- numpy")
            return
        
        # 创建新窗口
        video_window = tk.Toplevel(self.root)
        video_window.title("RacerTech视频转换工具")
        video_window.transient(self.root)  # 设置为主窗口的子窗口
        video_window.grab_set()  # 模态窗口
        
        # 创建视频转换工具实例
        VideoFrameExtractor(video_window)

    # ==================== ISP功能方法 ====================
    def refresh_ports(self):
        """刷新串口列表"""
        import serial.tools.list_ports
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def browse_firmware(self):
        """浏览选择固件文件"""
        filename = filedialog.askopenfilename(
            title="选择固件文件",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.firmware_var.set(filename)

    def append_isp_log(self, message: str):
        """添加ISP日志"""
        if "[ERROR]" in message:
            def _show_error():
                self.isp_status_label.config(text="烧录失败", foreground="red")
                error_msg = message.split("] ")[-1] if "] " in message else message
                messagebox.showerror("烧录错误", f"ISP烧录失败：{error_msg}")
            
            self.root.after(0, _show_error)
        elif "[SUCCESS]" in message:
            pass
        elif "[PROGRESS]" in message:
            def _update_progress():
                progress_text = message.split("] ")[-1] if "] " in message else message
                self.isp_status_label.config(text=progress_text, foreground="blue")
            
            self.root.after(0, _update_progress)

    def update_isp_address_display(self, address_text: str):
        """更新ISP地址显示"""
        def _update():
            self.isp_address_label.config(text=address_text)
        self.root.after(0, _update)

    def update_isp_progress(self, value: int):
        """更新ISP进度条和状态显示"""
        if value < self.last_isp_progress:
            value = self.last_isp_progress
        else:
            self.last_isp_progress = value
            
        def _update():
            self.isp_progress_var.set(value)
            
            # 根据进度值确定状态文本
            if value == 0:
                status_text = "正在启动ISP模式..."
            elif value < 100:
                status_text = f"烧录中... {value}%"
            elif value == 100:
                status_text = "烧录完成"
            else:
                status_text = f"处理中... {value}%"
            
            # 更新状态标签
            self.isp_status_label.config(text=status_text)
            
            # 设置颜色
            if value == 100:
                self.isp_status_label.config(foreground="green")
            elif value < 100:
                self.isp_status_label.config(foreground="blue")
        
        self.root.after(0, _update)

    def start_isp_burn(self):
        """开始ISP烧录"""
        if not self.port_var.get():
            messagebox.showerror("错误", "请选择串口")
            return
        
        if not self.firmware_var.get():
            messagebox.showerror("错误", "请选择固件文件")
            return
        
        if not os.path.exists(self.firmware_var.get()):
            messagebox.showerror("错误", "固件文件不存在")
            return
        
        # 检查ISP文件是否存在
        from rt1809_tools_config import ISPConfig
        if getattr(sys, 'frozen', False):
            isp_cmd_path = os.path.join(sys._MEIPASS, ISPConfig.ISP_CMD_FILE)
            isp_driver_path = os.path.join(sys._MEIPASS, ISPConfig.ISP_DRIVER_FILE)
        else:
            isp_cmd_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ISPConfig.ISP_CMD_FILE)
            isp_driver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ISPConfig.ISP_DRIVER_FILE)
        
        if not os.path.exists(isp_cmd_path):
            messagebox.showerror("错误", f"ISP命令文件不存在: {isp_cmd_path}")
            return
            
        if not os.path.exists(isp_driver_path):
            messagebox.showerror("错误", f"ISP驱动文件不存在: {isp_driver_path}")
            return
        
        # 记录开始时间
        self.isp_start_time = time.time()

        # 创建新的ISP编程器实例（确保状态干净）
        self.create_new_isp_programmer()

        # 重置状态
        self.isp_burn_cancel = False
        self.last_isp_progress = 0
        
        # 禁用控件
        self.isp_burn_btn.config(state=tk.DISABLED)
        self.isp_stop_btn.config(state=tk.NORMAL)
        self.port_combo.config(state=tk.DISABLED)
        self.firmware_entry.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.refresh_btn.config(state=tk.DISABLED)
        
        # 重置进度和状态
        self.isp_progress_var.set(0)
        self.isp_status_label.config(text="正在启动ISP模式...", foreground="blue")
        self.isp_address_label.config(text="")
        
        # 启动烧录线程
        self.isp_burn_thread = threading.Thread(
            target=self._isp_burn_thread,
            args=(self.port_var.get(), self.firmware_var.get()),
            daemon=True
        )
        self.isp_burn_thread.start()

    def format_time(self, seconds):
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}分{secs:.1f}秒"

    def _isp_burn_thread(self, port: str, firmware: str):
        """ISP烧录线程"""
        success = False
        cancelled = False

        try:
            # 确保有编程器实例
            if not self.isp_programmer:
                self.create_new_isp_programmer()
            success = self.isp_programmer.burn_firmware(port, firmware, self.update_isp_progress)
            cancelled = self.isp_programmer.is_cancelled()
            
        except Exception as e:
            error_msg = f"烧录过程异常: {str(e)}"
            self.append_isp_log(f"[ERROR] {error_msg}")
            success = False
        finally:
            self.isp_end_time = time.time()
            # 确保串口关闭
            if self.isp_programmer:
                try:
                    self.isp_programmer.protocol.close_port()
                except:
                    pass
        
        # 计算总耗时
        total_time = self.isp_end_time - self.isp_start_time if self.isp_start_time else 0
        time_str = self.format_time(total_time)
        
        # 在主线程中更新UI
        def _finish():
            if cancelled:
                # 被用户取消
                self.isp_status_label.config(text=f"烧录已取消 (耗时: {time_str})", foreground="orange")
                self.isp_progress_var.set(0)
                self.isp_address_label.config(text="")
            elif success:
                # 成功完成
                self.isp_progress_var.set(100)
                self.isp_status_label.config(text=f"烧录成功 (耗时: {time_str})", foreground="green")
                self.isp_address_label.config(text="")
                messagebox.showinfo("成功", f"固件烧录成功！\n\n 耗时: {time_str}")
            else:
                # 失败
                self.isp_status_label.config(text=f"烧录失败 (耗时: {time_str})", foreground="red")
            
            # 恢复控件（如果没有被停止按钮处理）
            if not cancelled:
                self.reset_isp_ui()
        
        self.root.after(0, _finish)

    def stop_isp_burn(self):
        """停止ISP烧录"""
        if not self.isp_burn_thread or not self.isp_burn_thread.is_alive():
            self.reset_isp_ui()
            return

        # 记录停止时间并计算已用时间
        if self.isp_start_time:
            elapsed = time.time() - self.isp_start_time
            time_str = self.format_time(elapsed)
        
        # 设置取消标志
        if self.isp_programmer:
            self.isp_programmer.cancel()

        # 更新UI状态
        self.isp_status_label.config(text="正在停止...", foreground="orange")
        self.isp_address_label.config(text="")
        
        # 禁用停止按钮，防止重复点击
        self.isp_stop_btn.config(state=tk.DISABLED)
        self.isp_burn_btn.config(state=tk.DISABLED)

        # 在后台线程中处理停止操作
        def stop_and_cleanup():
            try:
                # 等待烧录线程结束（最多3秒）
                if self.isp_burn_thread:
                    self.isp_burn_thread.join(timeout=3.0)
                
                # 强制关闭串口并清理
                if self.isp_programmer:
                    try:
                        # 尝试发送退出ISP命令
                        if self.isp_programmer.protocol.serial_port and \
                           self.isp_programmer.protocol.serial_port.is_open:
                            try:
                                from rt1809_tools_config import Command
                                packet = self.isp_programmer.protocol.build_request_packet(
                                    Command.EXIT_ISP_MODE, 0, b''
                                )
                                self.isp_programmer.protocol.send_data(packet)
                                time.sleep(0.1)
                            except:
                                pass
                            
                        # 关闭串口
                        self.isp_programmer.protocol.close_port()
                    except Exception as e:
                        print(f"清理串口时出错: {e}")
                    
                    # 清空编程器实例
                    self.isp_programmer = None
                
                # 额外等待，确保串口完全释放
                time.sleep(0.5)
                
            except Exception as e:
                print(f"停止过程出错: {e}")
            finally:
                # 在主线程中恢复UI
                self.root.after(0, self.cleanup_after_stop)
        
        # 启动停止线程
        stop_thread = threading.Thread(target=stop_and_cleanup, daemon=True)
        stop_thread.start()

    def cleanup_after_stop(self):
        """停止后的清理和UI恢复"""
        # 清空线程引用
        self.isp_burn_thread = None
        
        # 重置UI
        self.reset_isp_ui()
        
        # 刷新串口列表（串口可能需要重新识别）
        self.refresh_ports()
        
        # 显示提示
        messagebox.showinfo("提示", "烧录已停止。如需重新烧录，请选择正确的串口。")
    
    def reset_isp_ui(self):
        """重置ISP界面状态"""
        # 重置进度和状态
        self.isp_progress_var.set(0)
        self.isp_status_label.config(text="就绪", foreground="green")
        self.isp_address_label.config(text="")
        
        # 恢复所有控件
        self.isp_burn_btn.config(state=tk.NORMAL)
        self.isp_stop_btn.config(state=tk.DISABLED)
        self.port_combo.config(state=tk.NORMAL)
        self.firmware_entry.config(state=tk.NORMAL)
        self.browse_btn.config(state=tk.NORMAL)
        self.refresh_btn.config(state=tk.NORMAL)

    # ==================== OTA功能方法 ====================
    def on_chip_type_changed(self):
        """芯片类型变更时的处理"""
        chip = self.chip_type.get()
        
        if chip == CHIP_RT9806:
            # RT9806只支持固件升级
            self.mode_var.set(OTA)  # 强制设置为固件升级
            self.firmware_radio.config(state=tk.NORMAL)
            self.resource_radio.config(state=tk.DISABLED)
            self.get_info_btn.config(state=tk.DISABLED)
            self.video_tool_btn.config(state=tk.DISABLED)
            # 清空设备信息显示
            self.reset_panel_displays()
        else:
            # RT1809支持所有功能
            self.firmware_radio.config(state=tk.NORMAL)
            self.resource_radio.config(state=tk.NORMAL)
            self.get_info_btn.config(state=tk.NORMAL)
            self.video_tool_btn.config(state=tk.NORMAL)
    
    def get_fw_image_number(self):
        """获取设备信息 - 修改后的函数"""
        if self.is_running:
            messagebox.showwarning("警告", "OTA正在进行中，请等待完成后再获取！")
            return
        
        # 检查芯片类型，RT9806不支持此功能
        chip = self.chip_type.get()
        if chip == CHIP_RT9806:
            messagebox.showwarning("提示", "RT9806芯片不支持获取设备信息功能")
            return
        
        try:
            # 先检查设备是否连接
            import usb.core
            dev = usb.core.find(idVendor=0x34C7, idProduct=0x8888)
            if dev is None:
                messagebox.showerror("错误", "设备未连接！")
                self.reset_panel_displays()
                return
        
            # 获取屏数量
            panel_num = GetPanelNumber()
            
            # 根据屏数量获取详细信息
            if panel_num == 1:
                # 单屏：获取图像数和分辨率
                fw_image_num = GetFwImageNum(0)
                panel_size = GetPanelSize(0)
                
                # 更新屏1信息
                self.update_panel_display(0, fw_image_num, panel_size)
                # 屏2显示None
                self.panel2_res_label.config(text="None", foreground="gray")
                self.panel2_img_label.config(text="")
                
            elif panel_num == 2:
                # 双屏：获取两个屏的信息
                fw_image_num_0 = GetFwImageNum(0)
                fw_image_num_1 = GetFwImageNum(1)
                panel_size_0 = GetPanelSize(0)
                panel_size_1 = GetPanelSize(1)
                
                # 更新两个屏的信息
                self.update_panel_display(0, fw_image_num_0, panel_size_0)
                self.update_panel_display(1, fw_image_num_1, panel_size_1)
                
            else:
                messagebox.showerror("错误", f"不支持的屏数量: {panel_num}")
                self.reset_panel_displays()
                return
            
            self.update_ota_status(f"获取成功: {panel_num}个屏", "green")
            
        except Exception as e:
            print(f"获取屏信息失败: {e}")
            self.reset_panel_displays()
            messagebox.showerror("错误", f"获取屏信息失败：{str(e)}")

    def update_panel_display(self, panel_index, image_count, panel_size):
        """更新屏信息显示"""
        if panel_index == 0:
            res_label = self.panel1_res_label
            img_label = self.panel1_img_label
        else:
            res_label = self.panel2_res_label
            img_label = self.panel2_img_label
        
        # 更新分辨率显示
        if panel_size is not None and len(panel_size) >= 4:
            height = panel_size[0] + (panel_size[1] * 16 * 16)
            width = panel_size[2] + (panel_size[3] * 16 * 16)
            resolution_text = f"分辨率: {width}x{height}"
            res_label.config(text=resolution_text, foreground="blue")
        else:
            res_label.config(text="分辨率: 未知", foreground="red")
        
        # 更新图像数显示
        if image_count is not None:
            img_label.config(text=f"图像数: {image_count}", foreground="blue")
        else:
            img_label.config(text="图像数: --", foreground="red")

    def reset_panel_displays(self):
        """重置屏信息显示"""
        self.panel1_res_label.config(text="分辨率: --", foreground="black")
        self.panel1_img_label.config(text="图像数: --", foreground="black")
        self.panel2_res_label.config(text="None", foreground="gray")
        self.panel2_img_label.config(text="")
        
    def browse_ota_file(self):
        """浏览OTA文件"""
        filename = filedialog.askopenfilename(
            title="选择OTA文件",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.file_var.set(filename)
            
    def update_ota_status(self, text, color="black"):
        """更新OTA状态"""
        self.ota_status_label.config(text=text, foreground=color)

    def ota_progress_callback(self, progress, current, total):
        """OTA进度回调函数"""
        self.progress_queue.put(('progress', progress, current, total))

    def start_ota_progress_monitor(self):
        """启动OTA进度监控"""
        self.last_ota_update_time = time.time()
        self.last_ota_bytes = 0
        self.check_ota_progress_queue()

    def check_ota_progress_queue(self):
        """检查OTA进度队列"""
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                if msg[0] == 'progress':
                    _, progress, current, total = msg
                    self.ota_progress['value'] = progress
                    
                    # 计算速度
                    current_time = time.time()
                    time_diff = current_time - self.last_ota_update_time
                    if time_diff > 0:
                        bytes_diff = current - self.last_ota_bytes
                        speed = bytes_diff / time_diff / 1024
                        self.ota_speed_label.config(text=f"{speed:.2f} KB/s")
                        self.last_ota_update_time = current_time
                        self.last_ota_bytes = current

                    self.ota_progress_detail.config(
                        text=f"{current:,} / {total:,} Byte ({progress:.1f}%)"
                    )
                elif msg[0] == 'status':
                    self.update_ota_status(msg[1], msg[2])
                elif msg[0] == 'complete':
                    self.ota_complete(msg[1], msg[2] if len(msg) > 2 else None)
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_ota_progress_queue)
        
    def start_ota(self):
        """开始OTA"""
        if self.is_running:
            messagebox.showwarning("警告", "OTA正在进行中，请等待完成！")
            return
            
        file_path = self.file_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("错误", "文件不存在！")
            return

        # 重置进度
        self.ota_progress['value'] = 0
        self.ota_progress_detail.config(text="0 / 0 Byte (0%)")
        self.ota_speed_label.config(text="0 KB/s")
        self.last_ota_update_time = time.time()
        self.last_ota_bytes = 0

        self.is_running = True
        self.ota_start_btn.config(state="disabled")
        self.get_info_btn.config(state="disabled")
        self.video_tool_btn.config(state="disabled")
        
        # 在新线程中执行OTA
        self.ota_thread = threading.Thread(target=self.run_ota, daemon=True)
        self.ota_thread.start()
        
    def run_ota(self):
        """在后台线程执行OTA操作"""
        try:
            chip = self.chip_type.get()
            mode = self.mode_var.get()
            file_path = self.file_var.get()
            
            # RT9806使用不同的OTA流程
            if chip == CHIP_RT9806:
                # RT9806只支持固件升级
                self.progress_queue.put(('status', "正在连接RT9806设备...", "blue"))
                
                # 创建进度回调
                progress_cb = ProgressCallback()
                progress_cb.callback = self.ota_progress_callback
                
                self.progress_queue.put(('status', "正在进行RT9806固件OTA...", "blue"))
                success = ota_usb_send_rt9806(file_path=file_path, progress_callback=progress_cb)
                
                self.progress_queue.put(('complete', success, None))
                return
            
            # RT1809的原有流程
            # 更新文件路径
            from rt1809_tools_config import OTA_FILE_PATH, OTA_RES_FILE_PATH
            if mode == OTA:
                OTA_FILE_PATH = file_path
            else:
                OTA_RES_FILE_PATH = file_path
            
            # 创建进度回调
            progress_cb = ProgressCallback()
            progress_cb.callback = self.ota_progress_callback

            self.progress_queue.put(('status', "正在等待设备就绪...", "blue"))
            
            # 等待设备就绪
            for i in range(1, 10):
                if GetPanelSourceState() == 1:
                    if GetPanelState() == 1:
                        break
                time.sleep(0.5)
                
            self.progress_queue.put(('status', "正在配置加密...", "blue"))
            package = CreatePackage(0x32, random_key)
            CryptoLib.config_key_function(random_key)
            set_control_transfer(0x01, package)
            
            self.progress_queue.put(('status', "正在发送握手信号...", "blue"))
            start = "star"
            ascii_list = [ord(c) for c in start]
            ciphertext = CryptoLib.ecies_encrypt(ascii_list)
            package = CreatePackage(0x11, ciphertext)
            set_control_transfer(0x01, package)
            
            if mode == OTA:
                otar = "otaA" 
                ascii_list = [ord(c) for c in otar]
                ciphertext = CryptoLib.ecies_encrypt(ascii_list)
                package = CreatePackage(0x11, ciphertext)
                set_control_transfer(0x01, package)
                self.progress_queue.put(('status', "正在进行固件OTA...", "blue"))
                success = ota_usb_send(vid=0x34C7, pid=0x8888, endpoint_out=0x02, 
                                     file_path=file_path, progress_callback=progress_cb)
            else:
                otar = "otaR"
                ascii_list = [ord(c) for c in otar]
                ciphertext = CryptoLib.ecies_encrypt(ascii_list)
                package = CreatePackage(0x11, ciphertext)
                set_control_transfer(0x01, package)
                self.progress_queue.put(('status', "正在进行资源OTA...", "blue"))
                success = ota_usb_send_res(vid=0x34C7, pid=0x8888, endpoint_out=0x02, 
                                         file_path=file_path, progress_callback=progress_cb)
            
            self.progress_queue.put(('complete', success, None))
            
        except Exception as e:
            error_msg = str(e)
            print(f"OTA错误: {error_msg}")
            self.progress_queue.put(('complete', False, error_msg))
            
    def ota_complete(self, success, error_msg=None):
        """OTA完成后的处理"""
        self.is_running = False
        self.ota_start_btn.config(state="normal")
        
        # 根据芯片类型恢复按钮状态
        chip = self.chip_type.get()
        if chip == CHIP_RT9806:
            # RT9806模式下，这些按钮保持禁用
            self.get_info_btn.config(state=tk.DISABLED)
            self.video_tool_btn.config(state=tk.DISABLED)
        else:
            # RT1809模式下，恢复启用
            self.get_info_btn.config(state=tk.NORMAL)
            self.video_tool_btn.config(state=tk.NORMAL)
        
        if success:
            self.ota_progress['value'] = 100
            self.update_ota_status("OTA完成！", "green")
            messagebox.showinfo("成功", "OTA升级完成！")
        else:
            self.update_ota_status("OTA失败！", "red")
            messagebox.showerror("错误", f"OTA失败：{error_msg}")

    # ==================== 通用方法 ====================
    def show_about(self):
        """显示关于对话框"""
        about_text = f"""RacerTech 烧录工具
版本: {__version__}
作者: {__author__}
版权所有 © 2025 RacerTech

集成功能:
• ISP烧录 - 通过UART对MCU进行固件烧录
• OTA升级 - 通过USB进行固件和资源升级
• 影像转换工具 - 视频转BIN文件工具"""
        
        messagebox.showinfo("关于", about_text)
        
    def show_help(self):
        """显示帮助窗口"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x400")
        help_window.resizable(False, False)

        # 为帮助窗口设置图标
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, APP_ICON)
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), APP_ICON)
            
            if os.path.exists(icon_path):
                help_window.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置帮助窗口图标失败: {e}")
        
        # 创建文本框显示帮助信息
        help_text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, padx=10, pady=10)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_content = """
RacerTech 烧录工具使用说明

1. ISP烧录功能
   - 选择正确的串口和固件文件
   - 点击"开始烧录"进行固件烧录
   - 烧录过程中请勿断开设备连接

2. OTA升级功能
   - 确保USB设备连接并有驱动挂载
   - 点击"获取设备信息"按钮读取屏信息
   - 选择升级模式：固件升级或影像升级
   - 选择要升级的文件
   - 点击"开始OTA"进行升级

3. 影像转换工具
   - OTA升级界面点击"影像转换工具"按钮打开转换窗口
   - 选择视频文件和输出路径
   - 设置提取帧数量和选项
   - 确保视频文件分辨率和帧数量跟设备信息匹配
   - 生成BIN文件和头文件用于OTA升级

4. 注意事项
   - 确保设备连接正常
   - 选择正确的文件格式
   - 升级过程中不要断电或断开连接
   - 如遇问题请查看状态信息和错误提示

技术支持: RacerTech
"""
        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
        
        # 关闭按钮
        ttk.Button(help_window, text="关闭", command=help_window.destroy).pack(pady=10)

    def run(self):
        """运行应用程序"""
        self.root.mainloop()
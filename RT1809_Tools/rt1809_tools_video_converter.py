"""视频转换工具模块"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import os
import struct
import numpy as np
from PIL import Image
import sys


class VideoFrameExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("影像转换工具")
        
        # 设置窗口图标
        self.setup_icon()

        # 变量初始化
        self.video_path = tk.StringVar()
        self.video_path2 = tk.StringVar()  # 第二个视频文件
        self.frame_count = tk.IntVar(value=50)
        self.frame_count2 = tk.IntVar(value=50)  # 第二个视频帧数
        self.output_path = tk.StringVar()
        self.output_name = tk.StringVar(value="PicROM")
        self.generate_images = tk.BooleanVar(value=False)
        self.image_prefix = tk.StringVar(value="output")
        self.show_advanced = tk.BooleanVar(value=False)  # 更多配置选项
        self.dual_screen = tk.BooleanVar(value=False)  # 双屏选项
        self.progress = tk.DoubleVar()
        
        # 新增分辨率变量
        self.resolution1 = tk.StringVar(value="")
        self.resolution2 = tk.StringVar(value="")
        
        self.setup_ui()
    
    def setup_icon(self):
        """设置应用程序图标"""
        try:
            # 从主程序导入配置
            from rt1809_tools_config import APP_ICON
            
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, APP_ICON)
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), APP_ICON)
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置图标失败: {e}")
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 固定所有列的宽度，防止自动扩展
        for i in range(4):
            main_frame.columnconfigure(i, weight=0, minsize=0)
        
        # 行计数器
        row = 0
        
        # 视频文件选择1 - 使用紧凑布局
        ttk.Label(main_frame, text="选择视频文件1:").grid(row=row, column=0, sticky=tk.W, pady=3)
        
        # 创建紧凑的文件选择框架
        file_frame1 = ttk.Frame(main_frame)
        file_frame1.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=3)
        
        video_entry1 = ttk.Entry(file_frame1, textvariable=self.video_path, width=30)
        video_entry1.grid(row=0, column=0, padx=(0, 5))
        ttk.Button(file_frame1, text="浏览", command=self.select_video, width=6).grid(row=0, column=1)
        row += 1
        
        # 视频1的帧数量设置和分辨率显示
        frame_res_frame1 = ttk.Frame(main_frame)
        frame_res_frame1.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        ttk.Label(frame_res_frame1, text="提取帧数量:").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(frame_res_frame1, from_=1, to=1000, textvariable=self.frame_count, width=8).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 分辨率显示
        ttk.Label(frame_res_frame1, text="分辨率:").grid(row=0, column=2, sticky=tk.W, padx=(15, 0))
        self.resolution_label1 = ttk.Label(frame_res_frame1, textvariable=self.resolution1, foreground="blue", width=10)
        self.resolution_label1.grid(row=0, column=3, sticky=tk.W, padx=5)
        row += 1
        
        # 双屏选项
        self.dual_screen_check = ttk.Checkbutton(
            main_frame, 
            text="双屏", 
            variable=self.dual_screen,
            command=self.toggle_dual_screen
        )
        self.dual_screen_check.grid(row=row, column=0, sticky=tk.W, pady=3)
        row += 1
        
        # 第二个视频文件选择（默认隐藏）
        self.video2_frame = ttk.Frame(main_frame)
        self.video2_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        # 视频文件选择2 - 使用紧凑布局
        ttk.Label(self.video2_frame, text="选择视频文件2:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # 创建紧凑的文件选择框架
        file_frame2 = ttk.Frame(self.video2_frame)
        file_frame2.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=2)
        
        video_entry2 = ttk.Entry(file_frame2, textvariable=self.video_path2, width=30)
        video_entry2.grid(row=0, column=0, padx=(0, 5))
        ttk.Button(file_frame2, text="浏览", command=self.select_video2, width=6).grid(row=0, column=1)
        
        # 第二个视频的帧数量和分辨率
        frame_res_frame2 = ttk.Frame(self.video2_frame)
        frame_res_frame2.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        ttk.Label(frame_res_frame2, text="提取帧数量:").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(frame_res_frame2, from_=1, to=1000, textvariable=self.frame_count2, width=8).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 第二个视频的分辨率显示
        ttk.Label(frame_res_frame2, text="分辨率:").grid(row=0, column=2, sticky=tk.W, padx=(15, 0))
        self.resolution_label2 = ttk.Label(frame_res_frame2, textvariable=self.resolution2, foreground="blue", width=10)
        self.resolution_label2.grid(row=0, column=3, sticky=tk.W, padx=5)
        row += 1
        
        # 输出路径选择 - 使用紧凑布局
        ttk.Label(main_frame, text="输出路径:").grid(row=row, column=0, sticky=tk.W, pady=3)
        
        # 创建紧凑的输出路径框架
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=3)
        
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path, width=30)
        output_entry.grid(row=0, column=0, padx=(0, 5))
        ttk.Button(output_frame, text="浏览", command=self.select_output_path, width=6).grid(row=0, column=1)
        row += 1
        
        # 更多配置选项
        self.advanced_check = ttk.Checkbutton(
            main_frame, 
            text="更多配置", 
            variable=self.show_advanced,
            command=self.toggle_advanced_options
        )
        self.advanced_check.grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        # 高级选项框架（默认隐藏）
        self.advanced_frame = ttk.LabelFrame(main_frame, text="高级选项", padding="5")
        self.advanced_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        
        # 输出文件名
        ttk.Label(self.advanced_frame, text="输出BIN文件名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(self.advanced_frame, textvariable=self.output_name, width=20).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 生成图片文件选项
        self.generate_images_check = ttk.Checkbutton(
            self.advanced_frame, 
            text="保存提取的帧图像文件", 
            variable=self.generate_images,
            command=self.toggle_image_prefix
        )
        self.generate_images_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 图片文件前缀（默认隐藏）
        self.image_prefix_label = ttk.Label(self.advanced_frame, text="文件名前缀(自动编号):")
        self.image_prefix_entry = ttk.Entry(self.advanced_frame, textvariable=self.image_prefix, width=20)
        row += 1
        
        # 进度条
        ttk.Label(main_frame, text="进度:").grid(row=row, column=0, sticky=tk.W, pady=8)
        # 设置固定宽度的进度条
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress, length=300)
        self.progress_bar.grid(row=row, column=1, columnspan=2, pady=8, sticky=tk.W)
        row += 1
        
        # 状态标签 - 固定宽度和高度
        ttk.Label(main_frame, text="状态:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.status_label = ttk.Label(main_frame, text="准备就绪", relief=tk.SUNKEN, padding="3", width=40, anchor=tk.W)
        self.status_label.grid(row=row, column=1, columnspan=2, pady=5, sticky=tk.W)
        row += 1
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="开始提取", command=self.start_extraction).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.root.destroy).pack(side=tk.LEFT, padx=5)
        
        # 初始化UI状态
        self.toggle_advanced_options()
        self.toggle_dual_screen()
        
        # 设置初始窗口大小并禁止调整
        self.update_window_size()
        self.root.resizable(False, False)  # 禁止调整窗口大小
    
    def update_window_size(self):
        """根据当前选项更新窗口大小"""
        if self.dual_screen.get() and self.show_advanced.get():
            # 同时勾选双屏和更多配置
            self.root.geometry("420x460")
        elif self.dual_screen.get():
            # 只勾选双屏
            self.root.geometry("420x360")
        elif self.show_advanced.get():
            # 只勾选更多配置
            self.root.geometry("420x410")
        else:
            # 都没有勾选
            self.root.geometry("420x300")
    
    def toggle_dual_screen(self):
        """切换双屏选项的显示状态"""
        if self.dual_screen.get():
            self.video2_frame.grid()
        else:
            self.video2_frame.grid_remove()
        
        # 更新窗口大小
        self.update_window_size()
    
    def toggle_advanced_options(self):
        """切换高级选项的显示状态"""
        if self.show_advanced.get():
            self.advanced_frame.grid()
            self.toggle_image_prefix()  # 更新图片前缀显示状态
        else:
            self.advanced_frame.grid_remove()
            # 确保图片前缀输入框也被隐藏
            self.image_prefix_label.grid_remove()
            self.image_prefix_entry.grid_remove()
        
        # 更新窗口大小
        self.update_window_size()
    
    def toggle_image_prefix(self):
        """切换图片前缀输入框的显示状态"""
        if self.generate_images.get() and self.show_advanced.get():
            self.image_prefix_label.grid(row=2, column=0, sticky=tk.W, pady=2)
            self.image_prefix_entry.grid(row=2, column=1, sticky=tk.W, padx=5)
        else:
            self.image_prefix_label.grid_remove()
            self.image_prefix_entry.grid_remove()
    
    def update_status(self, message, update_ui=True):
        """更新状态标签"""
        # 限制状态信息的长度，防止UI变化
        if len(message) > 60:
            message = message[:57] + "..."
        
        self.status_label.config(text=message)
        if update_ui:
            # 仅在处理过程中需要更新UI
            self.root.update_idletasks()  # 使用update_idletasks而不是update，避免强制重绘
    
    def get_video_resolution(self, video_path):
        """获取视频分辨率"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return "无法获取"
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            return f"{width}×{height}"
        except Exception as e:
            return "无法获取"
    
    def select_video(self):
        """选择第一个视频文件"""
        filename = filedialog.askopenfilename(
            title="选择视频文件1",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv"), ("所有文件", "*.*")]
        )
        if filename:
            # 如果路径太长，显示文件名而不是完整路径
            display_name = os.path.basename(filename) if len(filename) > 60 else filename
            self.video_path.set(filename)
            
            # 获取并显示分辨率
            resolution = self.get_video_resolution(filename)
            self.resolution1.set(resolution)
            
            # 使用简短的提示信息，避免状态栏过长
            self.update_status(f"已选择视频1: {os.path.basename(filename)} ({resolution})", update_ui=False)
    
    def select_video2(self):
        """选择第二个视频文件"""
        filename = filedialog.askopenfilename(
            title="选择视频文件2",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv"), ("所有文件", "*.*")]
        )
        if filename:
            # 如果路径太长，显示文件名而不是完整路径
            display_name = os.path.basename(filename) if len(filename) > 60 else filename
            self.video_path2.set(filename)
            
            # 获取并显示分辨率
            resolution = self.get_video_resolution(filename)
            self.resolution2.set(resolution)
            
            # 使用简短的提示信息，避免状态栏过长
            self.update_status(f"已选择视频2: {os.path.basename(filename)} ({resolution})", update_ui=False)
    
    def select_output_path(self):
        """选择输出路径"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            # 如果路径太长，显示最后一部分
            if len(directory) > 60:
                parts = directory.split(os.sep)
                if len(parts) > 3:
                    display_dir = os.sep.join(parts[-3:])
                    display_dir = "..." + os.sep + display_dir
                else:
                    display_dir = directory
            else:
                display_dir = directory
                
            self.output_path.set(directory)
            self.update_status(f"输出目录: {display_dir}", update_ui=False)
    
    def clear_all(self):
        """清空所有设置"""
        self.video_path.set("")
        self.video_path2.set("")
        self.output_path.set("")
        self.output_name.set("PicROM")
        self.frame_count.set(50)
        self.frame_count2.set(50)
        self.generate_images.set(False)
        self.image_prefix.set("output")
        self.show_advanced.set(False)  # 重置更多配置选项
        self.dual_screen.set(False)    # 重置双屏选项
        self.progress.set(0)
        
        # 清空分辨率显示
        self.resolution1.set("")
        self.resolution2.set("")
        
        self.toggle_advanced_options()  # 更新UI状态
        self.toggle_dual_screen()       # 更新双屏UI状态
        self.update_status("已清空所有设置", update_ui=False)
    
    def extract_frames_from_video(self, video_path, frame_count, progress_start, progress_end, video_name="视频"):
        """从视频中提取指定数量的帧"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"无法打开{video_name}文件")
        
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps
        
        self.update_status(f"{video_name}信息: 总帧数={total_frames}, FPS={fps:.2f}, 时长={duration:.2f}秒")
        
        # 计算帧间隔
        interval = max(1, total_frames // frame_count)
        frames = []
        frame_indices = []
        
        for i in range(frame_count):
            target_frame = i * interval
            if target_frame >= total_frames:
                break
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            
            if ret:
                # 转换 BGR 到 RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
                frame_indices.append(target_frame)
                
                # 更新进度
                progress_value = progress_start + (i + 1) / frame_count * (progress_end - progress_start)
                self.progress.set(progress_value)
                self.update_status(f"提取{video_name}帧 {i+1}/{frame_count}")
            else:
                self.update_status(f"警告: 无法读取{video_name}帧 {target_frame}")
        
        cap.release()
        return frames, frame_indices
    
    def rgb_to_rgb565(self, rgb_array):
        """将RGB图像转换为RGB565格式（修正字节序）"""
        r = (rgb_array[..., 0] >> 3).astype(np.uint16)
        g = (rgb_array[..., 1] >> 2).astype(np.uint16)
        b = (rgb_array[..., 2] >> 3).astype(np.uint16)
        
        rgb565 = (r << 11) | (g << 5) | b
    
        # 修正：直接返回uint16数组，让struct.pack处理字节序
        return rgb565
    
    def save_frames_as_images(self, frames, output_path, prefix, start_index=0):
        """将帧保存为单独的图片文件"""
        images_dir = os.path.join(output_path, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        saved_files = []
        for i, frame in enumerate(frames):
            # 使用PIL保存图像
            img = Image.fromarray(frame)
            filename = f"{prefix}_{start_index + i + 1:03d}.bmp"
            filepath = os.path.join(images_dir, filename)
            img.save(filepath, "BMP")
            saved_files.append(filepath)
            
            # 更新进度
            progress_value = 70 + (i + 1) / len(frames) * 20  # 保存图片阶段占20%
            self.progress.set(progress_value)
            self.update_status(f"保存图片: {filename}")
        
        return saved_files
    
    def generate_bin_file(self, frames, output_path, output_name):
        """生成二进制文件（修正版本）"""
        bin_path = os.path.join(output_path, f"{output_name}.bin")
        
        with open(bin_path, 'wb') as f:
            # 写入帧数量
            frame_count = len(frames)
            f.write(struct.pack('<I', frame_count))
            
            # 预留偏移量表位置
            offset_table_pos = f.tell()
            f.write(b'\x00' * (frame_count * 4))  # 预留空间
            
            offsets = []
            frame_sizes = []
            
            # 写入每帧数据
            for i, frame in enumerate(frames):
                offsets.append(f.tell())
                
                # 转换为RGB565
                rgb565 = self.rgb_to_rgb565(frame)
                height, width = rgb565.shape
                
                # 计算帧数据大小
                frame_size = width * height * 2
                frame_sizes.append(frame_size)
                
                # 写入RGB565数据 - 使用大端序
                for y in range(height):
                    for x in range(width):
                        pixel = rgb565[y, x]
                        # 确保大端序：高字节在前，低字节在后
                        f.write(struct.pack('>H', pixel))
                
                # 更新进度
                progress_value = 40 + (i + 1) / frame_count * 20
                self.progress.set(progress_value)
                self.update_status(f"生成BIN文件: 处理帧 {i+1}/{frame_count}")
            
            # 写回偏移量表
            f.seek(offset_table_pos)
            for offset in offsets:
                f.write(struct.pack('<I', offset))
            
            # 记录文件信息用于调试
            total_size = f.tell()
            self.update_status(f"BIN文件生成完成，大小: {total_size}字节")
        
        return bin_path
        
    def generate_header_file(self, bin_path, output_path, output_name):
        """生成头文件"""
        header_path = os.path.join(output_path, "images.h")
        bin_name = os.path.basename(bin_path)
        sanitized_name = bin_name.replace('.', '_')
        
        # 读取二进制文件获取帧信息
        with open(bin_path, 'rb') as f:
            frame_count = struct.unpack('<I', f.read(4))[0]
            offsets = []
            for i in range(frame_count):
                offsets.append(struct.unpack('<I', f.read(4))[0])
        
        with open(header_path, 'w', encoding='utf-8') as f:
            f.write(f"""/* Auto-generated image resource header */
#ifndef {sanitized_name.upper()}_H
#define {sanitized_name.upper()}_H

#if defined (__GNUC__) || defined (__CC_ARM)  || defined (__ICCARM__)\t/* 32 bit ARM compiler */\n\n
\t#include <stdint.h>
\t#if defined (__CSRC_USED__)\t\t\t\t\t/* use C source instead of elf obj file */
\t\textern const uint8_t* {sanitized_name}_Data;
\t\t#define SEC_START_ADDR {sanitized_name}_Data
\t#else
\t\textern uint8_t _binary_{sanitized_name}_start;
\t\textern uint32_t _binary_{sanitized_name}_size;\n\n
\t\t#define SEC_START_ADDR &_binary_{sanitized_name}_start
\t#endif\n\n
#else
\t#define SEC_START_ADDR 0
#endif\n\n
""")
            
            # 写入组表定义
            f.write("#define _GROUP_TABLE 0\t\t\t\t//Group Index:0\t\tGroup Name:Group_Table\t Group Type:Unknown \n")
            f.write("#define _GROUP_TABLE_ADDR (SEC_START_ADDR + 0x%08x)\t" % 0)
            f.write("//Group Addr :0x%08x\tGroup Name:Group_Table\t Group Type:Unknown \n\n" % 0)
            
            # 写入帧定义
            for i in range(frame_count):
                frame_name = f"FRAME_{i:04d}"
                f.write("#define _%-30s %d\t\t\t//Frame Index:%d\t\tFrame Name:%s\n" % 
                       (frame_name, i, i, frame_name))
                f.write("#define _%s_ADDR\t\t\t(SEC_START_ADDR + 0x%08x)\t" % 
                       (frame_name, offsets[i]))
                f.write("//Frame Addr :0x%08x\tFrame Name:%s\n\n" % 
                       (offsets[i], frame_name))
            
            f.write(f"\n#endif // {sanitized_name.upper()}_H\n")
        
        return header_path
    
    def start_extraction(self):
        """开始提取和处理"""
        try:
            # 验证输入
            if not self.video_path.get():
                messagebox.showerror("错误", "请选择视频文件1")
                return
            
            if self.dual_screen.get() and not self.video_path2.get():
                messagebox.showerror("错误", "双屏模式下请选择视频文件2")
                return
            
            if not self.output_path.get():
                messagebox.showerror("错误", "请选择输出路径")
                return
            
            frame_count = self.frame_count.get()
            if frame_count <= 0:
                messagebox.showerror("错误", "帧数量必须大于0")
                return
            
            if self.dual_screen.get():
                frame_count2 = self.frame_count2.get()
                if frame_count2 <= 0:
                    messagebox.showerror("错误", "视频2帧数量必须大于0")
                    return
            
            # 创建输出目录
            os.makedirs(self.output_path.get(), exist_ok=True)
            
            self.update_status("开始处理视频...")
            self.progress.set(0)
            
            all_frames = []
            all_frame_indices = []
            
            # 1. 提取第一个视频的帧
            frames1, frame_indices1 = self.extract_frames_from_video(
                self.video_path.get(), 
                frame_count, 
                0, 20,  # 进度范围0-20%
                "视频1"
            )
            
            if not frames1:
                messagebox.showerror("错误", "无法从视频1中提取任何帧")
                return
            
            all_frames.extend(frames1)
            all_frame_indices.extend(frame_indices1)
            
            self.update_status(f"成功提取视频1 {len(frames1)} 帧")
            
            # 2. 如果双屏模式，提取第二个视频的帧
            if self.dual_screen.get():
                frames2, frame_indices2 = self.extract_frames_from_video(
                    self.video_path2.get(), 
                    self.frame_count2.get(), 
                    20, 40,  # 进度范围20-40%
                    "视频2"
                )
                
                if not frames2:
                    messagebox.showerror("错误", "无法从视频2中提取任何帧")
                    return
                
                all_frames.extend(frames2)
                all_frame_indices.extend(frame_indices2)
                
                self.update_status(f"成功提取视频2 {len(frames2)} 帧")
                self.update_status(f"总计提取 {len(all_frames)} 帧")
            
            # 3. 生成BIN文件
            self.progress.set(40)
            bin_path = self.generate_bin_file(all_frames, self.output_path.get(), self.output_name.get())
            self.update_status(f"生成BIN文件: {os.path.basename(bin_path)}")
            
            # 4. 生成头文件
            self.progress.set(60)
            header_path = self.generate_header_file(bin_path, self.output_path.get(), self.output_name.get())
            self.update_status(f"生成头文件: {os.path.basename(header_path)}")
            
            # 5. 如果勾选了生成图片文件，则保存为单独的图片
            if self.generate_images.get():
                self.progress.set(70)
                # 如果双屏模式，从视频1开始编号到视频2结束
                image_files = self.save_frames_as_images(
                    all_frames, self.output_path.get(), self.image_prefix.get()
                )
                self.update_status(f"生成 {len(image_files)} 个图片文件")
            
            # 完成
            self.progress.set(100)
            self.update_status("处理完成！")
            
            # 显示完成信息
            generated_files = []
            if os.path.exists(bin_path):
                generated_files.append(f"  - {os.path.basename(bin_path)}")
            if os.path.exists(header_path):
                generated_files.append(f"  - {os.path.basename(header_path)}")
            if self.generate_images.get():
                generated_files.append(f"  - images/ 目录下的 {len(all_frames)} 个BMP文件")
            
            messagebox.showinfo("完成", 
                f"处理完成！\n"
                f"提取帧数: {len(all_frames)}\n"
                f"生成文件:\n" + "\n".join(generated_files) + 
                f"\n输出目录: {self.output_path.get()}")
                
        except Exception as e:
            self.update_status(f"错误: {str(e)}")
            messagebox.showerror("错误", f"处理过程中发生错误:\n{str(e)}")
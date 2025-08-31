import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps
import os

class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高級圖片處理工具")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 初始化變量
        self.image_path = None
        self.initial_image = None  # 原始未修改的圖片
        self.original_image = None  # 當前處理的圖片
        self.displayed_image = None  # 顯示的圖片
        self.palettes = ["原始色彩", "灰度", "暖色", "冷色", "復古", "黑白", "反轉"]
        self.modes = ["標準模式", "編輯模式", "預覽模式", "分析模式"]
        self.process_options = ["模糊", "銳化", "邊緣增強", "輪廓", "浮雕", "平滑", "細節增強"]
        
        # 創建 UI 框架
        self.create_widgets()
        
        # 初始化狀態
        self.last_canvas_width = 0
        self.last_canvas_height = 0
    
    def create_widgets(self):
        # 創建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)
        
        # 文件操作按鈕
        file_frame = ttk.LabelFrame(control_frame, text="文件操作", padding=5)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="選擇圖片", command=self.select_image, 
                  width=15).pack(fill=tk.X, pady=3)
        ttk.Button(file_frame, text="選擇目錄", command=self.select_directory,
                  width=15).pack(fill=tk.X, pady=3)
        ttk.Button(file_frame, text="保存圖片", command=self.save_image,
                  width=15).pack(fill=tk.X, pady=3)
        
        # 圖片處理按鈕
        process_frame = ttk.LabelFrame(control_frame, text="圖片處理", padding=5)
        process_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(process_frame, text="應用效果", command=self.apply_effect,
                  width=15).pack(fill=tk.X, pady=3)
        
        # 新增確認按鈕
        ttk.Button(process_frame, text="確認處理", command=self.confirm_processing,
                  width=15, style="Accent.TButton").pack(fill=tk.X, pady=3)
        
        ttk.Button(process_frame, text="重置圖片", command=self.reset_image,
                  width=15).pack(fill=tk.X, pady=3)
        
        # 效果選擇
        ttk.Label(process_frame, text="處理效果:").pack(anchor=tk.W, pady=(10, 0))
        self.process_combo = ttk.Combobox(process_frame, values=self.process_options, 
                                        state="readonly", width=13)
        self.process_combo.pack(fill=tk.X, pady=3)
        self.process_combo.current(0)
        
        # 調色盤選擇
        palette_frame = ttk.LabelFrame(control_frame, text="色彩調整", padding=5)
        palette_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(palette_frame, text="調色盤:").pack(anchor=tk.W)
        self.palette_combo = ttk.Combobox(palette_frame, values=self.palettes, 
                                        state="readonly", width=13)
        self.palette_combo.pack(fill=tk.X, pady=3)
        self.palette_combo.current(0)
        self.palette_combo.bind("<<ComboboxSelected>>", self.change_palette)
        
        # 亮度調整
        ttk.Label(palette_frame, text="亮度:").pack(anchor=tk.W, pady=(10, 0))
        self.brightness = tk.DoubleVar(value=1.0)
        ttk.Scale(palette_frame, from_=0.1, to=2.0, variable=self.brightness,
                 command=self.adjust_brightness, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 對比度調整
        ttk.Label(palette_frame, text="對比度:").pack(anchor=tk.W, pady=(10, 0))
        self.contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(palette_frame, from_=0.1, to=2.0, variable=self.contrast,
                 command=self.adjust_contrast, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # 模式選擇
        mode_frame = ttk.LabelFrame(control_frame, text="工作模式", padding=5)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="選擇模式:").pack(anchor=tk.W)
        self.mode_combo = ttk.Combobox(mode_frame, values=self.modes, 
                                      state="readonly", width=13)
        self.mode_combo.pack(fill=tk.X, pady=3)
        self.mode_combo.current(0)
        
        # 右側顯示區域
        display_frame = ttk.LabelFrame(main_frame, text="圖片顯示區域", padding=10)
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=5)
        
        # 圖片畫布
        self.canvas = tk.Canvas(display_frame, bg="#2d2d2d", bd=2, relief=tk.GROOVE)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 綁定畫布大小變化事件
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # 狀態欄
        self.status = ttk.Label(self.root, text="就緒 | 請選擇圖片開始操作", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, padx=10, pady=5)
    
    def select_image(self):
        filetypes = (
            ("圖片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
            ("所有文件", "*.*")
        )
        path = filedialog.askopenfilename(title="選擇圖片", filetypes=filetypes)
        if path:
            self.image_path = path
            try:
                self.initial_image = Image.open(path)  # 保存原始圖片
                self.original_image = self.initial_image.copy()  # 工作圖片
                self.display_image()
                self.status.config(text=f"已載入圖片: {os.path.basename(path)} | 尺寸: {self.original_image.size[0]}x{self.original_image.size[1]}")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法載入圖片: {str(e)}")
    
    def select_directory(self):
        path = filedialog.askdirectory(title="選擇目錄")
        if path:
            self.status.config(text=f"已選擇目錄: {path}")
    
    def save_image(self):
        if not self.displayed_image:
            messagebox.showwarning("警告", "沒有圖片可保存")
            return
            
        filetypes = (
            ("PNG 文件", "*.png"),
            ("JPEG 文件", "*.jpg;*.jpeg"),
            ("BMP 文件", "*.bmp"),
            ("TIFF 文件", "*.tiff"),
            ("所有文件", "*.*")
        )
        path = filedialog.asksaveasfilename(title="保存圖片", filetypes=filetypes, defaultextension=".png")
        if path:
            try:
                # 保存全尺寸圖片
                self.get_fullsize_processed_image().save(path)
                messagebox.showinfo("成功", "圖片保存成功！")
                self.status.config(text=f"圖片已保存至: {path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"保存圖片失敗: {str(e)}")
    
    def display_image(self):
        if not self.original_image:
            return
            
        try:
            # 清除畫布
            self.canvas.delete("all")
            
            # 複製原始圖片進行處理
            img = self.original_image.copy()
            
            # 應用調色盤
            palette = self.palette_combo.get()
            if palette == "灰度":
                img = img.convert("L")
            elif palette == "暖色":
                img = self.apply_warm_filter(img)
            elif palette == "冷色":
                img = self.apply_cool_filter(img)
            elif palette == "復古":
                img = self.apply_vintage_filter(img)
            elif palette == "黑白":
                img = img.convert("1")
            elif palette == "反轉":
                img = ImageOps.invert(img.convert("RGB"))
            
            # 調整亮度
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness.get())
            
            # 調整對比度
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast.get())
            
            # 調整大小以適應畫布
            canvas_width = self.canvas.winfo_width() - 20
            canvas_height = self.canvas.winfo_height() - 20
            
            if canvas_width > 1 and canvas_height > 1:
                img.thumbnail((canvas_width, canvas_height))
            
            # 保存顯示的圖片
            self.displayed_image = img
            
            # 顯示圖片
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.create_image(
                self.canvas.winfo_width() // 2, 
                self.canvas.winfo_height() // 2, 
                anchor=tk.CENTER, 
                image=self.tk_img
            )
            
            # 顯示文件名
            self.canvas.create_text(
                20, 20, 
                anchor=tk.NW, 
                text=os.path.basename(self.image_path),
                fill="white",
                font=("Arial", 10, "bold"),
                stroke_width=2,
                stroke_fill="black"
            )
            
        except Exception as e:
            self.status.config(text=f"錯誤: {str(e)}")
    
    def on_canvas_resize(self, event):
        # 只有在畫布大小實際改變時才重新顯示圖片
        if (event.width != self.last_canvas_width or 
            event.height != self.last_canvas_height):
            self.last_canvas_width = event.width
            self.last_canvas_height = event.height
            if self.image_path:
                self.display_image()
    
    def change_palette(self, event=None):
        if self.image_path:
            self.display_image()
            self.status.config(text=f"已切換調色盤: {self.palette_combo.get()}")
    
    def adjust_brightness(self, value):
        if not self.image_path:
            return
        self.display_image()
        self.status.config(text=f"亮度調整: {float(value):.2f}")
    
    def adjust_contrast(self, value):
        if not self.image_path:
            return
        self.display_image()
        self.status.config(text=f"對比度調整: {float(value):.2f}")
    
    def apply_effect(self):
        """應用選中的圖片處理效果"""
        if not self.image_path:
            messagebox.showwarning("警告", "請先選擇圖片")
            return
            
        effect = self.process_combo.get()
        self.status.config(text=f"應用效果: {effect}")
        
        try:
            # 複製原始圖片進行處理
            img = self.original_image.copy()
            
            # 應用選中的效果
            if effect == "模糊":
                img = img.filter(ImageFilter.BLUR)
            elif effect == "銳化":
                img = img.filter(ImageFilter.SHARPEN)
            elif effect == "邊緣增強":
                img = img.filter(ImageFilter.EDGE_ENHANCE)
            elif effect == "輪廓":
                img = img.filter(ImageFilter.CONTOUR)
            elif effect == "浮雕":
                img = img.filter(ImageFilter.EMBOSS)
            elif effect == "平滑":
                img = img.filter(ImageFilter.SMOOTH)
            elif effect == "細節增強":
                img = img.filter(ImageFilter.DETAIL)
            
            # 更新原始圖片為處理後的圖片
            self.original_image = img
            self.display_image()
            messagebox.showinfo("效果應用", f"已成功應用 {effect} 效果")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"應用效果失敗: {str(e)}")
    
    def confirm_processing(self):
        """確認當前處理結果"""
        if not self.image_path:
            messagebox.showwarning("警告", "請先選擇圖片")
            return
            
        # 將當前處理結果設為新的原始圖片
        self.initial_image = self.original_image.copy()
        self.status.config(text="處理結果已確認！")
        messagebox.showinfo("確認處理", "當前處理結果已確認為新的基準圖片")
    
    def reset_image(self):
        """重置圖片到原始狀態"""
        if not self.image_path:
            return
            
        try:
            # 恢復到最初載入的圖片
            self.original_image = self.initial_image.copy()
            self.brightness.set(1.0)
            self.contrast.set(1.0)
            self.palette_combo.current(0)
            self.display_image()
            self.status.config(text="圖片已重置到初始狀態")
        except Exception as e:
            messagebox.showerror("錯誤", f"重置圖片失敗: {str(e)}")
    
    def get_fullsize_processed_image(self):
        """獲取全尺寸的處理後圖片"""
        if not self.original_image:
            return None
            
        # 複製原始圖片進行處理
        img = self.original_image.copy()
        
        # 應用調色盤
        palette = self.palette_combo.get()
        if palette == "灰度":
            img = img.convert("L")
        elif palette == "暖色":
            img = self.apply_warm_filter(img)
        elif palette == "冷色":
            img = self.apply_cool_filter(img)
        elif palette == "復古":
            img = self.apply_vintage_filter(img)
        elif palette == "黑白":
            img = img.convert("1")
        elif palette == "反轉":
            img = ImageOps.invert(img.convert("RGB"))
        
        # 調整亮度
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(self.brightness.get())
        
        # 調整對比度
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(self.contrast.get())
        
        return img
    
    def apply_warm_filter(self, img):
        # 暖色過濾器
        r, g, b = img.split()
        r = r.point(lambda i: min(i + 30, 255))
        return Image.merge("RGB", (r, g, b))
    
    def apply_cool_filter(self, img):
        # 冷色過濾器
        r, g, b = img.split()
        b = b.point(lambda i: min(i + 30, 255))
        return Image.merge("RGB", (r, g, b))
    
    def apply_vintage_filter(self, img):
        # 復古濾鏡
        r, g, b = img.split()
        r = r.point(lambda i: min(i * 0.9, 255))
        g = g.point(lambda i: min(i * 0.7, 255))
        b = b.point(lambda i: min(i * 0.5, 255))
        return Image.merge("RGB", (r, g, b))

if __name__ == "__main__":
    root = tk.Tk()
    
    # 創建自定義樣式
    style = ttk.Style()
    style.configure("TButton", padding=6)
    style.configure("TLabelFrame", padding=10)
    style.configure("Accent.TButton", background="#4CAF50", foreground="white", font=("Arial", 10, "bold"))
    
    # 設置主題 (如果系統支持)
    try:
        root.tk.call("source", "sun-valley.tcl")
        root.tk.call("set_theme", "light")
    except:
        pass
    
    app = ImageViewerApp(root)
    root.mainloop()
import tkinter as tk
from tkinter import messagebox
def button_click(button_name):
    """更新輸入欄位為當前按鈕名稱"""
    if button_name is "M2" or button_name is "M4":
        entry_var.set("輸入更新區域")
    if button_name is "確認":
        print("")
        process_text()

def process_text():
    """獲取輸入欄位文字並進行處理"""
    input_text = entry.get().strip()  # 獲取並清除前後空白
    
    if not input_text:
        messagebox.showinfo("訊息", "輸入欄位為空！")
        return
    
    # 這裡可以添加任何自定義處理邏輯
    processed_text = f"處理結果: {input_text.upper()} (長度: {len(input_text)})"
    
    # 顯示處理結果
    messagebox.showinfo("處理完成", processed_text)
    
    # 清空輸入欄位（可選）
    entry_var.set("")


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
    text="確認",
    width=15,
    height=2,
    command=lambda n=name: button_click(n)  # 綁定按鈕名稱
)
confirm_btn.pack(pady=15)

# 運行主循環
root.mainloop()
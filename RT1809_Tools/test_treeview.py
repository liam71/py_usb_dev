import os

def check_project_structure():
    """检查项目结构"""
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    
    # 检查 RT1809_Tools 目录
    rt1809_dir = os.path.join(current_dir, 'RT1809_Tools')
    if os.path.exists(rt1809_dir):
        print(f"RT1809_Tools 目录: {rt1809_dir}")
        print("RT1809_Tools 目录内容:")
        for item in os.listdir(rt1809_dir):
            item_path = os.path.join(rt1809_dir, item)
            if os.path.isdir(item_path):
                print(f"  目录: {item}")
                for sub_item in os.listdir(item_path):
                    print(f"    - {sub_item}")
            else:
                print(f"  文件: {item}")
    else:
        print("RT1809_Tools 目录不存在")
    
    # 检查 Isp_bin 目录
    isp_bin_dir = os.path.join(rt1809_dir, 'Isp_bin')
    if os.path.exists(isp_bin_dir):
        print(f"\nIsp_bin 目录: {isp_bin_dir}")
        print("Isp_bin 目录内容:")
        for item in os.listdir(isp_bin_dir):
            print(f"  - {item}")
    else:
        print(f"\nIsp_bin 目录不存在: {isp_bin_dir}")

if __name__ == "__main__":
    check_project_structure()
import os
import sys
import ctypes

def setup_local_libusb():
    """设置使用本地libusb DLL"""
    
    print("=== 使用本地libusb DLL ===")
    
    # 检查DLL文件是否存在
    dll_paths = [
        "libusb-1.0.dll",  # 当前目录
        os.path.join(os.getcwd(), "libusb-1.0.dll"),
    ]
    
    dll_path = None
    for path in dll_paths:
        if os.path.exists(path):
            dll_path = os.path.abspath(path)
            print(f"找到DLL文件: {dll_path}")
            break
    
    if not dll_path:
        print("错误: 未找到libusb-1.0.dll文件")
        print("请将libusb-1.0.dll文件放在当前目录:")
        print(f"当前目录: {os.getcwd()}")
        return False
    
    # 方法1: 设置环境变量
    os.environ['PATH'] = os.path.dirname(dll_path) + ';' + os.environ.get('PATH', '')
    
    # 方法2: 显式加载DLL
    try:
        # 先尝试直接加载DLL验证其有效性
        libusb_dll = ctypes.CDLL(dll_path)
        print("✓ DLL文件加载成功")
        
        # 检查是否是有效的libusb DLL
        if hasattr(libusb_dll, 'libusb_init'):
            print("✓ 是有效的libusb DLL")
        else:
            print("⚠ 警告: DLL可能不是有效的libusb库")
            
    except Exception as e:
        print(f"✗ DLL加载失败: {e}")
        return False
    
    return True

def test_usb_with_local_libusb():
    """使用本地libusb测试USB设备"""
    
    if not setup_local_libusb():
        return
    
    try:
        # 导入usb库
        import usb.core
        import usb.backend.libusb1 as libusb1
        
        print("\n=== 测试USB设备检测 ===")
        
        # 方法1: 让pyusb自动查找（应该能找到我们设置的DLL）
        print("方法1: 自动查找后端...")
        try:
            devices = list(usb.core.find(find_all=True))
            print(f"✓ 自动查找: 找到 {len(devices)} 个设备")
            for i, dev in enumerate(devices):
                print(f"  设备{i+1}: VID: 0x{dev.idVendor:04x}, PID: 0x{dev.idProduct:04x}")
        except Exception as e:
            print(f"✗ 自动查找失败: {e}")
        
        # 方法2: 显式指定后端
        print("\n方法2: 显式指定后端...")
        try:
            backend = libusb1.get_backend()
            if backend:
                devices = list(usb.core.find(find_all=True, backend=backend))
                print(f"✓ 显式指定: 找到 {len(devices)} 个设备")
            else:
                print("✗ 无法创建后端")
        except Exception as e:
            print(f"✗ 显式指定失败: {e}")
            
        # 方法3: 强制指定DLL路径
        print("\n方法3: 强制指定DLL路径...")
        try:
            backend = libusb1.get_backend(find_library=lambda x: "libusb-1.0.dll")
            if backend:
                devices = list(usb.core.find(find_all=True, backend=backend))
                print(f"✓ 强制指定路径: 找到 {len(devices)} 个设备")
            else:
                print("✗ 强制指定路径失败")
        except Exception as e:
            print(f"✗ 强制指定路径失败: {e}")
            
    except ImportError as e:
        print(f"✗ 导入错误: {e}")
        print("请确保已安装pyusb: pip install pyusb")
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_usb_with_local_libusb()
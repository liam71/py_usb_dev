"""辅助工具函数"""

import os
import sys
from typing import Optional


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径，支持打包后的exe文件
    
    Args:
        relative_path: 相对路径
        
    Returns:
        绝对路径
    """
    try:
        # 打包后的exe文件
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    else:
        return f"{size_bytes/(1024*1024):.2f} MB"


def validate_firmware_file(file_path: str, expected_size: Optional[int] = None) -> bool:
    """
    验证固件文件
    
    Args:
        file_path: 文件路径
        expected_size: 期望的文件大小
        
    Returns:
        是否验证通过
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        file_size = os.path.getsize(file_path)
        
        if expected_size and file_size != expected_size:
            return False
            
        # 可以添加更多的验证逻辑，如文件头校验等
        return True
        
    except Exception:
        return False
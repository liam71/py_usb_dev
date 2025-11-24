"""主程序入口"""

import sys
import os

# 添加当前目录到路径，确保模块导入正常
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rt1809_tools_config import USE_GUI, APP_model_, OTA, OTA_RES
from rt1809_tools_gui import MainApplication


def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    #USE_GUI = True
    
    if USE_GUI and APP_model_ in [OTA, OTA_RES]:
        app = MainApplication(get_resource_path)
        app.run()
    else:
        # 命令行模式（保留原有功能）
        print("命令行模式暂未实现")
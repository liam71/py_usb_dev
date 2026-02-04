from example_control import usb_control_transfer

def GetPanelNumber():
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x82,
            wIndex=0x0000,
            data_or_wLength=1
        )
        print("PanelNumber :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelNumber Fail: {str(e)}")
        return 0  # 返回默认值

def GetPanelSize(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x81,
            wIndex=wIndex,
            data_or_wLength=4
        )
        print("Size :", device_desc)
        return device_desc
    except Exception as e:
        print(f"GetPanelSize Fail: {str(e)}")
        return None  # 返回None，调用处需要检查

def GetPanelDirect(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x84,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("res :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelDirect Fail: {str(e)}")
        return 0  # 返回默认值

def GetPanelShape(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x83,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("PanelShape :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelShape Fail: {str(e)}")
        return 0  # 返回默认值

def GetPanelState(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x91,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("PanelState :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelState Fail: {str(e)}")
        return 0  # 返回默认值（0表示未就绪）

def GetPanelProcessState(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x92,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("ProcessState :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelProcessState Fail: {str(e)}")
        return 0  # 返回默认值

def SetSelectPanel(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0x40,
            bRequest=0x50,
            wValue=0x02,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("res:", device_desc)
    except Exception as e:
        print(f"SetSelectPanel fail: {str(e)}")

def SetCmdKeyAndCiphertext(data : bytes):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0x40,
            bRequest=0x50,
            wValue=0x01,
            wIndex=0x0001,
            data_or_wLength=data
        )
        print("res:", device_desc)
    except Exception as e:
        print(f"SetCmdKeyAndCiphertext: {str(e)}")

def GetPanelSourceState(wIndex = 0):
    try:
        device_desc = usb_control_transfer(
            vid=0x34C7,
            pid=0x8888,
            bmRequestType=0xC0,
            bRequest=0xA0,
            wValue=0x93,
            wIndex=wIndex,
            data_or_wLength=1
        )
        print("GetPanelSourceState :", device_desc)
        return device_desc[0] 
    except Exception as e:
        print(f"GetPanelSourceState Fail: {str(e)}")  # 修复错误消息
        return 0  # 返回默认值（0表示未就绪）
"""ISP烧录器实现"""

import os
import sys
import time
import struct
from typing import Optional, Callable

from rt1809_tools_config import ISPConfig, Command, Response
from rt1809_tools_isp_protocol import SerialProtocol
from rt1809_tools_isp_crc import CRCCalculator


class ISPProgrammer:
    """ISP烧录器 - 增加数据稳定性"""
    
    def __init__(self, log_callback: Optional[Callable] = None, address_callback: Optional[Callable] = None, get_resource_path_func = None):
        """
        初始化ISP烧录器
        
        Args:
            log_callback: 日志回调函数
            address_callback: 地址显示回调函数
        """
        self.protocol = SerialProtocol()
        self.config = ISPConfig()
        self.log_callback = log_callback
        self.address_callback = address_callback
        self.firmware_data: Optional[bytes] = None
        self.firmware_size: int = 0
        self.cancel_flag = False
        # 使用传入的资源路径获取函数，如果未传入则使用默认方法（向后兼容）
        if get_resource_path_func is not None:
            self.get_resource_path = get_resource_path_func
        else:
            # 如果没有传入，则使用原来的方法（可能不准确，但保持兼容）
            self.get_resource_path = self._default_get_resource_path

    def _default_get_resource_path(self, relative_path):
        """默认的资源路径获取方法（与setup_icon使用相同的逻辑）"""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    
    '''
    def get_resource_path(self, relative_path):
        """
        获取资源文件的绝对路径，兼容开发环境和打包环境
        完全使用第一个程序（ota_isp_tool.py）的方式
        """
        if getattr(sys, 'frozen', False):
            # 打包后的环境 - 使用sys._MEIPASS获取临时解压目录
            base_path = sys._MEIPASS
        else:
            # 开发环境 - 使用当前文件所在目录（与第一个程序完全相同）
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        full_path = os.path.join(base_path, relative_path)
        return full_path
    '''
    def cancel(self):
        '''设置取消标志'''
        self.cancel_flag = True
        self.log("正在取消操作...", "WARNING")
        # 立即尝试关闭串口，中断正在进行的操作
        try:
            if self.protocol.serial_port and self.protocol.serial_port.is_open:
                self.protocol.serial_port.cancel_read()  # 取消正在进行的读操作
                self.protocol.serial_port.cancel_write()  # 取消正在进行的写操作
        except:
            pass
    
    def is_cancelled(self):
        '''检查是否已取消'''
        return self.cancel_flag

    def reset(self):
        """重置编程器状态"""
        self.cancel_flag = False
        self.firmware_data = None
        self.firmware_size = 0
        try:
            self.protocol.close_port()
        except:
            pass
        
    def log(self, message: str, level: str = "INFO"):
        """
        输出日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        #self.log(log_msg)
        if self.log_callback:
            self.log_callback(log_msg)
    
    def validate_packet_checksum(self, packet: bytes) -> bool:
        """
        验证数据包校验和
        
        Returns:
            校验和是否正确
        """
        if len(packet) < 12:  # 最小包长度
            return False
            
        # 提取数据部分（不包括最后的4字节校验和）
        data_part = packet[:-4]
        
        # 提取校验和
        received_checksum = struct.unpack('<I', packet[-4:])[0]
        
        # 计算校验和
        calculated_checksum = 0
        for byte in data_part:
            calculated_checksum = (calculated_checksum + byte) & 0xFFFFFFFF
            
        return calculated_checksum == received_checksum
    
    def send_with_retry(self, packet: bytes, max_retries: int = 3, operation_name: str = "发送") -> bool:
        """
        带重试的数据发送
        
        Args:
            packet: 数据包
            max_retries: 最大重试次数
            operation_name: 操作名称，用于日志
            
        Returns:
            是否发送成功
        """
        for attempt in range(max_retries):
            # 发送前延时，避免连续发送过快
            if attempt > 0:
                time.sleep(0.01 * attempt)  # 递增延时
                
            # 发送数据
            if self.protocol.send_data(packet):
                self.log(f"{operation_name}尝试 {attempt+1}/{max_retries} 成功", "INFO")
                return True
                
        self.log(f"{operation_name}失败，已达最大重试次数", "ERROR")
        return False
    
    def receive_with_timeout_and_retry(self, length: int, timeout: float = 0.5, max_retries: int = 2, 
                                     operation_name: str = "接收") -> Optional[bytes]:
        """
        带超时和重试的数据接收
        
        Returns:
            接收到的数据
        """
        for attempt in range(max_retries):
            # 接收数据
            data = self.protocol.receive_data(length, timeout)
            
            if data is not None:
                self.log(f"{operation_name}尝试 {attempt+1}/{max_retries} 成功", "INFO")
                return data
            else:
                # 重试前清空输入缓冲区
                if self.protocol.serial_port and self.protocol.serial_port.is_open:
                    self.protocol.serial_port.reset_input_buffer()
                
        self.log(f"{operation_name}失败，请检查串口连接", "ERROR")
        return None
    
    def update_address_display(self, operation: str, address: int):
        """
        更新地址显示
        
        Args:
            operation: 操作类型 (Verify/Erase/Program)
            address: 地址值
        """
        if self.address_callback:
            address_text = f"{operation} 0x{address:08X}"  # 格式化为"Verify 0x00000000"
            self.address_callback(address_text)
    
    def load_firmware(self, file_path: str) -> bool:
        """
        加载固件文件
        
        Args:
            file_path: 固件文件路径
            
        Returns:
            是否加载成功
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.log(f"固件文件不存在: {file_path}", "ERROR")
                return False
                
            with open(file_path, 'rb') as f:
                self.firmware_data = f.read()
                self.firmware_size = len(self.firmware_data)
                self.log(f"固件加载成功，大小: {self.firmware_size} bytes")
                return True
        except Exception as e:
            self.log(f"加载固件失败: {e}", "ERROR")
            return False
    
    def start_isp_mode(self, port: str) -> bool:
        """
        启动ISP模式 - 使用与第一个程序相同的简单方式
        """
        # 添加调试信息
        cmd_path = self.get_resource_path(self.config.ISP_CMD_FILE)
        driver_path = self.get_resource_path(self.config.ISP_DRIVER_FILE)


        try:
            # 步骤1: 38400波特率，发送0x00
            self.log("步骤1: 初始化ISP模式...")
            if not self.protocol.open_port(port, self.config.INITIAL_BAUDRATE):
                return False
            
            self.protocol.send_data(b'\x00')
            time.sleep(0.001)
            
            # 步骤2: 发送ISP_WriterCMD.bin - 使用简单直接的方式
            self.log("步骤2: 发送ISP_WriterCMD...")
            isp_cmd_path = self.get_resource_path(self.config.ISP_CMD_FILE)
            
            # 直接检查文件是否存在
            if not os.path.exists(isp_cmd_path):
                self.log(f"ISP命令文件不存在: {isp_cmd_path}", "ERROR")
                return False
                
            with open(isp_cmd_path, 'rb') as f:
                cmd_data = f.read(39)
                self.protocol.send_data(cmd_data)
            
            self.protocol.close_port()
            
            # 步骤3: 115200波特率，等待回传
            self.log("步骤3: 等待IC响应...")
            if not self.protocol.open_port(port, self.config.ISP_BAUDRATE):
                return False
            
            # 步骤4: 发送ISP_DriverCode.bin前256字节
            self.log("步骤4: 发送ISP驱动代码前256字节...")
            isp_driver_path = self.get_resource_path(self.config.ISP_DRIVER_FILE)
            
            # 直接检查文件是否存在
            if not os.path.exists(isp_driver_path):
                self.log(f"ISP驱动文件不存在: {isp_driver_path}", "ERROR")
                return False
                
            with open(isp_driver_path, 'rb') as f:
                driver_data = f.read()
            
            self.protocol.send_data(driver_data[:256])
            
            # 等待CodeSize
            code_size_data = self.protocol.receive_data(4, 1)
            if code_size_data != b'\x0E\x1D\x00\x00':
                self.log(f"请检查串口连接，[CodeSize: {code_size_data.hex() if code_size_data else 'None'}]", "ERROR")
                return False
            
            # 步骤5: 发送剩余数据
            self.log("步骤5: 发送剩余ISP驱动代码...")
            code_size = 0x1D0E
            self.protocol.send_data(driver_data[256:256+code_size])
            
            # 等待Checksum
            checksum_data = self.protocol.receive_data(4, 1)
            if checksum_data != b'\xD4\x13\x06\x00':
                self.log(f"请关闭弹窗后重试[Checksum: {checksum_data.hex() if checksum_data else 'None'}]", "ERROR")
                return False
            
            self.log("成功进入ISP模式", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"进入ISP模式失败: {e}", "ERROR")
            return False
    
    def check_id(self) -> bool:
        """
        检查设备ID
        
        Returns:
            是否检查成功
        """
        self.log("检查设备ID...")
        address = self.firmware_size - 1  # 固件尾地址
        packet = self.protocol.build_request_packet(
            Command.CHECK_ID,
            address,
            self.config.DEVICE_ID
        )
        
        # 验证数据包校验和
        if not self.validate_packet_checksum(packet):
            self.log("数据包校验和错误", "ERROR")
            return False
            
        # 使用稳定性优化的发送方法
        if not self.send_with_retry(packet, 3, "检查设备ID"):
            return False
            
        response = self.receive_with_timeout_and_retry(1, 2, 2, "接收设备ID响应")
        
        if response is None:
            self.log("设备ID验证失败: 无响应", "ERROR")
            return False
            
        response_byte = response[0]
        
        if response_byte == Response.ACK:
            self.log("设备ID验证成功", "SUCCESS")
            return True
        else:
            self.log(f"设备ID验证失败: 0x{response_byte:02X}", "ERROR")
            return False
    
    def set_baudrate(self, new_baudrate: int) -> bool:
        """
        设置新波特率
        
        Args:
            new_baudrate: 新波特率
            
        Returns:
            是否设置成功
        """
        self.log(f"设置波特率为 {new_baudrate}...")
        
        # 计算波特率参数
        baudrate_param = 98304000 // (16 * new_baudrate)
        data = struct.pack('<H', baudrate_param)
        
        packet = self.protocol.build_request_packet(
            Command.BAUDRATE,
            0,  # 任意地址
            data
        )
        
        # 验证数据包校验和
        if not self.validate_packet_checksum(packet):
            self.log("数据包校验和错误", "ERROR")
            return False
            
        # 使用稳定性优化的发送方法
        if not self.send_with_retry(packet, 3, "设置波特率"):
            return False
        
        # 保存当前串口名称
        current_port = self.protocol.current_port_name
        
        # 切换波特率
        time.sleep(0.1)
        self.protocol.close_port()
        if not self.protocol.open_port(current_port, new_baudrate):
            self.log(f"无法以新波特率 {new_baudrate} 打开串口", "ERROR")
            return False
        
        # 不等待响应，直接返回成功
        return True
    
    def verify_block(self, block_address: int, block_size: int, max_retries=3) -> Optional[bool]:
        """
        验证数据块 - 优化时间间隔和稳定性
        """
        self.update_address_display("Verify", block_address)
        
        # 获取块数据
        block_end = min(block_address + block_size, self.firmware_size)
        block_data = self.firmware_data[block_address:block_end]

        # 计算CRC
        code_checksum = CRCCalculator.calculate_block_checksum(block_data)

        # 构建Verify请求 - 固定使用8字节数据长度
        data = struct.pack('<II', len(block_data), code_checksum)
        
        # 确保数据为8字节
        if len(data) != 8:
            if len(data) < 8:
                data = data + b'\x00' * (8 - len(data))
        
        # 构建数据包
        packet = self.protocol.build_request_packet(
            Command.VERIFY,
            block_address,
            data,
            data_len=8  # 固定为8字节
        )
        
        # 验证数据包校验和
        if not self.validate_packet_checksum(packet):
            self.log("数据包校验和错误", "ERROR")
            return None
        
        for retry_count in range(max_retries):
            # 使用稳定性优化的发送方法
            if not self.send_with_retry(packet, 2, f"验证块 0x{block_address:08X}"):
                continue
                
            # 使用稳定性优化的接收方法
            response = self.receive_with_timeout_and_retry(1, 1, 2, f"接收验证响应")
            
            if response is None:
                continue
                
            response_byte = response[0]
            
            if response_byte == Response.ACK:
                return True
            elif response_byte == Response.CODE_CHECKSUM_FAIL:
                return False
            elif response_byte == Response.CHECKSUM_FAIL:
                if retry_count < max_retries - 1:
                    time.sleep(0.02)  # 减少重试间隔
            elif response_byte is None:
                if retry_count < max_retries - 1:
                    time.sleep(0.02)  # 减少重试间隔
            else:
                return None
        
        self.log(f"验证失败 @ 0x{block_address:08X}", "ERROR")
        return None
    
    def erase_block(self, block_address: int, max_retries=2) -> bool:
        """
        擦除数据块 - 优化时间间隔和稳定性
        """
        self.log(f"擦除块 0x{block_address:08X}...")
        self.update_address_display("Erase", block_address)

        # 构建数据包
        packet = self.protocol.build_request_packet(
            Command.BLOCK_ERASE,
            block_address,
            b'',
            data_len=0  # 明确指定长度为0
        )
        
        # 验证数据包校验和
        if not self.validate_packet_checksum(packet):
            self.log("数据包校验和错误", "ERROR")
            return False

        for retry_count in range(max_retries):
            # 使用稳定性优化的发送方法
            if not self.send_with_retry(packet, 2, f"擦除块 0x{block_address:08X}"):
                continue
                
            # 使用稳定性优化的接收方法
            response = self.receive_with_timeout_and_retry(1, 3, 2, f"接收擦除响应")  # 减少等待时间
            
            if response is None:
                continue
                
            response_byte = response[0]
        
            if response_byte == Response.ACK:
                self.log(f"块 0x{block_address:08X} 擦除成功", "SUCCESS")
                return True
            elif response_byte == Response.CHECKSUM_FAIL:
                if retry_count < max_retries - 1:
                    time.sleep(0.05)  # 减少重试间隔
            elif response_byte is None:
                if retry_count < max_retries - 1:
                    time.sleep(0.05)  # 减少重试间隔
            else:
                self.log(f"擦除失败: 0x{response_byte:08X}:校验重试次数用尽", "ERROR")
                return False
    
    def program_block(self, block_address: int, block_size: int, progress_callback=None, max_retries=2) -> bool:
        """
        编程数据块 - 优化时间间隔和稳定性
        """
        self.log(f"编程块 0x{block_address:08X}...")
        self.update_address_display("Program", block_address)
        
        # 按2KB为单位编程
        for offset in range(0, block_size, self.config.PROGRAM_SIZE):
            # 检查取消标志
            if self.is_cancelled():
                self.log("编程被取消", "WARNING")
                return False
            program_address = block_address + offset
            
            # 检查是否超出固件范围
            if program_address >= self.firmware_size:
                break
            
            # 获取编程数据
            data_end = min(program_address + self.config.PROGRAM_SIZE, self.firmware_size)
            program_data = self.firmware_data[program_address:data_end]
            
            # 补齐到2KB
            if len(program_data) < self.config.PROGRAM_SIZE:
                program_data += b'\xFF' * (self.config.PROGRAM_SIZE - len(program_data))
            
            # 构建数据包
            packet = self.protocol.build_request_packet(
                Command.PROGRAM,
                program_address,
                program_data
            )
            
            # 验证数据包校验和
            if not self.validate_packet_checksum(packet):
                self.log("数据包校验和错误", "ERROR")
                return False
            
            # 重试机制 - 优化时间间隔
            success = False
            for retry_count in range(max_retries):
                # 使用稳定性优化的发送方法
                if not self.send_with_retry(packet, 2, f"编程块 0x{program_address:08X}"):
                    continue
                    
                # 使用稳定性优化的接收方法
                response = self.receive_with_timeout_and_retry(1, 1, 2, f"接收编程响应")  # 减少等待时间
                
                if response is None:
                    continue
                    
                response_byte = response[0]
                
                if response_byte == Response.ACK:
                    success = True
                    break  # 成功，跳出重试循环
                elif response_byte == Response.CHECKSUM_FAIL:
                    if retry_count == max_retries - 1:
                        time.sleep(0.05)  # 减少重试间隔
                elif response_byte is None:
                    if retry_count == max_retries - 1:
                        time.sleep(0.05)  # 减少重试间隔
                else:
                    self.log(f"编程失败 @ 0x{program_address:08X}: 0x{response_byte:02X}", "ERROR")
                    return False
            
            if not success:
                return False
            
            # 更新进度
            if progress_callback:
                progress = (program_address + self.config.PROGRAM_SIZE) * 100 // self.firmware_size
                progress_callback(progress)
        
        self.log(f"块 0x{block_address:08X} 编程成功", "SUCCESS")
        return True
    
    def exit_isp_mode(self) -> bool:
        """
        退出ISP模式
        
        Returns:
            是否成功退出
        """
        self.log("退出ISP模式...")
        
        packet = self.protocol.build_request_packet(
            Command.EXIT_ISP_MODE,
            0,
            b''
        )
        
        # 验证数据包校验和
        if not self.validate_packet_checksum(packet):
            self.log("数据包校验和错误", "ERROR")
            return False
            
        # 使用稳定性优化的发送方法
        if not self.send_with_retry(packet, 3, "退出ISP模式"):
            return False
            
        response = self.receive_with_timeout_and_retry(1, 2, 2, "接收退出ISP模式响应")
        
        if response is None:
            self.log(f"退出ISP模式失败: 无响应", "ERROR")
            return False
            
        response_byte = response[0]
        
        if response_byte == Response.ACK:
            self.log("成功退出ISP模式", "SUCCESS")
            return True
        else:
            self.log(f"退出ISP模式失败: 0x{response_byte:02X}", "ERROR")
            return False
    
    def burn_firmware(self, port: str, firmware_path: str, progress_callback=None) -> bool:
        """
        烧录固件主流程 - 全局稳定性控制
        """
        try:
            # 打开串口
            if not self.protocol.open_port(port, self.config.INITIAL_BAUDRATE):
                return False

            # 检查是否取消
            if self.is_cancelled():
                self.log("操作已取消", "WARNING")
                return False
            
            # 增加初始化延时
            time.sleep(0.1)
            
            # 加载固件
            if not self.load_firmware(firmware_path):
                return False

            # 检查是否取消
            if self.is_cancelled():
                self.log("操作已取消", "WARNING")
                return False
            
            # 进入ISP模式
            if not self.start_isp_mode(port):
                return False

            # 检查是否取消
            if self.is_cancelled():
                self.log("操作已取消", "WARNING")
                return False
            
            # 检查设备ID
            if not self.check_id():
                return False
            
            # 设置高速波特率
            if not self.set_baudrate(self.config.NEW_BAUDRATE):
                return False
            
            # 按块处理固件
            total_blocks = (self.firmware_size + self.config.BLOCK_SIZE - 1) // self.config.BLOCK_SIZE
            
            for block_num in range(total_blocks):
                if self.is_cancelled():
                    self.log("操作已被用户取消", "WARNING")
                    # 尝试退出ISP模式
                    try:
                        self.exit_isp_mode()
                    except:
                        pass
                    return False

                # 在块处理之间增加小延时
                if block_num > 0:
                    time.sleep(0.001)
                    
                block_address = block_num * self.config.BLOCK_SIZE
                
                # 验证块
                verify_result = self.verify_block(block_address, self.config.BLOCK_SIZE, max_retries=3)
                
                if verify_result is None:
                    return False
                elif verify_result is False:
                    # 需要更新
                    if not self.erase_block(block_address, max_retries=3):
                        return False
                    
                    # 擦除后增加延时
                    time.sleep(0.01)
                    
                    if not self.program_block(block_address, self.config.BLOCK_SIZE, progress_callback, max_retries=3):
                        self.log(f"烧录过程出错：设备可能已断开连接，请检查", "ERROR")
                        return False
                
                # 更新总进度
                if progress_callback:
                    total_progress = (block_num + 1) * 100 // total_blocks
                    progress_callback(total_progress)
            
            # 退出ISP模式
            if not self.exit_isp_mode():
                return False
            
            self.log("固件烧录成功！", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"烧录过程出错: {e}", "ERROR")
            return False
        finally:
            self.protocol.close_port()
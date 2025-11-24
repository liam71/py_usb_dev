"""串口通信协议实现"""

import struct
import time
from typing import Optional
import serial
import serial.tools.list_ports

from rt1809_tools_config import ISPConfig, Command


class SerialProtocol:
    """串口通讯协议实现 - 优化稳定性"""
    
    def __init__(self):
        """初始化串口协议"""
        self.serial_port: Optional[serial.Serial] = None
        self.config = ISPConfig()
        self.current_port_name: str = ""
        
    def open_port(self, port: str, baudrate: int) -> bool:
        """
        打开串口 - 优化稳定性参数
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1,
                write_timeout=1,  # 增加写超时
                inter_byte_timeout=0.1,  # 字节间超时
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            # 清空缓冲区
            if self.serial_port.is_open:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
            self.current_port_name = port
            return True
        except Exception as e:
            print(f"打开串口失败: {e}")
            return False
    
    def close_port(self):
        """关闭串口"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
    
    def send_data(self, data: bytes) -> bool:
        """
        发送数据 - 增加稳定性措施
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                # 发送前清空输出缓冲区
                self.serial_port.reset_output_buffer()
                
                # 分段发送数据，每段之间增加小延时
                chunk_size = 2048  # 每次发送的字节数
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i+chunk_size]
                    self.serial_port.write(chunk)
                    self.serial_port.flush()  # 等待所有数据写入
                    time.sleep(0.0001)  # 小延时，避免缓冲区溢出
                    
                return True
            return False
        except Exception as e:
            print(f"发送数据失败: {e}")
            return False
    
    def receive_data(self, length: int, timeout: float = 1) -> Optional[bytes]:
        """
        接收数据 - 增加稳定性措施
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                # 设置超时
                original_timeout = self.serial_port.timeout
                self.serial_port.timeout = timeout
                
                # 接收数据
                data = bytearray()
                start_time = time.time()
                
                while len(data) < length and (time.time() - start_time) < timeout:
                    # 计算还需要接收的字节数
                    remaining = length - len(data)
                    
                    # 尝试接收数据
                    chunk = self.serial_port.read(remaining)
                    if chunk:
                        data.extend(chunk)
                    
                    # 短暂延时，避免过度占用CPU
                    if len(data) < length:
                        time.sleep(0.001)
                
                # 恢复原始超时设置
                self.serial_port.timeout = original_timeout
                
                return bytes(data) if len(data) == length else None
            return None
        except Exception as e:
            print(f"接收数据失败: {e}")
            return None
    
    def build_request_packet(self, command: int, address: int, data: bytes = b'', data_len: Optional[int] = None) -> bytes:
        """
        构建请求包 - 严格按照字段字节数规定
        
        数据包结构:
        - Start Code (1字节)
        - Command (1字节) 
        - Address (4字节，小端)
        - DataLen (2字节，小端，表示后面Data的长度)
        - Data (n字节)
        - Checksum (4字节，小端)
        
        Args:
            command: 命令字节 (1字节)
            address: 地址 (4字节)
            data: 数据 (n字节)
            data_len: 可选的2字节数据长度，如果为None则使用len(data)
            
        Returns:
            完整的请求包
        """
        # 验证和调整各字段的字节数
        packet = bytearray()
        
        # 1. Start Code (1字节)
        if not (0 <= self.config.START_CODE <= 0xFF):
            raise ValueError(f"Start Code必须在0-255范围内，当前值: {self.config.START_CODE}")
        packet.append(self.config.START_CODE)
        
        # 2. Command (1字节)
        if not (0 <= command <= 0xFF):
            raise ValueError(f"Command必须在0-255范围内，当前值: {command}")
        packet.append(command)
        
        # 3. Address (4字节，小端)
        if not (0 <= address <= 0xFFFFFFFF):
            raise ValueError(f"Address必须在0-4294967295范围内，当前值: {address}")
        packet.extend(struct.pack('<I', address))  # 小端4字节
        
        # 4. DataLen (2字节，小端)
        if data_len is None:
            data_len = len(data)
        
        if not (0 <= data_len <= 0xFFFF):
            raise ValueError(f"DataLen必须在0-65535范围内，当前值: {data_len}")
        packet.extend(struct.pack('<H', data_len))  # 小端2字节
        
        # 5. Data (n字节)
        # 如果实际数据长度与声明的DataLen不符，进行调整
        actual_data_len = len(data)
        if actual_data_len != data_len:
            if actual_data_len < data_len:
                # 数据不足，填充0x00
                data = data + b'\x00' * (data_len - actual_data_len)
            else:
                # 数据过长，截断
                data = data[:data_len]
                print(f"警告: 数据被截断，从{actual_data_len}字节到{data_len}字节")
        
        packet.extend(data)
        
        # 6. Checksum (4字节，小端)
        checksum = 0
        for byte in packet:
            checksum = (checksum + byte) & 0xFFFFFFFF  # 限制为32位无符号整数
        
        packet.extend(struct.pack('<I', checksum))  # 小端4字节
        
        return bytes(packet)
    
    def wait_for_response(self, timeout: float = 2) -> Optional[int]:
        """
        等待IC应答
        
        Args:
            timeout: 超时时间
            
        Returns:
            应答码
        """
        response = self.receive_data(1, timeout)
        if response:
            return response[0]
        return None
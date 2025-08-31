import struct
import binascii
import os
from collections import namedtuple
from datetime import datetime

class BinaryFileEditor:
    """二进制文件编辑器，支持读取、修改和写入二进制文件"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_size = 0
        self.data = bytearray()
        self.header = {}
        self.sections = []
        
        if os.path.exists(file_path):
            self.load_file()
    
    def load_file(self):
        """加载二进制文件"""
        try:
            with open(self.file_path, 'rb') as f:
                self.data = bytearray(f.read())
                self.file_size = len(self.data)
                print(f"文件已加载: {self.file_path}, 大小: {self.file_size} 字节")
        except Exception as e:
            print(f"加载文件错误: {str(e)}")
            self.data = bytearray()
            self.file_size = 0
    
    def save_file(self, new_path=None):
        """保存二进制文件"""
        save_path = new_path or self.file_path
        try:
            with open(save_path, 'wb') as f:
                f.write(self.data)
            print(f"文件已保存: {save_path}, 大小: {len(self.data)} 字节")
            return True
        except Exception as e:
            print(f"保存文件错误: {str(e)}")
            return False
    
    def read_bytes(self, offset, length):
        """从指定偏移量读取字节"""
        if offset < 0 or offset + length > len(self.data):
            raise ValueError("读取超出文件范围")
        return bytes(self.data[offset:offset+length])
    
    def write_bytes(self, offset, new_data):
        """在指定偏移量写入字节"""
        if offset < 0 or offset > len(self.data):
            raise ValueError("写入偏移量无效")
        
        end = offset + len(new_data)
        if end > len(self.data):
            # 扩展数据数组
            self.data.extend(b'\x00' * (end - len(self.data)))
        
        # 写入数据
        self.data[offset:end] = new_data
    
    def parse_header(self, header_format):
        """
        解析文件头
        header_format: 格式字符串列表，如:
            [('magic', '4s'), ('version', 'H'), ('entries', 'I'), ('checksum', 'I')]
        """
        self.header = {}
        pos = 0
        
        for name, fmt in header_format:
            # 计算格式大小
            size = struct.calcsize(fmt)
            
            # 读取数据
            data = self.read_bytes(pos, size)
            
            # 解包数据
            value = struct.unpack(fmt, data)[0]
            
            # 处理字节串
            if isinstance(value, bytes):
                try:
                    # 尝试UTF-8解码
                    decoded = value.decode('utf-8').rstrip('\x00')
                    self.header[name] = decoded
                except UnicodeDecodeError:
                    # 保留十六进制表示
                    self.header[name] = binascii.hexlify(value).decode('utf-8')
            else:
                self.header[name] = value
            
            pos += size
        
        return self.header
    
    def add_section(self, section_type, data, offset=None):
        """
        添加新分区
        section_type: 分区类型 (2字节整数)
        data: 分区数据 (字节串)
        offset: 指定位置插入 (None表示追加到文件末尾)
        """
        # 创建分区头
        section_header = struct.pack('<H', section_type)  # 2字节类型
        section_header += struct.pack('<I', len(data))    # 4字节长度
        
        # 创建完整分区
        section_data = section_header + data
        
        # 确定写入位置
        if offset is None:
            offset = len(self.data)
        
        # 写入数据
        self.write_bytes(offset, section_data)
        
        return offset
    
    def find_pattern(self, pattern, start_offset=0):
        """
        在文件中查找字节模式
        pattern: 要查找的字节模式 (bytes)
        start_offset: 开始搜索的位置
        """
        pattern = bytes(pattern)
        data = bytes(self.data)
        
        offset = start_offset
        while offset < len(data):
            index = data.find(pattern, offset)
            if index == -1:
                return None
            yield index
            offset = index + 1
    
    def hex_dump(self, start_offset=0, length=128, bytes_per_line=16):
        """以十六进制格式显示文件内容"""
        end_offset = min(start_offset + length, len(self.data))
        data = self.data[start_offset:end_offset]
        
        print(f"十六进制转储 (偏移量 0x{start_offset:08X} - 0x{end_offset:08X}):")
        print("-" * 78)
        
        for i in range(0, len(data), bytes_per_line):
            # 计算当前行偏移量
            offset = start_offset + i
            
            # 获取当前行数据
            chunk = data[i:i+bytes_per_line]
            
            # 创建十六进制字符串
            hex_str = ' '.join(f"{b:02X}" for b in chunk)
            
            # 创建ASCII表示
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            
            # 打印行
            print(f"0x{offset:08X}: {hex_str.ljust(3*bytes_per_line)}  |{ascii_str}|")
        
        print("-" * 78)
    
    def calculate_checksum(self, start=0, end=None):
        """计算数据校验和"""
        if end is None:
            end = len(self.data)
        data = self.data[start:end]
        return binascii.crc32(data)
    
    def modify_byte(self, offset, value):
        """修改单个字节"""
        if offset < 0 or offset >= len(self.data):
            raise ValueError("偏移量超出文件范围")
        self.data[offset] = value & 0xFF
    
    def modify_int(self, offset, value, size=4, byteorder='little'):
        """修改整数"""
        if offset < 0 or offset + size > len(self.data):
            raise ValueError("偏移量超出文件范围")
        
        # 转换为字节
        int_bytes = value.to_bytes(size, byteorder)
        
        # 写入数据
        self.data[offset:offset+size] = int_bytes
    
    def insert_data(self, offset, new_data):
        """在指定位置插入数据"""
        if offset < 0 or offset > len(self.data):
            raise ValueError("插入偏移量无效")
        
        # 创建新数据数组
        new_buffer = bytearray(self.data)
        
        # 插入新数据
        new_buffer[offset:offset] = new_data
        
        # 更新数据
        self.data = new_buffer
    
    def delete_data(self, offset, length):
        """删除指定位置的数据"""
        if offset < 0 or offset + length > len(self.data):
            raise ValueError("删除范围超出文件")
        
        # 创建新数据数组
        new_buffer = bytearray(self.data)
        
        # 删除指定范围
        del new_buffer[offset:offset+length]
        
        # 更新数据
        self.data = new_buffer


# =============================================================================
# 使用示例
# =============================================================================

def main():
    # 创建示例二进制文件
    sample_file = "1809_bin/GPCM2_CM3_strip_Trans.bin"
    
    # 文件头格式: [魔数(4s), 版本(H), 条目数(I), 校验和(I)]
    header_data = struct.pack('<4sHII', b'BIN\x01', 0x0101, 3, 0)
    
    # 三个数据分区
    sections = [
        struct.pack('<HIf', 1, 0x12345678, 3.14159),  # 类型1: ID, 值, PI
        struct.pack('<HId', 2, 0xDEADBEEF, 2.71828),  # 类型2: ID, 值, e
        struct.pack('<HI16s', 3, 0xCAFEBABE, b'Hello, Binary!')  # 类型3: ID, 值, 消息
    ]
    
    # 创建文件内容
    file_content = header_data
    # for section in sections:
    #     # 添加分区头: 类型(H) + 长度(I)
    #     section_header = struct.pack('<HI', 1 if file_content == header_data else 2, len(section))
    #     file_content += section_header + section
    
    # 写入文件
    with open(sample_file, 'wb') as f:
        f.write(file_content)
    
    print(f"已创建示例文件: {sample_file} ({len(file_content)} 字节)")
    
    # =========================================================================
    # 使用BinaryFileEditor操作二进制文件
    # =========================================================================
    
    # 创建编辑器实例
    editor = BinaryFileEditor(sample_file)
    
    # 解析文件头
    header_format = [
        ('magic', '4s'),
        ('version', 'H'),
        ('entries', 'I'),
        ('checksum', 'I')
    ]
    header = editor.parse_header(header_format)
    print("\n文件头信息:")
    for key, value in header.items():
        print(f"  {key:>10}: {value} ({type(value).__name__})")
    
    # 显示十六进制转储
    print("\n文件前128字节的十六进制转储:")
    editor.hex_dump(0, 128)
    
    # 查找特定模式
    print("\n查找模式 'BIN\\x01':")
    for offset in editor.find_pattern(b'BIN\x01'):
        print(f"  在偏移量 0x{offset:08X} 处找到模式")
    
    # 添加新分区
    new_section_data = b'This is a new section added by Python!'
    new_offset = editor.add_section(4, new_section_data)
    print(f"\n添加新分区，类型: 4, 大小: {len(new_section_data)} 字节, 偏移量: 0x{new_offset:08X}")
    
    # 修改文件内容
    try:
        # 修改版本号 (偏移量4，2字节)
        editor.modify_int(4, 0x0202, size=2)
        print("修改版本号: 0x0101 -> 0x0202")
        
        # 修改第一个分区中的浮点数
        # 头(14字节) + 分区头(6字节) + 类型(2) + ID(4) = 偏移量26
        editor.modify_byte(26, 0x88)  # 修改ID部分
        print("修改第一个分区的ID字节")
        
        # 在文件开头插入数据
        editor.insert_data(0, b'HEADER_START')
        print("在文件开头插入 'HEADER_START'")
        
    except Exception as e:
        print(f"修改错误: {str(e)}")
    
    # 显示修改后的十六进制转储
    print("\n修改后的十六进制转储:")
    editor.hex_dump(0, 128)
    
    # 保存修改后的文件
    modified_file = "output_bin/modified.bin"
    if editor.save_file(modified_file):
        print(f"\n修改后的文件已保存为: {modified_file}")
        
        # 显示原始文件和修改后文件的大小
        orig_size = os.path.getsize(sample_file)
        mod_size = os.path.getsize(modified_file)
        print(f"原始大小: {orig_size} 字节, 修改后大小: {mod_size} 字节, 差异: {mod_size - orig_size} 字节")

def mc_main():
    input_file = "1809_bin/GPCM2_CM3_strip_Trans.bin"
    output_file = "output_bin/modified.bin"

    binaryfileeditor_m = BinaryFileEditor(input_file)

    # 修改文件内容
    try:
        # 在文件开头插入数据
        binaryfileeditor_m.insert_data(0, b'CM3X')
        print("在文件开头插入 'CM3X'")
        
    except Exception as e:
        print(f"修改错误: {str(e)}")

        # 显示修改后的十六进制转储
    print("\n修改后的十六进制转储:")
    binaryfileeditor_m.hex_dump(0, 512)

    if binaryfileeditor_m.save_file(output_file):
        print(f"\n修改后的文件已保存为: {output_file}")
        
        # 显示原始文件和修改后文件的大小
        orig_size = os.path.getsize(input_file)
        mod_size = os.path.getsize(output_file)
        print(f"原始大小: {orig_size} 字节, 修改后大小: {mod_size} 字节, 差异: {mod_size - orig_size} 字节")
if __name__ == "__main__":
    #main()
    mc_main()
    # with open("1809_bin/GPCM2_CM3_strip_Trans.bin", "rb") as f:
    #     data = f.read()
    # print(data)
    file_size = os.path.getsize("1809_bin/GPCM2_CM3_strip_Trans.bin")
    data_list = []
    data_list_len = int(file_size / 2048)
    data_list_pa_len = 2048

    with open("1809_bin/GPCM2_CM3_strip_Trans.bin", "rb") as f:
        for i in range(0 , data_list_len):
            data_list.append(f.read(data_list_pa_len))
    d_header = data_list[0][0:4] 
    print(f"data list len : {data_list_len} data list pa len : {data_list_pa_len}")
    checksum = 0
    count = 0;
    for i in range(0, data_list_len):
        for j in range(0, data_list_pa_len):
            checksum += data_list[i][j]
            count += 1
    byte_array = bytearray(struct.pack('>I', checksum))
    test2_array = bytearray(checksum.to_bytes(8, "little"))
    print(f"checksum : {checksum} byte_array : {byte_array}")
    test1 = 0
    for k in range(0, 10):
        print(data_list[0][k])
        test1 += data_list[0][k]
    test1_array = bytearray(struct.pack('>i', 12345))
    print(f"checksum : {test1} byte_array : {test1_array}")
    
    print(test2_array)
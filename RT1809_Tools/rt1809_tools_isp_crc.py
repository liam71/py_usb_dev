"""CRC校验计算器"""


class CRCCalculator:
    """CRC校验计算器 - 使用查找表优化性能"""
    
    # CRC查找表（类变量，只初始化一次）
    _crc_table_16bit = None
    _crc_table_8bit = None
    
    @classmethod
    def _init_crc_table_16bit(cls):
        """初始化16位查找表（65536个条目）"""
        if cls._crc_table_16bit is not None:
            return
            
        cls._crc_table_16bit = [0] * 65536
        
        # 为每个可能的16位输入值预计算CRC
        for i in range(65536):
            cls._crc_table_16bit[i] = cls._calculate_crc_for_word(i)
    
    @classmethod
    def _calculate_crc_for_word(cls, word):
        """计算单个16位字的CRC贡献（初始CRC为0）"""
        lfsr_c = [0] * 32
        data_in = [0] * 16
        
        # 初始化data_in数组
        for i in range(16):
            data_in[i] = (word >> i) & 0x01
        
        # 使用原始算法的异或逻辑（当dw_pre_crc=0时）
        lfsr_c[0] = data_in[0] ^ data_in[6] ^ data_in[9] ^ data_in[10] ^ data_in[12]
        lfsr_c[1] = data_in[0] ^ data_in[1] ^ data_in[6] ^ data_in[7] ^ data_in[9] ^ data_in[11] ^ data_in[12] ^ data_in[13]
        lfsr_c[2] = data_in[0] ^ data_in[1] ^ data_in[2] ^ data_in[6] ^ data_in[7] ^ data_in[8] ^ data_in[9] ^ data_in[13] ^ data_in[14]
        lfsr_c[3] = data_in[1] ^ data_in[2] ^ data_in[3] ^ data_in[7] ^ data_in[8] ^ data_in[9] ^ data_in[10] ^ data_in[14] ^ data_in[15]
        lfsr_c[4] = data_in[0] ^ data_in[2] ^ data_in[3] ^ data_in[4] ^ data_in[6] ^ data_in[8] ^ data_in[11] ^ data_in[12] ^ data_in[15]
        lfsr_c[5] = data_in[0] ^ data_in[1] ^ data_in[3] ^ data_in[4] ^ data_in[5] ^ data_in[6] ^ data_in[7] ^ data_in[10] ^ data_in[13]
        lfsr_c[6] = data_in[1] ^ data_in[2] ^ data_in[4] ^ data_in[5] ^ data_in[6] ^ data_in[7] ^ data_in[8] ^ data_in[11] ^ data_in[14]
        lfsr_c[7] = data_in[0] ^ data_in[2] ^ data_in[3] ^ data_in[5] ^ data_in[7] ^ data_in[8] ^ data_in[10] ^ data_in[15]
        lfsr_c[8] = data_in[0] ^ data_in[1] ^ data_in[3] ^ data_in[4] ^ data_in[8] ^ data_in[10] ^ data_in[11] ^ data_in[12]
        lfsr_c[9] = data_in[1] ^ data_in[2] ^ data_in[4] ^ data_in[5] ^ data_in[9] ^ data_in[11] ^ data_in[12] ^ data_in[13]
        lfsr_c[10] = data_in[0] ^ data_in[2] ^ data_in[3] ^ data_in[5] ^ data_in[9] ^ data_in[13] ^ data_in[14]
        lfsr_c[11] = data_in[0] ^ data_in[1] ^ data_in[3] ^ data_in[4] ^ data_in[9] ^ data_in[12] ^ data_in[14] ^ data_in[15]
        lfsr_c[12] = data_in[0] ^ data_in[1] ^ data_in[2] ^ data_in[4] ^ data_in[5] ^ data_in[6] ^ data_in[9] ^ data_in[12] ^ data_in[13] ^ data_in[15]
        lfsr_c[13] = data_in[1] ^ data_in[2] ^ data_in[3] ^ data_in[5] ^ data_in[6] ^ data_in[7] ^ data_in[10] ^ data_in[13] ^ data_in[14]
        lfsr_c[14] = data_in[2] ^ data_in[3] ^ data_in[4] ^ data_in[6] ^ data_in[7] ^ data_in[8] ^ data_in[11] ^ data_in[14] ^ data_in[15]
        lfsr_c[15] = data_in[3] ^ data_in[4] ^ data_in[5] ^ data_in[7] ^ data_in[8] ^ data_in[9] ^ data_in[12] ^ data_in[15]
        lfsr_c[16] = data_in[0] ^ data_in[4] ^ data_in[5] ^ data_in[8] ^ data_in[12] ^ data_in[13]
        lfsr_c[17] = data_in[1] ^ data_in[5] ^ data_in[6] ^ data_in[9] ^ data_in[13] ^ data_in[14]
        lfsr_c[18] = data_in[2] ^ data_in[6] ^ data_in[7] ^ data_in[10] ^ data_in[14] ^ data_in[15]
        lfsr_c[19] = data_in[3] ^ data_in[7] ^ data_in[8] ^ data_in[11] ^ data_in[15]
        lfsr_c[20] = data_in[4] ^ data_in[8] ^ data_in[9] ^ data_in[12]
        lfsr_c[21] = data_in[5] ^ data_in[9] ^ data_in[10] ^ data_in[13]
        lfsr_c[22] = data_in[0] ^ data_in[9] ^ data_in[11] ^ data_in[12] ^ data_in[14]
        lfsr_c[23] = data_in[0] ^ data_in[1] ^ data_in[6] ^ data_in[9] ^ data_in[13] ^ data_in[15]
        lfsr_c[24] = data_in[1] ^ data_in[2] ^ data_in[7] ^ data_in[10] ^ data_in[14]
        lfsr_c[25] = data_in[2] ^ data_in[3] ^ data_in[8] ^ data_in[11] ^ data_in[15]
        lfsr_c[26] = data_in[0] ^ data_in[3] ^ data_in[4] ^ data_in[6] ^ data_in[10]
        lfsr_c[27] = data_in[1] ^ data_in[4] ^ data_in[5] ^ data_in[7] ^ data_in[11]
        lfsr_c[28] = data_in[2] ^ data_in[5] ^ data_in[6] ^ data_in[8] ^ data_in[12]
        lfsr_c[29] = data_in[3] ^ data_in[6] ^ data_in[7] ^ data_in[9] ^ data_in[13]
        lfsr_c[30] = data_in[4] ^ data_in[7] ^ data_in[8] ^ data_in[10] ^ data_in[14]
        lfsr_c[31] = data_in[5] ^ data_in[8] ^ data_in[9] ^ data_in[11] ^ data_in[15]
        
        # 组合CRC值
        crc = 0
        for i in range(31, -1, -1):
            crc <<= 1
            crc |= (lfsr_c[i] & 0x01)
        
        return crc
    
    @classmethod
    def _init_crc_table_8bit(cls):
        """初始化8位查找表（256个条目，更节省内存）"""
        if cls._crc_table_8bit is not None:
            return
            
        cls._crc_table_8bit = [[0] * 256 for _ in range(2)]
        
        # 为低字节和高字节分别建立查找表
        for i in range(256):
            # 低字节表（word的低8位）
            cls._crc_table_8bit[0][i] = cls._calculate_crc_for_word(i)
            # 高字节表（word的高8位）
            cls._crc_table_8bit[1][i] = cls._calculate_crc_for_word(i << 8)
    
    @staticmethod
    def crc_checksum_16bit_table(w_value: int, dw_pre_crc: int) -> int:
        """
        使用16位查表法计算CRC
        
        Args:
            w_value: 16位输入值
            dw_pre_crc: 前一个CRC值
            
        Returns:
            计算后的CRC值
        """
        # 确保查找表已初始化
        if CRCCalculator._crc_table_16bit is None:
            CRCCalculator._init_crc_table_16bit()
        
        # 查表获取w_value对应的CRC贡献
        crc_from_data = CRCCalculator._crc_table_16bit[w_value & 0xFFFF]
        
        # 处理前一个CRC值的贡献（需要对原始CRC进行线性变换）
        crc_from_prev = CRCCalculator._process_prev_crc(dw_pre_crc)
        
        # 组合两个CRC贡献
        return crc_from_data ^ crc_from_prev
    
    @staticmethod
    def _process_prev_crc(dw_pre_crc: int) -> int:
        """处理前一个CRC值的线性变换"""
        lfsr_q = [0] * 32
        lfsr_c = [0] * 32
        
        # 初始化lfsr_q数组
        for i in range(32):
            lfsr_q[i] = (dw_pre_crc >> i) & 0x01
        
        # 只包含lfsr_q的异或运算部分
        lfsr_c[0] = lfsr_q[16] ^ lfsr_q[22] ^ lfsr_q[25] ^ lfsr_q[26] ^ lfsr_q[28]
        lfsr_c[1] = lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[25] ^ lfsr_q[27] ^ lfsr_q[28] ^ lfsr_q[29]
        lfsr_c[2] = lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[25] ^ lfsr_q[29] ^ lfsr_q[30]
        lfsr_c[3] = lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[25] ^ lfsr_q[26] ^ lfsr_q[30] ^ lfsr_q[31]
        lfsr_c[4] = lfsr_q[16] ^ lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[22] ^ lfsr_q[24] ^ lfsr_q[27] ^ lfsr_q[28] ^ lfsr_q[31]
        lfsr_c[5] = lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[26] ^ lfsr_q[29]
        lfsr_c[6] = lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[27] ^ lfsr_q[30]
        lfsr_c[7] = lfsr_q[16] ^ lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[21] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[26] ^ lfsr_q[31]
        lfsr_c[8] = lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[24] ^ lfsr_q[26] ^ lfsr_q[27] ^ lfsr_q[28]
        lfsr_c[9] = lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[25] ^ lfsr_q[27] ^ lfsr_q[28] ^ lfsr_q[29]
        lfsr_c[10] = lfsr_q[16] ^ lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[21] ^ lfsr_q[25] ^ lfsr_q[29] ^ lfsr_q[30]
        lfsr_c[11] = lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[25] ^ lfsr_q[28] ^ lfsr_q[30] ^ lfsr_q[31]
        lfsr_c[12] = lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[22] ^ lfsr_q[25] ^ lfsr_q[28] ^ lfsr_q[29] ^ lfsr_q[31]
        lfsr_c[13] = lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[21] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[26] ^ lfsr_q[29] ^ lfsr_q[30]
        lfsr_c[14] = lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[27] ^ lfsr_q[30] ^ lfsr_q[31]
        lfsr_c[15] = lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[25] ^ lfsr_q[28] ^ lfsr_q[31]
        lfsr_c[16] = lfsr_q[0] ^ lfsr_q[16] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[24] ^ lfsr_q[28] ^ lfsr_q[29]
        lfsr_c[17] = lfsr_q[1] ^ lfsr_q[17] ^ lfsr_q[21] ^ lfsr_q[22] ^ lfsr_q[25] ^ lfsr_q[29] ^ lfsr_q[30]
        lfsr_c[18] = lfsr_q[2] ^ lfsr_q[18] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[26] ^ lfsr_q[30] ^ lfsr_q[31]
        lfsr_c[19] = lfsr_q[3] ^ lfsr_q[19] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[27] ^ lfsr_q[31]
        lfsr_c[20] = lfsr_q[4] ^ lfsr_q[20] ^ lfsr_q[24] ^ lfsr_q[25] ^ lfsr_q[28]
        lfsr_c[21] = lfsr_q[5] ^ lfsr_q[21] ^ lfsr_q[25] ^ lfsr_q[26] ^ lfsr_q[29]
        lfsr_c[22] = lfsr_q[6] ^ lfsr_q[16] ^ lfsr_q[25] ^ lfsr_q[27] ^ lfsr_q[28] ^ lfsr_q[30]
        lfsr_c[23] = lfsr_q[7] ^ lfsr_q[16] ^ lfsr_q[17] ^ lfsr_q[22] ^ lfsr_q[25] ^ lfsr_q[29] ^ lfsr_q[31]
        lfsr_c[24] = lfsr_q[8] ^ lfsr_q[17] ^ lfsr_q[18] ^ lfsr_q[23] ^ lfsr_q[26] ^ lfsr_q[30]
        lfsr_c[25] = lfsr_q[9] ^ lfsr_q[18] ^ lfsr_q[19] ^ lfsr_q[24] ^ lfsr_q[27] ^ lfsr_q[31]
        lfsr_c[26] = lfsr_q[10] ^ lfsr_q[16] ^ lfsr_q[19] ^ lfsr_q[20] ^ lfsr_q[22] ^ lfsr_q[26]
        lfsr_c[27] = lfsr_q[11] ^ lfsr_q[17] ^ lfsr_q[20] ^ lfsr_q[21] ^ lfsr_q[23] ^ lfsr_q[27]
        lfsr_c[28] = lfsr_q[12] ^ lfsr_q[18] ^ lfsr_q[21] ^ lfsr_q[22] ^ lfsr_q[24] ^ lfsr_q[28]
        lfsr_c[29] = lfsr_q[13] ^ lfsr_q[19] ^ lfsr_q[22] ^ lfsr_q[23] ^ lfsr_q[25] ^ lfsr_q[29]
        lfsr_c[30] = lfsr_q[14] ^ lfsr_q[20] ^ lfsr_q[23] ^ lfsr_q[24] ^ lfsr_q[26] ^ lfsr_q[30]
        lfsr_c[31] = lfsr_q[15] ^ lfsr_q[21] ^ lfsr_q[24] ^ lfsr_q[25] ^ lfsr_q[27] ^ lfsr_q[31]
        
        # 组合CRC值
        crc = 0
        for i in range(31, -1, -1):
            crc <<= 1
            crc |= (lfsr_c[i] & 0x01)
        
        return crc
    
    @staticmethod
    def calculate_block_checksum(data: bytes) -> int:
        """
        使用查表法计算数据块的CRC校验值
        
        Args:
            data: 待计算的数据
            
        Returns:
            CRC校验值
        """
        crc_value = 0
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                word = data[i] | (data[i + 1] << 8)
            else:
                word = data[i]
            crc_value = CRCCalculator.crc_checksum_16bit_table(word, crc_value)
        return crc_value
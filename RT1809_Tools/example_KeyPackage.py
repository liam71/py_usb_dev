import struct

class KeyPackage:
    def __init__(self, header, cmd, payload, tail):
        self.header = header      # 1 byte
        self.cmd = cmd            # 1 byte
        self.payload = payload    # 4 bytes (list of 4 int)
        self.checksum = 0         # placeholder
        self.tail = tail          # 1 byte

    def to_bytes(self):
        # 組合資料為 bytes，checksum 暫時放 0
        return struct.pack(
            "BB4sBB",
            self.header,
            self.cmd,
            bytes(self.payload),
            self.checksum,
            self.tail
        )

    def calculate_checksum(self):
        data = bytearray(self.to_bytes())
        checksum_index = 6  # checksum 在第 6 個 byte（0-based）
        checksum = 0
        for i in range(len(data)):
            if i != checksum_index:
                checksum ^= data[i]
        self.checksum = checksum
        return checksum

    def to_bytes_with_checksum(self):
        # 計算後填入正確 checksum
        self.calculate_checksum()
        return struct.pack(
            "BB4sBB",
            self.header,
            self.cmd,
            bytes(self.payload),
            self.checksum,
            self.tail
        )
    
if __name__ == "__main__":
    print("This is Main")
    pkg = KeyPackage(
    header=0xAA,
    cmd=0x01,
    payload=[0x10, 0x20, 0x30, 0x40],
    tail=0x55
)

    checksum = pkg.calculate_checksum()
    print(f"Calculated checksum: 0x{checksum:02X}")

    raw_data = pkg.to_bytes_with_checksum()
    print("封包 bytes:", raw_data.hex(' '))

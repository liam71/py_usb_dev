import ctypes
import os
import platform
from ctypes import c_uint8, c_int, Structure, POINTER, byref, cast, create_string_buffer

BASE_X = 1234
BASE_Y = 7755

# 定义 ECPoint 结构体 (匹配 C++ 中的定义)
class ECPoint(Structure):
    _fields_ = [
        ('x', c_int),
        ('y', c_int),
        ('inf', c_int)  # 无穷远点标志 (0 表示有限点，1 表示无穷远点)
    ]
    
    def __init__(self, x=0, y=0, inf=0):
        super().__init__()
        self.x = x
        self.y = y
        self.inf = inf
        
    def __str__(self):
        if self.inf:
            return "ECPoint(INFINITY)"
        return f"ECPoint(x={self.x}, y={self.y})"

# 加载加密库
def load_crypto_library():
    system = platform.system()
    if system == "Windows":
        lib_name = "RacerTech_RT1809_SDK.dll"
    elif system == "Darwin":  # macOS
        lib_name = "RacerTech_RT1809_SDK.dylib"
    else:  # Linux
        lib_name = "RacerTech_RT1809_SDK.so"
    
    # 尝试从当前目录加载
    lib_path = os.path.join(os.path.dirname(__file__), lib_name)
    
    try:
        lib = ctypes.CDLL(lib_path)
        print(f"Successfully loaded crypto library from: {lib_path}")
        return lib
    except OSError:
        # 尝试系统路径
        try:
            lib = ctypes.CDLL(lib_name)
            print(f"Successfully loaded crypto library from system path")
            return lib
        except OSError as e:
            raise ImportError(f"Failed to load crypto library. Tried: {lib_path} and system path") from e

# 加载库
crypto = load_crypto_library()

# 定义函数原型
crypto.ecies_decrypt.restype = None
crypto.ecies_decrypt.argtypes = [
    POINTER(c_uint8),  # ciphertext (int数组)
    c_int,           # len (元素个数)
    POINTER(c_uint8)   # out_plain (int数组)
]

crypto.ecies_encrypt.restype = None
crypto.ecies_encrypt.argtypes = [
    POINTER(c_uint8),  # plaintext (int数组)
    c_int,           # len (元素个数)
    POINTER(c_uint8)   # out_cipher (int数组)
]

crypto.ec_scalar_mul.restype = ECPoint
crypto.ec_scalar_mul.argtypes = [ECPoint, c_int]

crypto.config_key_function.restype = None
crypto.config_key_function.argtypes = [
    c_int
]

# 封装为更Pythonic的接口
class CryptoLib:
    @staticmethod
    def ecies_encrypt(plaintext: bytes) -> tuple[ bytes]:
        """
        ECIES 加密
    
        :param plaintext: 要加密的明文
        :param pub_key: 公钥
        :return: 元组 (R点, 密文)
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")
    
        # 准备输入缓冲区
        plaintext_buffer = (c_uint8 * len(plaintext))()
        for i, byte in enumerate(plaintext):
            plaintext_buffer[i] = byte
    
        # 准备输出变量
        out_R = ECPoint()
        # 密文长度与明文相同（XOR加密）
        out_cipher_buffer = (c_uint8 * len(plaintext))()
    
        # 调用加密函数
        crypto.ecies_encrypt(
            plaintext_buffer,
            len(plaintext),
            out_cipher_buffer
        )
    
        # 转换为字节 - 这是关键修复！！！
        ciphertext = bytes(bytearray(out_cipher_buffer))
        return  ciphertext
    
    @staticmethod
    def ecies_decrypt(ciphertext: bytes) -> bytes:
        """
        ECIES 解密
    
        :param ciphertext: 要解密的密文
        :param priv_key: 私钥 (标量)
        :param R: R点
        :return: 解密后的明文
        """
        if not ciphertext:
            raise ValueError("Ciphertext cannot be empty")
    
        # 准备输入缓冲区
        ciphertext_buffer = (c_uint8 * len(ciphertext))()
        for i, byte in enumerate(ciphertext):
            ciphertext_buffer[i] = byte
    
        # 准备输出缓冲区
        plaintext_buffer = (c_uint8 * len(ciphertext))()
    
        # 调用解密函数
        crypto.ecies_decrypt(
            ciphertext_buffer,
            len(ciphertext),
            plaintext_buffer
        )
    
        # 转换为字节 - 这是关键修复！！！
        return bytes(bytearray(plaintext_buffer))
    
    @staticmethod
    def ec_scalar_mul(G: ECPoint, k: int) -> ECPoint:
        """
        椭圆曲线标量乘法
        
        :param G: 基点
        :param k: 标量
        :return: 结果点
        """
        return crypto.ec_scalar_mul(G, k)
    
    @staticmethod
    def config_key_function(value):
        """
        椭圆曲线标量乘法
        
        :param G: 基点
        :param k: 标量
        :return: 结果点
        """
        crypto.config_key_function(value)

def test_fun(priv:int) -> tuple[bool, ECPoint]:
    # priv_key_int = priv 
    # G = ECPoint(BASE_X, BASE_Y, 0);
    # device_pub_key = CryptoLib.ec_scalar_mul(G , priv_key_int)
    CryptoLib.config_key_function(priv)
    #device_pub_key = CryptoLib.get_pub_ecpoint()
    #device_pub_key = ECPoint(x=2, y=2, inf=0)  
    # ECIES 加密
    plaintext = [79, 75, 49, 50, 51, 52]  # "Hello!" 的ASCII值
    print(f"\nOriginal plaintext: {plaintext} ({bytes(plaintext).decode()})")
    
    ciphertext = CryptoLib.ecies_encrypt(plaintext)
    print(f"Ciphertext: {ciphertext}")
    
    # ECIES 解密
    #priv_key_int = 1234  # 示例私钥（整数）
    decrypted = CryptoLib.ecies_decrypt(ciphertext)
    print(f"\nDecrypted: {decrypted} ({bytes(decrypted).decode()})")
    flag = True
    for i in range(len(decrypted)):
        if plaintext[i] != decrypted[i]:
            flag = False
    return flag


'''
    plaintext = b"OK1234"
    print(f"\nOriginal plaintext: {plaintext} (bytes: {list(plaintext)})")
    
    R, ciphertext = CryptoLib.ecies_encrypt(plaintext, pub_key)
    print(f"Encryption R point: {R}")
    print(f"Ciphertext (hex): {ciphertext.hex()}")
    print(f"Ciphertext (bytes): {list(ciphertext)}")
    
    # 注意：在实际实现中，私钥应该是整数标量
    # 这里仅作演示（实际应用中需要将字节私钥转换为标量）
    priv_key_scalar = int.from_bytes(priv_key[:4], 'big')
    print(f"Using private key scalar: {priv_key_scalar}")
    
    # ECIES 解密
    decrypted = CryptoLib.ecies_decrypt(ciphertext, priv_key_scalar, R)
    print(f"\nDecrypted text: {decrypted.decode()}")
    print(f"Decrypted bytes: {list(decrypted)}")
'''
# 测试代码
if __name__ == "__main__":
    # CryptoLib.config_key_function(1)
    # priv_key_int = 8286 
    # G = ECPoint(BASE_X, BASE_Y, 0);
    # device_pub_key = CryptoLib.ec_scalar_mul(G , priv_key_int)
    # #device_pub_key = CryptoLib.get_pub_ecpoint()
    # #device_pub_key = ECPoint(x=2, y=2, inf=0)  
    # # ECIES 加密
    # plaintext = [79, 75, 49, 50, 51, 52]  # "Hello!" 的ASCII值
    # print(f"\nOriginal plaintext: {plaintext} ({bytes(plaintext).decode()})")
    # print(f"Encryption pub key point: {device_pub_key}")
    # R, ciphertext = CryptoLib.ecies_encrypt(plaintext, device_pub_key)
    # print(f"Encryption R point: {R}")
    # print(f"Ciphertext: {ciphertext}")
    
    # # ECIES 解密
    # #priv_key_int = 8489  # 示例私钥（整数）
    # decrypted = CryptoLib.ecies_decrypt(ciphertext, priv_key_int, R)
    # print(f"\nDecrypted: {decrypted} ({bytes(decrypted).decode()})")
    # flag = True
    # for i in range(len(decrypted)):
    #     if plaintext[i] != decrypted[i]:
    #         flag = False
    # if flag:
    #     print("Suceesc")
    ans_list = []
    ECPoint_list = []
    not_rep = []
    for prv in range(1234, 8888):
        flag= test_fun(prv)
        if flag == True:
            ans_list.append(prv)

    #print(len(ans_list) == len(ECPoint_list))
    pass_list = [1234,1285,1487,2623,3764,3803,4252,4428,4691,4818,5241,5525,6772,8359,8489,8286]
    pass_ans_list = []
    # for ecp in range(len(ECPoint_list)):
    #     print(f"",ecp , ECPoint_list[ecp] , ans_list[ecp])
    for prv in pass_list:
        flag = test_fun(prv)
        if flag == True:
            pass_ans_list.append(1)
        else:
            pass_ans_list.append(0)
    print(pass_ans_list)
    
        



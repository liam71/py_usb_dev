class ECPoint:
    def __init__(self, x, y, infinity=False):
        self.x = x
        self.y = y
        self.infinity = infinity

    def __repr__(self):
        if self.infinity:
            return "ECPoint(infinity)"
        return f"ECPoint(x={self.x}, y={self.y})"

# 橢圓曲線參數： y^2 = x^3 + ax + b mod p
# 這裡以 secp192r1 為例（可換成你要的曲線）
p = 10313#17# 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFFFFFFFFFF
a = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFFFFFFFFFC
b = 0x64210519E59C80E70FA7E9AB72243049FEB8DEECC146B9B1

def inverse_mod(k, p):
    """ 計算模反元素： k^(-1) mod p """
    if k == 0:
        raise ZeroDivisionError("division by zero")
    return pow(k, -1, p)

def ec_add(P, Q):
    """ 橢圓曲線加法：R = P + Q """
    if P.infinity:
        return Q
    if Q.infinity:
        return P

    if P.x == Q.x and (P.y != Q.y or P.y == 0):
        return ECPoint(0, 0, True)  # 無限遠點

    if P.x == Q.x:
        # R = 2P，切線斜率
        m = (3 * P.x**2 + a) * inverse_mod(2 * P.y, p) % p
    else:
        # R = P + Q，連線斜率
        m = (Q.y - P.y) * inverse_mod(Q.x - P.x, p) % p

    rx = (m**2 - P.x - Q.x) % p
    ry = (m * (P.x - rx) - P.y) % p
    return ECPoint(rx, ry)

def ec_scalar_mul(G, d):
    """ EC 標量乘法：R = d * G """
    R = ECPoint(0, 0, True)  # 無限遠點
    Q = G
    while d > 0:
        if d & 1:
            R = ec_add(R, Q)
        Q = ec_add(Q, Q)
        d >>= 1
    return R

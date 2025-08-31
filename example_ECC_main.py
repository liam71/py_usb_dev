from example_ECC import ECPoint, ec_scalar_mul

G = ECPoint(
    0x5,
    0x1
)

private_key = 0x56
public_key = ec_scalar_mul(G, private_key)

print("Public Key:", public_key)
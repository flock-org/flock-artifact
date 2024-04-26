import hashlib
import crypto_util
from ecdsa.util import sigencode_der, sigdecode_der

def generate_serialized_elements(N, sk_string):
    if N < 1:
        raise ValueError("N must be a positive integer")
    
    elements = []
    sk = crypto_util.sk_from_string(sk_string)
    for i in range(N):
        # fixed_64_bytes = (f"Element_{i}_" + "A" * (64 - len(f"Element_{i}_"))).encode("utf-8")

        fixed_64_bytes = ("A" * 64).encode("utf-8")
        assert len(fixed_64_bytes) == 64
        ele = fixed_64_bytes
        assert len(ele.hex()) == 128
        # message_hash = hashlib.sha256(ele).digest()
        sig = sk.sign_deterministic(ele, sigencode=sigencode_der)
        elements.append(ele.hex()+sig.hex())

        
    serialized_elements = ':'.join(elements)
    
    return serialized_elements
from typing import List
import random
import hashlib
import os
import binascii
from typing import List
import json

import subprocess 
import base64

bin_dir = "./bin"
deltas_dir = "./bin"

def gen_deltas(nP):
    assert nP == 2 or nP == 3
    commands = [os.path.join(bin_dir, f"create_authshare_{nP}PC"), "gen_deltas"]
    try:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise ValueError(f"Executable '{commands[0]}' not found")

    deltas, stderr = process.communicate()
    process.stdout.close()
    process.stderr.close()

    with open(os.path.join(deltas_dir, f"deltas_{nP}PC.bin"), "wb+") as f:
        f.write(deltas)

def read_deltas(nP):
    with open(os.path.join(deltas_dir, f"deltas_{nP}PC.bin"), "rb") as f:
        blocks = f.read()

    deltas = []
    for i in range(nP):
        delta = blocks[i*16:(i+1)*16]
        delta_b64 = base64.b64encode(delta).decode("utf-8")
        deltas.append(delta_b64)

    return deltas

def gen_authshares(bin_string, nP):
    deltas_path = os.path.join(deltas_dir, f"deltas_{nP}PC.bin")
    commands = [os.path.join(bin_dir, f"create_authshare_{nP}PC"), "gen_authshares", deltas_path, bin_string]
    try:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise ValueError(f"Executable '{commands[0]}' not found")

    authshares, stderr = process.communicate()
    process.stdout.close()
    process.stderr.close()

    res = []
    block_size = len(authshares) // nP
    for i in range(nP):
        block = authshares[block_size*i:block_size*(i+1)]
        block_b64 = base64.b64encode(block).decode("utf-8") 
        res.append(block_b64)
    return res

def to_authshares(input: List[bool], nP=3):
    bin_string = "".join(str(int(x)) for x in input)
    return gen_authshares(bin_string, nP)

def to_xor_shares(input: List[bool], nP: int) -> List[str]:
    len_ = len(input)
    shares = [[] for _ in range(nP)]

    # Copy input to shares[0]
    shares[0] = input.copy()

    for i in range(1, nP):
        # Generate a random share for player i
        share_i = [bool(random.getrandbits(1)) for _ in range(len_)]
        shares[i] = share_i

        # XOR the random share into shares[0]
        shares[0] = [x ^ y for x, y in zip(shares[0], share_i)]

    # Convert the bool arrays to strings
    share_strings = ["".join(str(int(b)) for b in share) for share in shares]

    return share_strings

def convert_to_binary(hex_string) -> List[bool]:
    byte_string = binascii.unhexlify(hex_string)
    binary_array = []
    for x in byte_string:
        binary_array.extend(format(x, '08b'))
    binary_array = [x == '1' for x in binary_array]
    return binary_array


def convert_bytes_to_binary(byte_string) -> List[bool]:
    binary_array = []
    for x in byte_string:
        binary_array.extend(format(x, '08b'))
    binary_array = [x == '1' for x in binary_array]
    return binary_array

def from_binary(binary_array):
    # Convert the boolean array to a string of '1' and '0'
    binary_string = ''.join(['1' if x else '0' for x in binary_array])
    # Split the binary string into 8-bit chunks
    chunks = [binary_string[i:i+8] for i in range(0, len(binary_string), 8)]
    # Convert each 8-bit chunk to a byte
    bytes_ = bytes([int(chunk, 2) for chunk in chunks])
    # Convert the bytes to a hexadecimal string
    hex_string = binascii.hexlify(bytes_).decode('utf-8')
    return hex_string

def from_bytes_to_binary(binary_array):
    binary_string = ''.join(['1' if x else '0' for x in binary_array])
    # Split the binary string into 8-bit chunks
    chunks = [binary_string[i:i+8] for i in range(0, len(binary_string), 8)]
    # Convert each 8-bit chunk to a byte
    bytes_ = bytes([int(chunk, 2) for chunk in chunks])
    return bytes_
    

def from_xor_shares(share_strings: List[str]) -> List[bool]:
    shares = [[bool(int(b)) for b in share] for share in share_strings]
    input_ = shares[0].copy()
    for share in shares[1:]:
        input_ = [x ^ y for x, y in zip(input_, share)]
    return input_

def recover_string(shards: List[str]) -> str:
    binary_array = from_xor_shares(shards)
    original_string = from_binary(binary_array)
    return original_string

def generate_salted_hash(password_hex: str) -> str:
    salt = os.urandom(32)
    hash_value = hashlib.pbkdf2_hmac('sha256', bytes.fromhex(password_hex), salt, 100000)
    return salt.hex() + hash_value.hex()

def generated_salted_hash_from_bytes(key_bytes: bytes) -> str:
    salt = os.urandom(32)
    hash_value = hashlib.pbkdf2_hmac('sha256', key_bytes, salt, 100000)
    return salt.hex() + hash_value.hex()

def check_hashes(hashes: List[str], recovered_key: str) -> bool:
    if not hashes:
        return False
    
    salt = hashes[0][:64]
    hash_value = hashlib.pbkdf2_hmac('sha256', bytes.fromhex(recovered_key), bytes.fromhex(salt), 100000)
    expected_hash = salt + hash_value.hex()

    for item in hashes:
        if item != expected_hash:
            return False
    
    return True


if __name__ == "__main__":
    # gen_deltas(2)
    gen_deltas(3)
    
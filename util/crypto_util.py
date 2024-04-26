import os
import ecdsa
import hashlib
from merkletools import MerkleTools
import base64
import json
from ecdsa.util import sigdecode_der

def validate_proof(proof, target_hash, merkle_root):
    merkle_root = bytearray.fromhex(merkle_root)
    target_hash = bytearray.fromhex(target_hash)
    if len(proof) == 0:
        return target_hash == merkle_root
    else:
        proof_hash = target_hash
        for p in proof:
            try:
                # the sibling is a left node
                sibling = bytearray.fromhex(p['left'])
                proof_hash = hashlib.sha256(sibling + proof_hash).digest()
            except:
                # the sibling is a right node
                sibling = bytearray.fromhex(p['right'])
                proof_hash = hashlib.sha256(proof_hash + sibling).digest()
        return proof_hash == merkle_root

def build_tree(leaves):
	mt = MerkleTools(hash_type="sha256")
	mt.add_leaf(leaves, True)
	mt.make_tree()
	root_val = mt.get_merkle_root()
	return root_val, mt

def verify_merkle_proof(root_hash, proof, leaf):
    hashed_leaf = hashlib.sha256(leaf.encode("utf-8")).hexdigest()
    return validate_proof(proof, hashed_leaf, root_hash)

def generate_key_pair():
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()
    return sk, vk

def sign_message(message, private_key):
    message_hash = hashlib.sha256(message.encode("utf-8")).digest()
    signature = private_key.sign(message_hash)
    return signature

def verify_signature(message, signature, public_key):
    message_hash = hashlib.sha256(message.encode("utf-8")).digest()
    try:
        return public_key.verify(signature, message_hash)
    except ecdsa.BadSignatureError:
        return False
    
def verify_pir_signature(msg_bytes, signature, vk):
    try:
        return vk.verify(signature, msg_bytes, sigdecode=sigdecode_der)
    except ecdsa.BadSignatureError:
        return False
    
def setup_u2f():
    sk, pk = generate_key_pair()
    return sk, pk

def generate_challenge():
    return os.urandom(32).hex()

def generate_response(challenges, sk):
    root_hash, mt = build_tree(challenges)
    signature = sign_message(root_hash, sk)
    proofs = []
    for i in range(len(challenges)):
        proofs.append(mt.get_proof(i))
    return root_hash, proofs, signature

def verify_response(pk, challenge, root_hash, proof, signature):
    is_valid_sig = verify_signature(root_hash, signature, pk)
    is_valid_proof = verify_merkle_proof(root_hash, proof, challenge)
    # print("is_valid_proof", is_valid_proof)
    return is_valid_sig and is_valid_proof

def vk_to_string(verifying_key):
    """Converts an ecdsa.VerifyingKey object to a string"""
    return base64.b64encode(verifying_key.to_string()).decode('utf-8')

def vk_from_string(s):
    """Converts a string to an ecdsa.VerifyingKey object"""
    vk_bytes = base64.b64decode(s)
    return ecdsa.VerifyingKey.from_string(vk_bytes, curve=ecdsa.SECP256k1)

def sk_to_string(signing_key):
    """Converts an ecdsa.keys.SigningKey object to a string"""
    return base64.b64encode(signing_key.to_string()).decode('utf-8')

def sk_from_string(s):
    """Converts a string to an ecdsa.keys.SigningKey object"""
    sk_bytes = base64.b64decode(s)
    return ecdsa.SigningKey.from_string(sk_bytes, curve=ecdsa.SECP256k1)

def sig_to_string(signature):
    return base64.b64encode(signature).decode('utf-8')

def sig_from_string(s):
    return base64.b64decode(s)

def store_file(file_content, merkle_tree):
    print(f"Number of leaves originally: {merkle_tree.get_leaf_count()}")
    
    merkle_tree.add_leaf(file_content, True)
    merkle_tree.make_tree()

    root = merkle_tree.get_merkle_root()
    leaf_index = merkle_tree.get_leaf_count() - 1
    proof = merkle_tree.get_proof(leaf_index)

    return root, proof

def verify_inclusion(leaf_value, proof, root):
    merkle_tree = MerkleTools()
    is_valid = merkle_tree.validate_proof(proof, leaf_value, root)
    return is_valid

def proof_to_string(proof):
    try:
        proof_str = json.dumps(proof)
        return proof_str
    except Exception as e:
        print(f"An error occurred while converting the proof to a string. Exception: {e}")
        raise e
    
def proof_from_string(proof_str):
    try:
        proof_obj = json.loads(proof_str)
        return proof_obj
    except Exception as e:
        print(f"An error occurred while converting the string to a proof. Exception: {e}")
        raise e

def merkle_to_string(merkle_tree):
    leaves = merkle_tree.leaves
    leaves_str = leaves_to_string(leaves)
    return leaves_str

def string_to_merkle(leaves_str):
    leaves = string_to_leaves(leaves_str)
    return build_tree_hash(leaves)

def build_tree_hash(leaves):
    mt = MerkleTools(hash_type="sha256")
    mt.add_leaf([leaf.hex() for leaf in leaves], do_hash=False)
    return mt

def leaves_to_string(leaves):
    """
    Convert a list of leaves (bytearrays) to a string.
    """
    # Convert bytearrays to their hexadecimal string representation
    hex_leaves = [byte.hex() for byte in leaves]
    
    # Serialize as a JSON string
    return json.dumps(hex_leaves)

def string_to_leaves(s):
    """
    Convert a string back to a list of leaves (bytearrays).
    """
    # Deserialize the JSON string
    hex_leaves = json.loads(s)
    
    # Convert hexadecimal strings back to bytearrays
    leaves = [bytearray.fromhex(hex_str) for hex_str in hex_leaves]
    
    return leaves
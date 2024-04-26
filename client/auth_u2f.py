import os
import ecdsa
import hashlib
from merkletools import MerkleTools
import base64

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

def verify_merkle_proof(root_hash, proof, challenge):
    hashed_challenge = hashlib.sha256(challenge.encode("utf-8")).hexdigest()
    return validate_proof(proof, hashed_challenge, root_hash)

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

if __name__ == "__main__":
    nP = 3
    # client generate sk, pk, store pk on the clouds
    sk, pk = setup_u2f()
    
    # gen_challenge, server generates a challenge, store challenge on clouds
    challenges = [generate_challenge() for _ in range(nP)]
    root_hash, proofs, signature = generate_response(challenges, sk)
    
    # verify_challenge, serve retrieves the challenge
    for idx in range(3):
        is_valid = verify_response(pk, challenges[idx], root_hash, proofs[idx], signature)
        print(is_valid)
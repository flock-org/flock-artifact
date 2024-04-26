import subprocess
import json
from storage import AWSStorage, GCPStorage, AzureStorage, LocalStorage
import os
import sys
sys.path.insert(0, '../util')
import crypto_util
import pir_util
import time
# from merkletools import MerkleTools
import hashlib
import struct
import errno
import mmap

MAX_FAULTY_ATTEMPTS = 5  # replace this with your desired maximum number of faulty attempts
LOCKOUT_PERIOD = 24 * 60 * 60  # 24 hours in seconds
FILES_DIR = "/app/files"

def handler_body(event, bucket_name, storage_name, exec_path):    
    result = {}
    
    # result["party_int"] = event["partyInt"]
    
    e2e_start_time = time.perf_counter()
    e2e_auth_start_time = time.perf_counter()
    result["e2e_auth_server_time"] = 0
    result["e2e_op_server_time"] = 0

    event["storage_name"] = storage_name

    username = event["username"]
    if storage_name == "aws":
        storage = AWSStorage(bucket_name, username)
    elif storage_name == "gcp":
        storage = GCPStorage(bucket_name, username)
    elif storage_name == "azure":
        storage = AzureStorage(bucket_name, username)
    elif storage_name == "local":
        storage = LocalStorage(bucket_name, username)
    else:
        raise ValueError("Unknown storage type.")

    event["circuitFileLocation"] = "/app/files"
    
    # RATE LIMITING
    op_type = event["op"]
    
    if event["authOp"] in ["auth_passcode", "auth_u2f"]:
        # Retrieve the current counter and timestamp values for the operation
        try:
            n = int(storage.get_object(f"{op_type}_auth_counter"))
            last_failed_timestamp = float(storage.get_object(f"{op_type}_auth_timestamp"))
        except:
            # If it's the first run or the objects don't exist, initialize them
            n = MAX_FAULTY_ATTEMPTS
            last_failed_timestamp = 0
            storage.store_object(f"{op_type}_auth_counter", str(n))
            storage.store_object(f"{op_type}_auth_timestamp", str(last_failed_timestamp))
        
        current_time = time.perf_counter()
        if n <= 0 and current_time < last_failed_timestamp + LOCKOUT_PERIOD:
            print(f"Operation '{op_type}' is locked due to too many faulty attempts.")
            return {"error": "Maximum faulty attempts reached, try again later"}, 429
        
    ### ONE-TIME SETUP ###
    if event ["op"] == "one_time_setup":
        # U2F setup for the auth U2F
        setup_u2f(event, storage, result)

        # PK, SK setup for freshness
        sk, pk = crypto_util.setup_u2f()
        sk_string = crypto_util.sk_to_string(sk)
        pk_string = crypto_util.vk_to_string(pk)
        storage.store_object("freshness_hash_server_sk", sk_string)
        storage.store_object("freshness_hash_server_pk", pk_string)
        
        # Generate signing preparams
        # gen_signing_preparam(event, exec_path, storage, result)

        # setup agmpc
        setup_agmpc(event, storage, result)

    ### OPERATION SETUP ###
    elif event["op"] == "auth_u2f_gen_challenge":
        e2e_auth_start_time = time.perf_counter()
        auth_u2f_gen_challenge(event, storage, result)
        e2e_auth_end_time = time.perf_counter()
        result["e2e_op_server_time"] += e2e_auth_end_time - e2e_auth_start_time
    
    elif event["op"] in ["signing_setup", "sharding_setup", "aes_setup"]:
        if event["authOp"] == "auth_passcode":
            e2e_auth_start_time = time.perf_counter()
            store_passcode(event["passcodeShare"], storage, result)
            e2e_auth_end_time = time.perf_counter()
            result["e2e_op_server_time"] += e2e_auth_end_time - e2e_auth_start_time
        
        if event["op"] == "signing_setup":     
            run_signing_keygen(event, exec_path, storage, result)

        if event["op"] == "sharding_setup":
            store_key(event["shardingKeyShard"], event["shardingSaltedHash"], storage, result)

        if event["op"] == "aes_setup":
            store_aes_key(event["aesKeyShare"], storage, result)
            
    ### OPERATIONS ###
    else:
        auth_bit = -1

        # AUTHENTICATION PHASE
        e2e_auth_start_time = time.perf_counter()
        if event["authOp"] == "auth_passcode":
            auth_bit = auth_passcode(event, storage, exec_path, result)
                
        elif event["authOp"] == "auth_u2f":
            auth_bit = auth_u2f_verify_challenge(event, storage, result)

        # Update counter and timestamp during the authentication phase based on the authentication result
        if auth_bit == -1:
            # if auth_bit == -1, don't do any authentication at all (for benchmarking purpose)
            pass
        elif auth_bit != 1:
            n -= 1  # Decrement the counter on authentication failure
            storage.store_object(f"{op_type}_auth_counter", str(n))
            if n <= 0:
                # If the counter reaches zero, store the current timestamp
                storage.store_object(f"{op_type}_auth_timestamp", str(current_time))
            print(f"Authentication failed for operation '{op_type}'. Remaining attempts: {n}.")
            return {"error": "Authentication failed"}, 401
        else:
            # Reset the counter on successful authentication
            n = MAX_FAULTY_ATTEMPTS
            storage.store_object(f"{op_type}_auth_counter", str(n))
            print(f"Authentication passed for operation '{op_type}'. Counter reset to: {n}.")
            result["auth_passed_timestamp"] = time.perf_counter()

        e2e_auth_end_time = time.perf_counter()
        # result["e2e_op_server_time"] += e2e_auth_end_time - e2e_auth_start_time
        
        # OPERATION PHASE
        e2e_op_start_time = time.perf_counter()
        if event["op"] == "signing_sign":
            run_signing_sign(event, exec_path, storage, result)
            
        elif event["op"] == "sharding_recover":
            run_sharding_recover(storage, result)

        elif event["op"] == "aes_encrypt":
            run_aes_encryption(event, exec_path, storage, result)

        elif event["op"] == "aes_decrypt":
            run_aes_decryption(event, exec_path, storage, result)
            
        elif event["op"] == "freshness_store_file":
            run_freshness_file_server_store(event, storage, result)
            
        elif event["op"] == "freshness_retrieve_file":
            run_freshness_file_server_retrieve(event, storage, result)
            
        elif event ["op"] == "freshness_hash_server_store":
            run_freshness_hash_server_store(event, storage, result)
            
        elif event["op"] == "freshness_hash_server_retrieve":
            run_freshness_hash_server_retrieve(event, storage, result)
        
        elif event["op"] == "freshness_permissions_update":
            run_freshness_permissions_update(event, storage, result)
            
        elif event["op"] == "pir":
            run_handle_pir_requests(event, exec_path, storage, result)
            
        elif event["op"] == "pir_setup":
            run_store_pir_database(event, storage, result)

        elif event["op"] == "auth_passcode_setup":
            store_passcode(event["passcodeShare"], storage, result)

        e2e_op_end_time = time.perf_counter()
        result["e2e_op_server_time"] = e2e_op_end_time - e2e_op_start_time
        
    e2e_end_time = time.perf_counter()
    if event["op"] == "auth_u2f_gen_challenge":
        result["e2e_server_time_u2f"] = e2e_end_time - e2e_start_time
        result["e2e_op_server_time_u2f"] = result["e2e_op_server_time"]
        result["e2e_auth_server_time_u2f"] = result["e2e_auth_server_time"]
    else:
        result["e2e_server_time"] = e2e_end_time - e2e_start_time

    return result, 200

def gen_signing_preparam(event, exec_path, storage, result):
    start_time = time.perf_counter()
    event["op"] = "signing_preparams"
    preparams = exec("signing", exec_path, f"{json.dumps(event)}")
    end_time = time.perf_counter()
    
    result["signing_preparams"] = preparams
    result["signing_preparams_total_time"] = end_time - start_time
    
    # Store preparams
    start_time = time.perf_counter()            
    storage.store_object("preparams", preparams)
    end_time = time.perf_counter()
    result["signing_preparams_storage_time"] = end_time - start_time

def run_signing_keygen(event, exec_path, storage, result):
    # Get preparams
    start_time = time.perf_counter()
    preparams = storage.get_object("preparams")
    end_time = time.perf_counter()
    event["preParams"] = preparams
    
    result["signing_keygen_storage_time"] = end_time - start_time
    
    event["op"] = "signing_keygen"
    start_time = time.perf_counter()            
    payload = exec("signing", exec_path, f"{json.dumps(event)}")
    end_time = time.perf_counter()
    
    insert_results(payload, result)
    result["signing_keygen_total_time"] = end_time - start_time
    
    # Store key
    start_time = time.perf_counter()            
    storage.store_object("key_shard", json.loads(payload)["key"])
    end_time = time.perf_counter()
    result["signing_keygen_storage_time"] += end_time - start_time
        
def run_signing_sign(event, exec_path, storage, result):
    # Get key shard
    start_time = time.perf_counter()            
    # key_shard = storage.get_object("key_shard")
    end_time = time.perf_counter()
    result["signing_sign_storage_time"] = end_time - start_time

    with open(os.path.join(FILES_DIR, f"signing_keyshard_{event['storage_name']}.txt"), "r") as f:
        key_shard = f.read()
    event["keyShard"] = key_shard

    h = hashlib.sha256()
    # h.update(bytes.fromhex(event["message"]))
    h.update(event["message"].encode("utf-8"))
    event["message"] = h.hexdigest()

    # Signature
    start_time = time.perf_counter()            
    payload = exec("signing", exec_path, f"{json.dumps(event)}")
    end_time = time.perf_counter()
        
    insert_results(payload, result)
    result["signing_sign_total_time"] = end_time - start_time

def run_sharding_recover(storage, result): 
    # Get sharding key shard
    start_time = time.perf_counter()            
    sharding_key_shard = storage.get_object("sharding_key_shard")
    sharding_salted_hash = storage.get_object("sharding_salted_hash")
    end_time = time.perf_counter()
    result["sharding_recover_storage_time"] = end_time - start_time

    result["sharding_key_shard"] = sharding_key_shard
    result["sharding_salted_hash"] = sharding_salted_hash

def run_aes_encryption(event, exec_path, storage, result):
    start_time = time.perf_counter()            
    key_share = storage.get_object("aes_key_shard")
    end_time = time.perf_counter()
    result["aes_encrypt_storage_time"] = end_time - start_time
    event["keyShare"] = key_share
    
    start_time = time.perf_counter()            
    payload = exec("aes_ctr", exec_path, f"{json.dumps(event)}")
    end_time = time.perf_counter()
    insert_results(payload, result)
    result["aes_encrypt_time"] = end_time - start_time
    
    start_time = time.perf_counter()
    storage.store_object("aes_ciphertext_shard", json.loads(payload)["aes_ctr_out_share"])
    end_time = time.perf_counter()
    result["aes_encrypt_storage_time"] += end_time - start_time

def run_aes_decryption(event, exec_path, storage, result):
    start_time = time.perf_counter()     
    ct_shard = storage.get_object("aes_ciphertext_shard")
    key_share = storage.get_object("aes_key_shard")
    end_time = time.perf_counter()
    result["aes_decrypt_storage_time"] = end_time - start_time

    event["keyShare"] = key_share
    event["inputShare"] = ct_shard
    
    start_time = time.perf_counter()
    payload = exec("aes_ctr", exec_path, f"{json.dumps(event)}")
    end_time = time.perf_counter()
    insert_results(payload, result)
    result["aes_decrypt_time"] = end_time - start_time
    
def run_freshness_file_server_store(event, storage, result):
    start_time = time.perf_counter()
    storage.store_object(event["file_id"], event["content"])
    end_time = time.perf_counter()
    result["freshness_file_storage_time"] = end_time - start_time
    
    result["freshness_hashed_content"] = hashlib.sha256(event["content"].encode("utf-8")).hexdigest()

def run_freshness_file_server_retrieve(event, storage, result):
    start_time = time.perf_counter()
    content = storage.get_object(event["file_id"])
    end_time = time.perf_counter()
    
    result["freshness_file_storage_time"] = end_time - start_time

    result["content"] = content
    
def run_freshness_hash_server_store(event, storage, result):
    start_time = time.perf_counter()
    hash_server_sk_string = storage.get_object("freshness_hash_server_sk")
    hash_server_pk_string = storage.get_object("freshness_hash_server_pk")
    end_time = time.perf_counter()
    result["freshness_hash_server_storage_time"] = end_time - start_time
    
    valid_version_number = False
    new_file = False
    start_time = time.perf_counter()
    if storage.check_object_exists(event["file_id"]+"_version"):
        version = storage.get_object(event["file_id"]+"_version")
        end_time = time.perf_counter()
        result["freshness_hash_server_storage_time"] += end_time - start_time
        if int(version) + 1 == int(event["version"]):
            valid_version_number = True
    else:
        end_time = time.perf_counter()
        result["freshness_hash_server_storage_time"] += end_time - start_time
        if event["version"] == "0":
            valid_version_number = True
            new_file = True
    
    if True:
        if new_file:
            permissions = {}
            permissions[event["username"]] = "owner"
            permissions_str = dict_to_string(permissions)
            start_time = time.perf_counter()
            storage.store_object(event["file_id"]+"_permissions", permissions_str)
            end_time = time.perf_counter()
            result["freshness_hash_server_storage_time"] += end_time - start_time
        else:
            start_time = time.perf_counter()
            permissions_str = storage.get_object(event["file_id"]+"_permissions")
            end_time = time.perf_counter()
            result["freshness_hash_server_storage_time"] += end_time - start_time
            permissions = string_to_dict(permissions_str)
            if event["username"] not in permissions or permissions[event["username"]] not in ["owner", "writer"]:
                result["error"] = "You do not have permissions to write to this file."
                return
            
        start_time = time.perf_counter()
        storage.store_object(event["file_id"]+"_version", event["version"])
        end_time = time.perf_counter()
        result["freshness_hash_server_storage_time"] += end_time - start_time
        hash_server_sk = crypto_util.sk_from_string(hash_server_sk_string)
        start_time = time.perf_counter()
        storage.store_object(event["file_id"]+ "_entry", event["hash_entry"])
        end_time = time.perf_counter()
        result["freshness_hash_server_storage_time"] += end_time - start_time
        signature = crypto_util.sign_message(event["file_id"] + event["hash_entry"], hash_server_sk)
        sig_string = crypto_util.sig_to_string(signature)
        result["freshness_hash_server_signature"] = sig_string
        result["freshness_hash_server_pk"] = hash_server_pk_string
    else:
        result["error"] = "Error: Invalid version number."

def run_freshness_hash_server_retrieve(event, storage, result):
    start_time = time.perf_counter()
    entry = storage.get_object(event["file_id"]+ "_entry")
    hash_server_sk_string = storage.get_object("freshness_hash_server_sk")
    hash_server_pk_string = storage.get_object("freshness_hash_server_pk")
    version = storage.get_object(event["file_id"] + "_version")
    end_time = time.perf_counter()
    result["freshness_hash_server_storage_time"] = end_time - start_time

    hash_server_sk = crypto_util.sk_from_string(hash_server_sk_string)
    signature = crypto_util.sign_message(entry, hash_server_sk)
    sig_string = crypto_util.sig_to_string(signature)
    result["hash_server_entry"] = entry
    result["freshness_hash_server_pk"] = hash_server_pk_string
    result["freshness_hash_server_signature"] = sig_string
    result["version"] = version
    
def run_freshness_permissions_update(event, storage, result):
    start_time = time.perf_counter()
    permissions_str = storage.get_object(event["file_id"]+"_permissions")
    end_time = time.perf_counter()
    result["freshness_permissions_storage_time"] = end_time - start_time
    permissions = string_to_dict(permissions_str)
    if event["username"] not in permissions or permissions[event["username"]] != "owner":
        result["error"] = "You do not have permissions to update file permissions."
        return
    permissions[event["username_update"]] = event["permissions_update"]
    permissions_str = dict_to_string(permissions)
    start_time = time.perf_counter()
    storage.store_object(event["file_id"]+"_permissions", permissions_str)
    end_time = time.perf_counter()
    result["freshness_permissions_storage_time"] += end_time - start_time

def run_store_pir_database(event, storage, result):
    start_time = time.perf_counter()
    serialized_pir_database = pir_util.generate_serialized_elements(int(event["num_database_elements"]), event["pir_sk"])
    end_time = time.perf_counter()
    result["pir_database_total_time"] = end_time - start_time

    start_time = time.perf_counter()
    storage.store_object("pir_database", serialized_pir_database)
    # storage.store_object("num_database_elements", event["num_database_elements"])
    end_time = time.perf_counter()
    result["pir_database_storage_total_time"] = end_time - start_time
    
def run_handle_pir_requests(event, exec_path, storage, result):
    start_time = time.perf_counter()
    pir_database = storage.get_object("pir_database")
    # db_size = storage.get_object("num_database_elements")
    end_time = time.perf_counter()
    result["pir_storage_total_time"] = end_time - start_time
    data = {
        "serialized_request": event["request"],
        "serialized_elements": pir_database,
        "num_database_elements": event["num_database_elements"]
    }
    # serialized_json = json.dumps(data)
    # write data to shared memory
    start_time = time.perf_counter()
    # write_to_shm(data)
    # write_to_pipe(data)
    write_to_mmap(data)
    end_time = time.perf_counter()
    result["pir_write_mem_time"] = end_time - start_time

    start_time = time.perf_counter()
    payload = exec("pir", exec_path)
    end_time = time.perf_counter()
    result["pir_total_time"] = end_time - start_time
    insert_results(payload, result)
    # result["pir_response"] = payload

def store_passcode(passcode, storage, result):
    start_time = time.perf_counter()     
    storage.store_object("passcode_shard", passcode)
    end_time = time.perf_counter()
    
    result["passcode_storage_result"] = "Successfully stored passcode."
    result["passcode_storage_time"] = end_time - start_time

def store_key(key_shard, sharding_salted_hash, storage, result):
    start_time = time.perf_counter()            
    storage.store_object("sharding_key_shard", key_shard)
    storage.store_object("sharding_salted_hash", sharding_salted_hash)
    end_time = time.perf_counter()
    
    result["sharding_key_storage_result"] = "Successfully stored key."
    result["sharding_key_storage_time"] = end_time - start_time
        
def store_aes_key(key_shard, storage, result):
    start_time = time.perf_counter()            
    storage.store_object("aes_key_shard", key_shard)
    end_time = time.perf_counter()
    
    result["aes_key_storage_result"] =  "Successfully stored AES key."
    result["aes_key_storage_time"] = end_time - start_time

def auth_passcode(event, storage, exec_path, result):
    # Get stored password shard
    start_time = time.perf_counter()
    passcode_gt = storage.get_object("passcode_shard")
    end_time = time.perf_counter()
    event["passcodeGroundTruth"] = passcode_gt
    result["auth_passcode_storage_time"] = end_time - start_time

    nP = event["numParties"]

    start_time = time.perf_counter()
    payload = exec(f"auth_passcode_{nP}PC", exec_path, f"{json.dumps(event)}")
    end_time = time.perf_counter()
    result["auth_passcode_total_time"] = end_time - start_time

    insert_results(payload, result)
    
    auth_bit = int(result["auth_passcode_result"])
    return auth_bit

def setup_u2f(event, storage, result):
    # Store pk on the clouds
    start_time = time.perf_counter()
    storage.store_object("auth_u2f_pk", event["authU2fPk"])
    end_time = time.perf_counter()
    result["u2f_setup_storage_time"] = end_time - start_time

def setup_agmpc(event, storage, result):
    storage.store_object("delta", event["delta"])

def auth_u2f_gen_challenge(event, storage, result):
    start_time = time.perf_counter()
    challenge = crypto_util.generate_challenge()
    end_time = time.perf_counter()
    
    result["auth_u2f_challenge"] = {event["partyInt"]: challenge}
    result["auth_u2f_challenge_time"] = end_time - start_time
    
    # Store challenge on the clouds
    start_time = time.perf_counter()
    storage.store_object("auth_u2f_challenge", challenge)
    end_time = time.perf_counter()
    result["auth_u2f_challenge_storage_time"] = end_time - start_time
        
def auth_u2f_verify_challenge(event, storage, result):     
    start_time = time.perf_counter() 
    vk_string = storage.get_object("auth_u2f_pk")
    challenge = storage.get_object("auth_u2f_challenge")
    end_time = time.perf_counter()
    result["auth_u2f_storage_time"] = end_time - start_time
    
    start_time = time.perf_counter() 
    vk = crypto_util.vk_from_string(vk_string)
    sig_string = event["authU2fSignature"]
    signature = crypto_util.sig_from_string(sig_string)
    is_valid = crypto_util.verify_response(vk, challenge, event["authU2fRootHash"], event["authU2fProof"], signature)
    end_time = time.perf_counter()

    result["auth_u2f_result"] = is_valid
    result["auth_u2f_time"] = end_time - start_time
    
    return is_valid

def insert_results(payload, result): 
    print("Returned Payload:", payload, flush=True)
    try:
        payload_json = json.loads(payload)
        for key in payload_json:
            if key != "key":
                result[key] = payload_json[key]
    except Exception:
        print("Exception when parsing the payload as JSON.")
    
def exec(op, exec_path, *args):
    if op not in exec_path:
        raise ValueError(f"Unknown operation '{op}'")

    command = [exec_path[op], *args]
    print(command, flush=True)
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise ValueError(f"Executable '{command[0]}' not found")

    stdout, stderr = process.communicate()
    output_lines = stdout.decode('utf-8').splitlines()

    for line in output_lines:
        print("Output:", line, flush=True)

    last_output = output_lines[-1] if output_lines else ""

    if stderr:
        print(f"Error: {stderr.decode('utf-8')}", flush=True)

    process.stdout.close()
    process.stderr.close()

    return last_output

def exec_with_payload(op, exec_path, payload):
    """The arguments of the function are passed in through stdin"""

    if op not in exec_path:
        raise ValueError(f"Unknown operation '{op}'")

    command = [exec_path[op]]
    print(command, flush=True)
    try:
        tik = time.perf_counter()
        result = subprocess.run(command, input=payload, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tok = time.perf_counter()
        print("execute function cost:", tok - tik)
    except subprocess.CalledProcessError as e:
        print(f"The executable failed with: {str(e)}")

    stdout, stderr = result.stdout, result.stderr
    output_lines = stdout.splitlines()

    for line in output_lines:
        print("Output:", line, flush=True)

    last_output = output_lines[-1] if output_lines else ""

    if stderr:
        print(f"Error: {stderr}", flush=True)

    return last_output

def dict_to_string(dict_obj):
    """Converts a dictionary to a JSON string."""
    try:
        return json.dumps(dict_obj)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Unable to convert dictionary to JSON string: {e}")


def string_to_dict(string_obj):
    """Converts a JSON string to a dictionary."""
    try:
        return json.loads(string_obj)
    except (TypeError, json.JSONDecodeError) as e:
        raise ValueError(f"Unable to convert JSON string to dictionary: {e}")


def write_to_shm(data):
    shm_name = '/dev/shm/pir'
    with open(shm_name, 'wb') as shm_file:
        for key, value in data.items():
            if isinstance(value, str):
                encoded_value = value.encode('utf-8')
                shm_file.write(struct.pack('I', len(encoded_value)))
                shm_file.write(encoded_value)
            elif isinstance(value, int):
                shm_file.write(struct.pack('I', value))
            else:
                raise ValueError(f"Unsupported data type: {type(value)}")


def write_to_pipe(data):
    fifo_name = '/tmp/pir'
    # Create the named pipe (FIFO) if it doesn't already exist
    try:
        os.mkfifo(fifo_name)
    except OSError as oe: 
        if oe.errno != errno.EEXIST:
            raise

    # Open the named pipe in binary write mode
    with open(fifo_name, 'wb') as fifo:
        for key, value in data.items():
            if isinstance(value, str):
                encoded_value = value.encode('utf-8')
                # Write the length of the string as a 4-byte integer, followed by the string itself
                fifo.write(struct.pack('I', len(encoded_value)))
                fifo.write(encoded_value)
            elif isinstance(value, int):
                # Write the integer value as a 4-byte integer
                fifo.write(struct.pack('I', value))
            else:
                raise ValueError(f"Unsupported data type: {type(value)}")


def write_to_mmap(data):
    file_name = '/tmp/pir'
    # Create a new file or overwrite an existing one
    with open(file_name, 'wb') as f:
        # Determine the size of the memory-mapped file
        total_size = sum(4 + len(value.encode('utf-8')) if isinstance(value, str) else 4 for value in data.values())
        # Set the file size
        f.truncate(total_size)
    
    # Open the file in r+b mode to read and write in binary
    with open(file_name, 'r+b') as f:
        # Create the memory-mapped object
        mmapped_file = mmap.mmap(f.fileno(), 0)
        
        offset = 0  # Initialize offset to keep track of where to write next
        for key, value in data.items():
            if isinstance(value, str):
                encoded_value = value.encode('utf-8')
                # Write the length of the string as a 4-byte integer, followed by the string itself
                mmapped_file[offset:offset+4] = struct.pack('I', len(encoded_value))
                offset += 4
                mmapped_file[offset:offset+len(encoded_value)] = encoded_value
                offset += len(encoded_value)
            elif isinstance(value, int):
                # Write the integer value as a 4-byte integer
                mmapped_file[offset:offset+4] = struct.pack('I', value)
                offset += 4
            else:
                raise ValueError(f"Unsupported data type: {type(value)}")
        mmapped_file.close()  # Close the memory-mapped file
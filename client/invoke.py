import json
import aiohttp
import subprocess
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import sys
import requests
import sharding_helper
sys.path.insert(0, '../util')
import crypto_util
import time
import hashlib
import statistics
import secrets
import binascii
from config import *

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def append_common_fields(datas):
  for i, data in enumerate(datas):
    data["username"] = USERNAME
    data["routerAddr"] = ROUTER_ADDR
    data["routerPort"] = ROUTER_PORT + offset % 4
    # data["routerPort"] = ROUTER_PORT
    data["numParties"] = 3
    data["useRouter"] = USE_ROUTER
    data["certPath"] = CERT_PATH
    data["partyInt"] = i if len(datas) == 3 else i + 1
    if "authOp" not in data:
        data["authOp"] = ""

def send_request(url, json_data):
    tic = time.perf_counter()
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json_data, headers=headers, verify=False)
    toc = time.perf_counter()
    # print(response.text)
    size_in_bytes = sys.getsizeof(response.content)
    print("Response size:", size_in_bytes)

    response_json = response.json()
    response_json["invoke_time"] = toc - tic
    return response_json


def invoke(datas):
    futures, results = [], []
    append_common_fields(datas)

    # when measuring throughput, use the larger server from AWS to saturate the Azure server.
    if sys.argv[-1].startswith("user") and sys.argv[1] == "baseline" and sys.argv[2] in ["sharding_recover"]:
        URLS[0] = f"https://{GCP_TP_ADDR}:443"
        URLS[1] = f"https://{AWS_TP_ADDR}:443"

    print("URLS:", URLS)

    with ThreadPoolExecutor() as executor:
        for party_int in range(len(datas)-1, -1, -1):   
            json_data = json.dumps(datas[party_int])

            futures.append(executor.submit(send_request, URLS[party_int], json_data))
    for future in as_completed(futures):
        results.append(future.result())
    return results


def invoke_2PC(datas):
    futures, results = [], []
    append_common_fields(datas)

    # when measuring throughput, use the larger server from AWS to saturate the Azure server.
    if sys.argv[-1].startswith("user") and sys.argv[1] == "baseline" and sys.argv[2] in ["freshness_retrieve_file", "pir"]:
        URLS[1] = f"https://{AWS_TP_ADDR}:443"

    with ThreadPoolExecutor() as executor:
        for i in range(2):   
            json_data = json.dumps(datas[i])
            print(json_data)
            futures.append(executor.submit(send_request, URLS[i+1], json_data))
    for future in as_completed(futures):
        results.append(future.result())
    return results


def invoke_sharding_setup(log_key_size):
    random_bytes = secrets.token_bytes(2 ** log_key_size)
    print("Key size: ", 2 ** log_key_size)
    key_shards = gen_shards_from_bytes(random_bytes)
    sharding_salted_hash = sharding_helper.generated_salted_hash_from_bytes(random_bytes)

    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "sharding_setup"
        data["shardingKeyShard"] = key_shards[i] 
        data["shardingSaltedHash"] = sharding_salted_hash
        
    results = invoke(datas)
    return results


def invoke_sharding_recover():
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "sharding_recover"
    results = invoke(datas)
    recover_sharding_key(results)
    return results  


def invoke_signing_keygen():
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "signing_setup"
        data["awsInt"] = 1
        data["gcpInt"] = 0
        data["azureInt"] = 2
        data["gcpAddr"] = GCP_ADDR
        data["awsAddr"] = AWS_ADDR
        data["azureAddr"] = AZURE_ADDR
        data["awsPort"] = ":"+str(AWS_PORT+offset)
        data["azurePort1"] = ":"+str(AZURE_PORT_1+offset*5)
        data["azurePort2"] = ":"+str(AZURE_PORT_2+offset*5)
    results = invoke(datas)
    return results


def invoke_signing_sign(msg_loglen):
    msg_len = 2 ** msg_loglen
    msg = secrets.token_hex(msg_len)
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "signing_sign"
        data["message"] = msg
        data["awsInt"] = 1
        data["gcpInt"] = 0
        data["azureInt"] = 2
        data["gcpAddr"] = GCP_ADDR
        data["awsAddr"] = AWS_ADDR
        data["azureAddr"] = AZURE_ADDR
        data["awsPort"] = ":"+ str(AWS_PORT+offset*5)
        data["azurePort1"] = ":"+str(AZURE_PORT_1+offset*5)
        data["azurePort2"] = ":"+str(AZURE_PORT_2+offset*5)
    results = invoke(datas)
    return results


def invoke_aes_setup():
    aes_key = secrets.token_bytes(16)
    aes_shards = gen_shards_from_bytes(aes_key)
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "aes_setup"
        data["aesKeyShare"] = aes_shards[i]
    results = invoke(datas)
    return results


def invoke_aes_encrypt(log_input_size):
    input_size = 2 ** int(log_input_size)
    input_hex = secrets.token_hex(input_size)
    input_hash = hashlib.sha256(bytes.fromhex(input_hex)).hexdigest()
    aes_input_shards = gen_shards(input_hex+input_hash)

    ip_addrs = ["", GCP_ADDR, AWS_ADDR, AZURE_ADDR]
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "aes_encrypt"
        data["inputShare"] = aes_input_shards[i]
        data["ipAddrs"] = ip_addrs
        data["port"] = CPP_PORT + offset
    results = invoke(datas)
    return results


def invoke_pir_setup(log_db_size):
    db_size = 2 ** int(log_db_size)
    print(f"Setting up PIR with {db_size} elements")
    with open(f"./output/pir-sk.txt", "r") as f:
        sk_string = f.read()
    datas = [{}, {}]
    for i, data in enumerate(datas):
        data["op"] = "pir_setup"
        data["num_database_elements"] = db_size
        data["pir_sk"] = sk_string
    results = invoke_2PC(datas)
    return results


def invoke_pir(log_db_size):
    indices = "1"
    db_size = 2 ** int(log_db_size)
    requests = gen_pir_requests(indices, db_size)
    datas = [{}, {}]
    for i, data in enumerate(datas):
        data["op"] = "pir"
        data["num_database_elements"] = db_size
        data["request"] = requests["request" + str(i + 1)]
    results = invoke_2PC(datas)
    handle_pir_responses(results)
    return results


def invoke_freshness_store_file(log_file_size):
    file_size = 2 ** log_file_size
    print("File size:", file_size)

    file_id = "file"
    version = "0"

    file_server_data, hash_server_data = {}, {}
    file_content = secrets.token_hex(file_size)
    file_server_data["op"] = "freshness_store_file"
    file_server_data["file_id"] = file_id
    file_server_data["content"] = file_content
    

    hash_server_data["file_id"] = file_id
    hash_server_data["hash_entry"] = hashlib.sha256(file_content.encode("utf-8")).hexdigest()
    hash_server_data["op"] = "freshness_hash_server_store"
    hash_server_data["version"] = version 

    datas = [file_server_data, hash_server_data]
    file_server_result, hash_server_result = invoke_2PC(datas)
    if "freshness_hash_server_pk" in file_server_result:
        file_server_result, hash_server_result = hash_server_result, file_server_result
    hash_server_sig_str = hash_server_result["freshness_hash_server_signature"]
    hash_server_pk_str = hash_server_result["freshness_hash_server_pk"]
    hash_server_sig = crypto_util.sig_from_string(hash_server_sig_str)
    hash_server_pk = crypto_util.vk_from_string(hash_server_pk_str)
    is_valid = crypto_util.verify_signature(file_server_data["file_id"] + hash_server_data["hash_entry"], hash_server_sig, hash_server_pk)
    if is_valid:
        print("Hash server succeessfully stored hash.")
    else:
        print("Hash server failed to store hash.")

    return [file_server_result, hash_server_result]


def invoke_freshness_retrieve_file():
    file_server_data, hash_server_data = {}, {}

    file_id = "file"

    file_server_data["op"] = "freshness_retrieve_file"
    file_server_data["file_id"] = file_id
    
    hash_server_data["file_id"] = file_id
    hash_server_data["op"] = "freshness_hash_server_retrieve"

    datas = [file_server_data, hash_server_data]
    file_server_result, hash_server_result = invoke_2PC(datas)

    if "freshness_hash_server_pk" in file_server_result:
        file_server_result, hash_server_result = hash_server_result, file_server_result

    retrieved_content = file_server_result["content"] 
    hashed_content = hashlib.sha256(retrieved_content.encode("utf-8")).hexdigest()
        
    hash_server_sig_str = hash_server_result["freshness_hash_server_signature"]
    hash_server_pk_str = hash_server_result["freshness_hash_server_pk"]
    hash_server_entry = hash_server_result["hash_server_entry"]
    hash_server_version = hash_server_result["version"]
    hash_server_sig = crypto_util.sig_from_string(hash_server_sig_str)
    hash_server_pk = crypto_util.vk_from_string(hash_server_pk_str)
    is_valid = crypto_util.verify_signature(hash_server_entry, hash_server_sig, hash_server_pk)
    if is_valid:
        print("Hash server signature verified.")
    else:
        print("Hash server signature verified.")
        
    if hash_server_entry.startswith(hashed_content):
        print("Hashes are the same, so content is untampered. Here are the latest file contents: ", retrieved_content)
        print("Version: ", hash_server_version)
    else:
        print("Hashes are inconsistent. Tampering has occurred.")

    return [file_server_result, hash_server_result]

def invoke_auth_passcode(passcode):
    passcode_hex = binascii.hexlify(str(passcode).encode("utf-8")).decode('utf-8')
    passcode_shards = gen_auth_shards(passcode_hex)
    deltas = sharding_helper.read_deltas(N)
    ip_addrs = ["", GCP_ADDR, AWS_ADDR, AZURE_ADDR]
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["authOp"] = "auth_passcode"
        data["op"] = ""
        data["passcodeShare"] = passcode_shards[i]
        data["ipAddrs"] = ip_addrs
        data["port"] = CPP_PORT
        data["delta"] = deltas[i]
    results = invoke(datas)
    return results


def invoke_auth_passcode_setup(passcode):
    passcode_hex = binascii.hexlify(str(passcode).encode("utf-8")).decode('utf-8')
    passcode_shards = gen_auth_shards(passcode_hex)
    datas = [{}, {}, {}]
    for i, data in enumerate(datas):
        data["op"] = "auth_passcode_setup"
        data["passcodeShare"] = passcode_shards[i]
    results = invoke(datas)
    return results


def compute_u2f_challenges(orig_op, results):
    global time_count
    global USERNAME
    start_time = time.perf_counter()
    challenges = {}
    for element in results:
        json_data = json.loads(element)
        challenge = json_data['auth_u2f_challenge']
        challenges.update(challenge)

    party_keys = list(challenges.keys())
    party_keys.sort()
    sorted_challenges = {i: challenges[i] for i in party_keys}
    # Read the string from the file
    with open(f"./output/sk-{USERNAME}.txt", "r") as f:
        sk_string = f.read()
    root_hash, proofs, signature = crypto_util.generate_response(list(sorted_challenges.values()), crypto_util.sk_from_string(sk_string))
    datas = [{} for _ in range(len(results))]
    for i in range(len(datas)):
        datas[i]["authU2fRootHash"] = root_hash
        datas[i]["authU2fProof"] = proofs[i]
        datas[i]["authU2fSignature"] = crypto_util.sig_to_string(signature)
        datas[i]["op"] = orig_op
        datas[i]["authOp"] = "auth_u2f_complete"
    end_time = time.perf_counter()
    time_count += end_time - start_time
    return datas


def invoke_auth_u2f():
    datas = [{}, {}, {}]
    for i in range(len(datas)):
        datas[i]["op"] = "auth_u2f_gen_challenge"

    results = invoke(datas)
    
    challenges = {}
    max_invoke_time = 0
    max_server_time = 0
    for element in results:
        print(element)
        challenge = element['auth_u2f_challenge']
        challenges.update(challenge)
        max_invoke_time = max(max_invoke_time, element["invoke_time"])
        max_server_time = max(max_server_time, element["e2e_op_server_time"])

    party_keys = list(challenges.keys())
    party_keys.sort()
    sorted_challenges = {i: challenges[i] for i in party_keys}


    datas = [{}, {}, {}]
    with open(f"./output/sk-user1.txt", "r") as f:
        sk_string = f.read()
    root_hash, proofs, signature = crypto_util.generate_response(list(sorted_challenges.values()), crypto_util.sk_from_string(sk_string))

    for i in range(len(datas)):
        datas[i]["authU2fRootHash"] = root_hash
        datas[i]["authU2fProof"] = proofs[i]
        datas[i]["authU2fSignature"] = crypto_util.sig_to_string(signature)
        datas[i]["authOp"] = "auth_u2f"
        datas[i]["op"] = ""

    results = invoke(datas)
    for element in results:
        element["invoke_time"] += max_invoke_time
        element["e2e_server_time"] += max_server_time
    return results


def gen_shards_from_bytes(unsharded):
    unsharded_bin = sharding_helper.convert_bytes_to_binary(unsharded)
    shards = sharding_helper.to_xor_shares(unsharded_bin, N)
    return shards


def gen_shards(unsharded, shard_len=256):
    unsharded_bin = sharding_helper.convert_to_binary(unsharded)
    if len(unsharded_bin) < shard_len:
        unsharded_bin += [False] * (shard_len - len(unsharded_bin))
    shards = sharding_helper.to_xor_shares(unsharded_bin, N)
    return shards


def gen_auth_shards(unsharded, shard_len=256):
    unsharded_bin = sharding_helper.convert_to_binary(unsharded)
    if len(unsharded_bin) < shard_len:
        unsharded_bin += [False] * (shard_len - len(unsharded_bin))
    shards = sharding_helper.to_authshares(unsharded_bin, N)
    return shards


def recover_sharding_key(results):
    sharding_key_shards, sharding_salted_hashes = [], []
    for i, element in enumerate(results):
        try:
            sharding_key_shards.append(element['sharding_key_shard'])
            sharding_salted_hashes.append(element['sharding_salted_hash'])
        except Exception:
            print(f"Authentication failed for party {i}")
    
    recovered_key = sharding_helper.recover_string(sharding_key_shards)
    verified = sharding_helper.check_hashes(sharding_salted_hashes, recovered_key)
    if verified:
        print("Recovered key:", recovered_key[:10])
    else:
        print("Recovered key:", recovered_key[:10])
        print("Verification failed. Hashes are inconsistent.")


def gen_pir_requests(indices, database_size):
    serialized_requests_json = exec("gen_requests", exec_path, indices, str(database_size))
    requests = json.loads(serialized_requests_json)
    
    return requests


def handle_pir_responses(results):
    responses = []
    for i, element in enumerate(results):
        try:
            responses.append(element['pir_response'])
        except Exception:
            print("Failed to extract json response")
    
    # Create a JSON object of the serialized PirResponses
    responses_json = {
        "response1": responses[0],
        "response2": responses[1],
    }
    serialized_responses_json = json.dumps(responses_json)
    
    # Get the final answer by processing the PirResponses
    res = exec("handle_responses", exec_path, serialized_responses_json)

    ele = bytes.fromhex(res[:128])
    sig = bytes.fromhex(res[128:])

    with open("./output/pir-pk.txt", "r") as f:
        vk_string = f.read()
    vk = crypto_util.vk_from_string(vk_string)
    sig_check = crypto_util.verify_pir_signature(ele, sig, vk)
    assert sig_check is True
    print("Signature verified")
    print("Retrieved element: ", ele)


def exec(op, exec_path, *args):
    if op not in exec_path:
        raise ValueError(f"Unknown operation '{op}'")

    command = [exec_path[op], *args]
    print(command)
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise ValueError(f"Executable '{command[0]}' not found")

    stdout, stderr = process.communicate()
    output_lines = stdout.decode('utf-8').splitlines()

    last_output = output_lines[-1] if output_lines else ""
    print(last_output)
    if stderr:
        print(f"Error: {stderr.decode('utf-8')}")

    process.stdout.close()
    process.stderr.close()

    return last_output


def bench():
    tic = time.perf_counter()

    global USERNAME 
    global offset
    tmp = sys.argv[-1]
    if tmp.startswith("user"):
        USERNAME = tmp
        offset = int(tmp.lstrip("user"))

    op = sys.argv[2]
    if op == "sharding_setup":
        log_key_size = int(sys.argv[3])
        results = invoke_sharding_setup(log_key_size)
    elif op == "sharding_recover":
        results = invoke_sharding_recover()
    elif op == "signing_keygen":
        results = invoke_signing_keygen()
    elif op == "signing_sign":
        log_msg_size = int(sys.argv[3])
        results = invoke_signing_sign(log_msg_size)
    elif op == "aes_setup":
        results = invoke_aes_setup()
    elif op == "aes_encrypt":
        log_input_size = int(sys.argv[3])
        results = invoke_aes_encrypt(log_input_size)
    elif op == "pir_setup":
        log_input_size = int(sys.argv[3])
        results = invoke_pir_setup(log_input_size)
    elif op == "pir":
        log_input_size = int(sys.argv[3])
        results = invoke_pir(log_input_size)
    elif op == "freshness_store_file":
        log_file_size = int(sys.argv[3])
        results = invoke_freshness_store_file(log_file_size)
    elif op == "freshness_retrieve_file":
        results = invoke_freshness_retrieve_file()
    elif op == "auth_passcode":
        passcode = int(sys.argv[3])
        results = invoke_auth_passcode(passcode)
    elif op == "auth_passcode_setup":
        passcode = int(sys.argv[3])
        results = invoke_auth_passcode_setup(passcode)
    elif op == "auth_u2f":
        results = invoke_auth_u2f()

    toc = time.perf_counter()
    e2e_time = toc - tic

    runtime_dict = {}
    max_server_time = 0
    max_invoke_time = 0
    max_inmem_time = 0
    for entry in results:
        max_server_time = max(entry["e2e_server_time"], max_server_time)
        max_invoke_time = max(entry["invoke_time"], max_invoke_time)

        if op == "pir":
            extra_time = entry["pir_storage_total_time"] + entry["pir_setup_db_time"] + entry["pir_write_mem_time"]
            inmem_time = entry["e2e_server_time"] - extra_time
            max_inmem_time = max(inmem_time, max_inmem_time)
    
    client_time = e2e_time - max_invoke_time
    runtime_dict["server_time"] = max_server_time
    runtime_dict["client_time"] = client_time
    runtime_dict["e2e_time"] = e2e_time
    runtime_dict["inmem_time"] = max_inmem_time

    print(runtime_dict)

    return runtime_dict


def latency(op, log_input_size):
    tic = time.perf_counter()

    if op == "sharding_setup":
        results = invoke_sharding_setup(log_input_size)
    elif op == "sharding_recover":
        results = invoke_sharding_recover()
    elif op == "signing_keygen":
        results = invoke_signing_keygen()
    elif op == "signing_sign":
        results = invoke_signing_sign(log_input_size)
    elif op == "aes_setup":
        results = invoke_aes_setup()
    elif op == "aes_encrypt":
        results = invoke_aes_encrypt(log_input_size)
    elif op == "pir_setup":
        results = invoke_pir_setup(log_input_size)
    elif op == "pir":
        results = invoke_pir(log_input_size)
    elif op == "freshness_store_file":
        results = invoke_freshness_store_file(log_input_size)
    elif op == "freshness_retrieve_file":
        results = invoke_freshness_retrieve_file()

    toc = time.perf_counter()
    e2e_time = toc - tic

    runtime_dict = {}
    max_server_time = 0
    max_invoke_time = 0
    max_inmem_time = 0
    for entry in results:
        max_server_time = max(entry["e2e_server_time"], max_server_time)
        max_invoke_time = max(entry["invoke_time"], max_invoke_time)

        if op == "pir":
            extra_time = entry["pir_storage_total_time"] + entry["pir_setup_db_time"] + entry["pir_write_mem_time"]
            inmem_time = entry["e2e_server_time"] - extra_time
            max_inmem_time = max(inmem_time, max_inmem_time)
    
    client_time = e2e_time - max_invoke_time
    runtime_dict["server_time"] = max_server_time
    runtime_dict["client_time"] = client_time
    runtime_dict["e2e_time"] = e2e_time
    runtime_dict["inmem_time"] = max_inmem_time

    print(runtime_dict)

    return runtime_dict


def aggregate(trials=10):

    server_latencies = []
    client_latencies = []
    e2e_latencies = [] 
    inmem_latencies = []

    for i in range(trials):
        runtime_dict = bench()

        server_latencies.append(runtime_dict["server_time"])
        client_latencies.append(runtime_dict["client_time"])     
        e2e_latencies.append(runtime_dict["e2e_time"])
        inmem_latencies.append(runtime_dict["inmem_time"])

    res = []

    mean = statistics.mean(server_latencies)
    std = statistics.stdev(server_latencies)
    print("Server time mean and std:", mean, std)

    res += [mean, std]

    mean = statistics.mean(client_latencies)
    std = statistics.stdev(client_latencies)
    print("Client time mean and std:", mean, std)

    res += [mean, std]

    mean = statistics.mean(e2e_latencies)
    std = statistics.stdev(e2e_latencies)
    print("E2E time mean and std:", mean, std)

    res += [mean, std]

    mean = statistics.mean(inmem_latencies)
    std = statistics.stdev(inmem_latencies)
    print("In mem server time mean and std:", mean, std)

    print(res)



if __name__ == "__main__":
    bench()
    # aggregate(10)
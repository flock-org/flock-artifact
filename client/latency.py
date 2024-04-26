import os
import time

from config import *
from invoke import *

def execute(op, log_input_size):
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


def aggregate(op, log_input_size, trials=10):
    server_latencies = []
    client_latencies = []
    e2e_latencies = []
    inmem_latencies = []

    # execute a test trial before recording the numbers
    execute(op, log_input_size)
    time.sleep(0.5)

    i = 0
    while i < trials:
        try:
            runtime_dict = execute(op, log_input_size)
            time.sleep(0.5)
            server_latencies.append(runtime_dict["server_time"])
            client_latencies.append(runtime_dict["client_time"])
            e2e_latencies.append(runtime_dict["e2e_time"])
            inmem_latencies.append(runtime_dict["inmem_time"])
            i += 1
        except Exception as e:
            print(f"Exception occurred in trial {i+1}: {str(e)}")
            print("Retrying the trial...")

    result = {}

    server_mean = statistics.mean(server_latencies)
    server_std = statistics.stdev(server_latencies)
    print("Server time mean and std:", server_mean, server_std)
    result["server_time"] = {"mean": server_mean, "std": server_std}

    client_mean = statistics.mean(client_latencies)
    client_std = statistics.stdev(client_latencies)
    print("Client time mean and std:", client_mean, client_std)
    result["client_time"] = {"mean": client_mean, "std": client_std}

    e2e_mean = statistics.mean(e2e_latencies)
    e2e_std = statistics.stdev(e2e_latencies)
    print("E2E time mean and std:", e2e_mean, e2e_std)
    result["e2e_time"] = {"mean": e2e_mean, "std": e2e_std}

    inmem_mean = statistics.mean(inmem_latencies)
    inmem_std = statistics.stdev(inmem_latencies)
    print("In mem server time mean and std:", inmem_mean, inmem_std)
    result["inmem_time"] = {"mean": inmem_mean, "std": inmem_std}

    return result


def save_result(result_json, op, log_input_size, mode, dir="../results"):
    fpath = os.path.join(dir, f"{op}_{log_input_size}_{mode}.json")
    with open(fpath, "w+") as f:
        json.dump(result, f, indent=4)


if __name__ == "__main__":
    mode = sys.argv[1]
    op = sys.argv[2]

    if op == "sharding_setup":
        log_input_size = 10
        result = aggregate("sharding_setup", log_input_size)
        save_result(result, op, log_input_size, mode)
    elif op == "signing_keygen":
        log_input_size = 10
        result = aggregate("signing_keygen", log_input_size)
        save_result(result, op, log_input_size, mode)
    elif op == "pir_setup":
        log_input_size = 10
        result = aggregate("pir_setup", log_input_size)
        save_result(result, op, log_input_size, mode)
    elif op == "freshness_store_file":
        log_input_size = 10
        result = aggregate("freshness_store_file", log_input_size)
        save_result(result, op, log_input_size, mode)
    elif op == "aes_setup":
        log_input_size = 7
        result = aggregate("aes_setup", log_input_size)
        save_result(result, op, log_input_size, mode)

    if op == "sharding_recover":
        for log_input_size in [4,6,8,10,12,14,16]:
            execute("sharding_setup", log_input_size)
            result = aggregate("sharding_recover", log_input_size)
            save_result(result, op, log_input_size, mode)
    elif op == "signing_sign":
        for log_input_size in [4,6,8,10,12,14,16]:
            execute("signing_keygen", log_input_size)
            result = aggregate("signing_sign", log_input_size)
            save_result(result, op, log_input_size, mode)
    elif op == "aes_encrypt":
        for log_input_size in [1,3,5,7,9]:
            execute("aes_setup", log_input_size)
            result = aggregate("aes_encrypt", log_input_size)
            save_result(result, op, log_input_size, mode)
    elif op == "pir":
        for log_input_size in [4,6,8,10,12,14,16]:
            execute("pir_setup", log_input_size)
            result = aggregate("pir", log_input_size)
            save_result(result, op, log_input_size, mode)
    elif op == "freshness_retrieve_file":
        for log_input_size in [4,6,8,10,12,14,16]:
            execute("freshness_store_file", log_input_size)
            result = aggregate("freshness_retrieve_file", log_input_size)
            save_result(result, op, log_input_size, mode)
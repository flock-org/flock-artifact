import sys
import time
import threading
import subprocess
import concurrent.futures
import json

MAX_NUM_THREADS = 30
NUM_THREADS = [i for i in range(1, MAX_NUM_THREADS+1)]  # Number of threads to test
REQUEST_ARGS = sys.argv[1:]  # Arguments to pass to request
TIME_LIMIT = 60  # Time limit for each run (in seconds)
PORT_MAX = 400
PORT_BASE = 5001
if REQUEST_ARGS[0].startswith("signing"):
    PORT_INCREMENT = 10
elif REQUEST_ARGS[0].startswith("sharding"):
    PORT_INCREMENT = 30
else :
    PORT_INCREMENT = 30


offset = 15
results_dict = {}

def send_requests(thread_idx):
    num_requests = 0
    global PORT

    count = 0
    while True:
        request_args = REQUEST_ARGS + [f"user{str(thread_idx+1)}"]
        with threading.Lock():
            PORT += PORT_INCREMENT

        try:
            result = subprocess.run(["python3", "invoke.py", *request_args], capture_output=True)
            output_string = result.stdout.decode()
            print(output_string)

            # Increment number of requests
            duration = time.time() - START_TIME
            print("Received response from", request_args[-1])
            print("Current duration:", duration)
            if duration > offset and duration < TIME_LIMIT + offset:
                num_requests += 1
        except Exception:
            pass

        count += 1

        # Check if time is up
        if time.time() - START_TIME >= TIME_LIMIT + offset:
            break

    return num_requests


def run_experiment(num_threads):
    # Start time
    global START_TIME
    START_TIME = time.time()

    # Start threads and collect their results
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(send_requests, range(num_threads)))

    # Calculate total number of requests
    total_requests = sum(results)
    return total_requests


def setup_experiments(num_threads):
    print("Setting up throughput experiments...")
    op = REQUEST_ARGS[1]
    setup_op = None
    if op == "sharding_recover":
        setup_op = "sharding_setup"
    elif op == "signing_sign":
        setup_op = "signing_keygen"
    elif op == "aes_encrypt":
        setup_op = "aes_setup"
    elif op == "pir":
        setup_op = "pir_setup"
    elif op == "freshness_retrieve_file":
        setup_op = "freshness_store_file"

    for thread_idx in range(num_threads):
        request_args = REQUEST_ARGS + [f"user{str(thread_idx+1)}"]
        request_args[1] = setup_op
        print(request_args)
        result = subprocess.run(["python3", "invoke.py", *request_args], capture_output=True)
        # print(result.stdout)


if __name__ == "__main__":
    # Run experiments for each number of threads
    PORT = 0

    op = REQUEST_ARGS[1]
    if op == "signing_sign":
        threads = [6,8,10,12]
    elif op == "aes_encrypt":
        threads = [1, 2]
    else:
        threads = [10,12,14,16]

    if op != "signing_sign":
        setup_experiments(threads[-1])

    for num_threads in threads:
        print(f"Running throughput benchmark with {num_threads} threads")
        NUM_REQUESTS = 0

        # Run experiment
        num_requests = run_experiment(num_threads)
        throughput = num_requests/(TIME_LIMIT/60)
        results_dict[num_threads] = throughput
        # Print results
        print(f"Threads: {num_threads} | Total number of requests: {num_requests} | Throughput: {throughput:.2f} requests/minute")

# Write results to JSON file
with open(f'../results/tp_{sys.argv[1]}_{sys.argv[2]}.json', 'w') as f:
    json.dump(results_dict, f, indent=4)

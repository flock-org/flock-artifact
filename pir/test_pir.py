import subprocess
import json
import sys

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


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <indices (e.g., '6,7,8')>")
        sys.exit(1)

    # Convert the comma-separated string of indices to a list of integers
    indices = sys.argv[1]
    
    # Step 1: Generate PirRequests
    exec_path = {
        "gen_requests": "./bazel-bin/client_gen_pir_requests_bin",
        "handle_request": "./bazel-bin/server_handle_pir_requests_bin",
        "handle_responses": "./bazel-bin/client_handle_pir_responses_bin",
    }
    
    serialized_requests_json = exec("gen_requests", exec_path, indices)
    
    # Step 2: Deserialize the JSON to get the serialized PirRequests
    requests = json.loads(serialized_requests_json)
    
    # Step 3: Call server scripts to handle the requests
    serialized_response1 = exec("handle_request", exec_path, requests["request1"])
    serialized_response2 = exec("handle_request", exec_path, requests["request2"])
    
    # Step 4: Create a JSON object of the serialized PirResponses
    responses = {
        "response1": serialized_response1,
        "response2": serialized_response2,
    }
    serialized_responses_json = json.dumps(responses)
    
    # Step 5: Get the final answer by processing the PirResponses
    final_answer = exec("handle_responses", exec_path, serialized_responses_json)
    
if __name__ == "__main__":
    main()

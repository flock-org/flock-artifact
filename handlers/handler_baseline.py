from flask import Flask, request, jsonify
import argparse
import handler_util

app = Flask(__name__)

storage_name = "local"

exec_path = {
    "signing": "../internal/cmd/signing/signing",
    "auth_passcode_2PC": "../mpcauth/build/bin/auth_passcode_2PC",
    "auth_passcode_3PC": "../mpcauth/build/bin/auth_passcode_3PC",
    "aes_ctr": "../mpcauth/build/bin/aes_ctr",
    "pir": "../pir/bazel-bin/server_handle_pir_requests_bin"
}

@app.route('/', methods=['POST'])
def handler():
    event = request.json
    
    username = event["username"]
    party_int = str(event["partyInt"])
    
    if party_int == "1":
        bucket_name = f"flock-storage-{username}-1"
    else:
        bucket_name = f"flock-baseline-storage-{username}-{party_int}"
    print("Bucket is:", bucket_name)
    
    response, status_code = handler_util.handler_body(event, bucket_name, storage_name, exec_path)
    return jsonify(response), status_code

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', default=5000)
    args = parser.parse_args()
    app.run(debug=True, host='0.0.0.0', port=args.port)
import handler_util
import json

storage_name = ""

cert_path = "/app/certs"

exec_path = {
    "signing": "/usr/local/bin/signing",
    "auth_passcode_2PC": "/app/mpcauth/build/bin/auth_passcode_2PC",
    "auth_passcode_3PC": "/app/mpcauth/build/bin/auth_passcode_3PC",
    "aes_ctr": "/app/mpcauth/build/bin/aes_ctr",
    "pir": "/app/pir/bazel-bin/server_handle_pir_requests_bin"
}

def lambda_handler(event, context):
    event = json.loads(event["body"])

    storage_name = "aws"
    bucket_name = f"flock-storage"
    
    response, status_code = handler_util.handler_body(event, bucket_name, storage_name, exec_path)
    return {
        'statusCode': status_code,
        'body': json.dumps(response)
    }
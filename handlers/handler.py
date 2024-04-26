from flask import Flask, request, jsonify
import argparse
import handler_util
import socket
import os

app = Flask(__name__)


app.config["STORAGE_NAME"] = None

cert_path = "/app/certs"

exec_path = {
    "signing": "/usr/local/bin/signing",
    "auth_passcode_2PC": "/app/mpcauth/build/bin/auth_passcode_2PC",
    "auth_passcode_3PC": "/app/mpcauth/build/bin/auth_passcode_3PC",
    "aes_ctr": "/app/mpcauth/build/bin/aes_ctr",
    "pir": "/app/pir/bazel-bin/server_handle_pir_requests_bin"
}

@app.route("/tcptest", methods=["POST"])
def tcptest():
    event = request.json

    port = event["port"]
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set the socket to reuse address and ports
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)  # Listen for connections, max 5 clients in the waiting queue
    
    print(f"Server listening on port {port}...", flush=True)
    
    while True:
        # Accept a new client connection
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}", flush=True)
        
        # Send a welcome message
        welcome_message = "Welcome to the server!\n"
        client_socket.send(welcome_message.encode())
        
        # Receive and echo data
        while True:
            data = client_socket.recv(1024)
            if not data:
                # Client has disconnected
                print(f"Connection from {client_address} closed.", flush=True)
                break
            
            print(f"Received data: {data.decode()}", flush=True)
            client_socket.send(data)  # Echo back the received data
        
        client_socket.close()
        break

    return event

@app.route('/', methods=['POST'])
def handler():
    event = request.json
    
    storage_name = os.environ.get("STORAGE")
    bucket_name = f"flock-storage"
    
    response, status_code = handler_util.handler_body(event, bucket_name, storage_name, exec_path)
    return jsonify(response), status_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=443, help='port number to run the server on')
    parser.add_argument('-s', '--storage_name', default="azure", help='which storage type you are using (e.g. aws, gcp, azure, local)')
    args = parser.parse_args()
    port = args.port

    storage_name = os.environ.get("STORAGE")

    app.config["STORAGE_NAME"] = storage_name
    print("Storage:", storage_name)

    if port == 443:
        app.run(debug=True, host='0.0.0.0', port=443, ssl_context=('/app/certs/client.pem', '/app/certs/client.key'))
    else:
        app.run(debug=True, host="0.0.0.0", port=port)
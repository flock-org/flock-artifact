import socket
import requests
import json
import threading
import time
import ssl

cert_path = "../internal/cmd/signing/certs/client.pem"

def start_client(ip, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect to the server
    client_socket.connect((ip, port))
    
    # Receive the welcome message
    welcome_message = client_socket.recv(1024)
    print(f"Server says: {welcome_message.decode()}")
    
    # while True:
    #     # Get user input and send data to the server
    #     message = input("Enter message to send to server (or 'exit' to quit): ")
        
    #     # Check if user wants to exit
    #     if message.lower() == 'exit':
    #         break
        
    #     client_socket.send(message.encode())
        
    #     # Receive and print server response
    #     data = client_socket.recv(1024)
    #     print(f"Server responded with: {data.decode()}")
    
    client_socket.close()
    print("Connection closed.")


def send_post_request(ip, port):
    """
    Send a POST request to a specified URL with provided payload.

    Parameters:
    - port (int): The port number to be included in the payload.
    - username (str): The username to be included in the payload. Default is "data".
    - storage_name (str): The storage name to be included in the payload. Default is "world".
    - partyInt (int): The partyInt to be included in the payload. Default is 1.

    Returns:
    - dict: A dictionary containing the status code and response text.
    """
    # Define the URL and payload data
    url = f"https://{ip}:443/tcptest"
    payload = {
        "port": port,
    }

    # Set the headers
    headers = {
        'Content-Type': 'application/json',
    }

    # # Make the POST request
    # try:
    #     response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)

    #     cert = None
    #     if response.raw.version == 11:  # Check if HTTP/1.1
    #         cert = response.raw._connection.sock.getpeercert(binary_form=True)
    #     print(cert)
    #     return {
    #         "status_code": response.status_code,
    #         "response_text": response.text
    #     }
    # except requests.RequestException as e:
    #     # Handle request errors
    #     return {
    #         "status_code": None,
    #         "response_text": str(e)
    #     }
    

    with requests.Session() as session:
        try:
            # Make the POST request
            response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)
            
            # Check if the connection and sock objects are not None
            # cert = None
            # if response.raw._connection and response.raw._connection.sock:
            #     if response.raw.version == 11:  # Check if HTTP/1.1
            #         cert = response.raw._connection.sock.getpeercert(binary_form=True)
            # print(cert)
            
            return {
                "status_code": response.status_code,
                "response_text": response.text
            }
        except requests.RequestException as e:
            print(f"An error occurred: {str(e)}")
            return {
                "status_code": None,
                "response_text": str(e)
            }

def get_server_certificate(ip):
    """
    Get the server's certificate at the specified URL.
    """
    
    # Establish a connection and retrieve the certificate
    # context = ssl.create_default_context()
    # with socket.create_connection((ip, 443)) as sock:
    #     with context.wrap_socket(sock, server_hostname=ip) as ssock:
    #         cert = ssock.getpeercert(binary_form=True)


    context = ssl._create_unverified_context()
    
    # Establish a connection and retrieve the certificate
    with socket.create_connection((ip, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=ip) as ssock:
            cert = ssock.getpeercert(binary_form=True)
    
    print(ssl.DER_cert_to_PEM_cert(cert))
    return ssl.DER_cert_to_PEM_cert(cert)

if __name__ == "__main__":
    # Set IP and port of the server
    IP = "13.52.182.120"
    PORT = 5001

    get_server_certificate(IP)
    
    # for port in range(5001, 5002):
    #     threading.Thread(target=send_post_request, args=(IP, port,)).start()
    #     # print(send_post_request(IP, port))
    #     print(port)
    #     time.sleep(0.5)
    #     start_client(IP, port)
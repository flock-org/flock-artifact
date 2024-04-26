#ifndef EMP_NETWORK_IO_CHANNEL
#define EMP_NETWORK_IO_CHANNEL

#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include "emp-tool/io/io_channel.h"
using std::string;

#include <unistd.h>
#include <arpa/inet.h>
#include <sys/types.h>
#include <netinet/tcp.h>
#include <netinet/in.h>
#include <sys/socket.h>

#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <condition_variable>
#include <queue>

#include <openssl/ssl.h>
#include <openssl/err.h>

#include "utils/aes.h"
#include "emp-agmpc/cmpc_config.h"
#include "emp-tool/net/client.h"

namespace emp {

class NetIO: public IOChannel<NetIO> { 	
	public:
	bool is_server;
	int mysocket = -1;
	int consocket = -1;
	FILE * stream = nullptr;
	char * buffer = nullptr;
	bool has_sent = false;
	string addr;
	int port;
	std::string enc_key;
	std::string cert_path;

	SSL *ssl;
	SSL_CTX *ctx;

	NetIO(std::string addr, int port, std::string tag, std::string cert_path) {
        struct sockaddr_in dest;
        memset(&dest, 0, sizeof(dest));
        dest.sin_family = AF_INET;
        dest.sin_addr.s_addr = inet_addr(addr.c_str());
        dest.sin_port = htons(port);

        while (1) {
            consocket = socket(AF_INET, SOCK_STREAM, 0);
            if (connect(consocket, (struct sockaddr *)&dest, sizeof(struct sockaddr)) == 0) {
                break;
            }
            close(consocket);
            usleep(1000);
        }
		set_nodelay();
		stream = fdopen(consocket, "wb+");
		buffer = new char[NETWORK_BUFFER_SIZE];
		memset(buffer, 0, NETWORK_BUFFER_SIZE);
		setvbuf(stream, buffer, _IOFBF, NETWORK_BUFFER_SIZE);

		this->cert_path = cert_path;

		initializeSSL();
		upgradeToTLSClient();

        // Send the tag length as a 4-byte integer
        uint32_t tagLen = htonl(static_cast<uint32_t>(tag.length()));
        
		// send(consocket, reinterpret_cast<char *>(&tagLen), sizeof(tagLen), 0);
        // // Send the tag
        // send(consocket, tag.c_str(), tag.length(), 0);

		send_data_internal(reinterpret_cast<char *>(&tagLen), sizeof(tagLen));
		send_data_internal(tag.c_str(), tag.length());

		std::cout << "Connected to channel: " << tag << std::endl;
    }

	// This is the one we are using
	NetIO(const char * address, int port, bool quiet = false, std::string cert_path = "") {
		if (port <0 || port > 65535) {
			throw std::runtime_error("Invalid port number!");
		}

		this->port = port;
		this->cert_path = cert_path;
		is_server = (address == nullptr);
		if (address == nullptr) {
			struct sockaddr_in dest;
			struct sockaddr_in serv;
			socklen_t socksize = sizeof(struct sockaddr_in);
			memset(&serv, 0, sizeof(serv));
			serv.sin_family = AF_INET;
			serv.sin_addr.s_addr = htonl(INADDR_ANY); /* set our address to any interface */
			serv.sin_port = htons(port);           /* set the server port number */
			mysocket = socket(AF_INET, SOCK_STREAM, 0);
			int reuse = 1;
			setsockopt(mysocket, SOL_SOCKET, SO_REUSEADDR, (const char*)&reuse, sizeof(reuse));
			if(bind(mysocket, (struct sockaddr *)&serv, sizeof(struct sockaddr)) < 0) {
				perror("error: bind");
				exit(1);
			}
			if(listen(mysocket, 1) < 0) {
				perror("error: listen");
				exit(1);
			}
			consocket = accept(mysocket, (struct sockaddr *)&dest, &socksize); // File descriptor of socket
			close(mysocket);
		}
		else {
			addr = string(address);

			struct sockaddr_in dest;
			memset(&dest, 0, sizeof(dest));
			dest.sin_family = AF_INET;
			dest.sin_addr.s_addr = inet_addr(address);
			dest.sin_port = htons(port);

			while(1) {
				consocket = socket(AF_INET, SOCK_STREAM, 0);

				if (connect(consocket, (struct sockaddr *)&dest, sizeof(struct sockaddr)) == 0) {
					break;
				}

				close(consocket);
				usleep(1000);
			}
		}
		set_nodelay();
		stream = fdopen(consocket, "wb+");
		buffer = new char[NETWORK_BUFFER_SIZE];
		memset(buffer, 0, NETWORK_BUFFER_SIZE);
		setvbuf(stream, buffer, _IOFBF, NETWORK_BUFFER_SIZE);
		if(!quiet)
			std::cout << "connected\n";
		initializeSSL();
		if (is_server) {
			// Upgrade to TLS server
			upgradeToTLSServer();
		} else {
			// Upgrade to TLS client
			upgradeToTLSClient();
		}
	}

	NetIO(std::string addr, int port, std::string user, int party, int dest, char *tag, std::string cert_path) {
		int conn, mode;
		char partyString[100], destString[100];
		
		sprintf(partyString, "%d", party);
		sprintf(destString, "%d",dest);

		StartRelayAuth(partyString, destString, tag, addr.c_str(), port, cert_path.c_str(), &conn, &mode);

		if (GetSessionE2E(conn, mode, cert_path.c_str(), user.c_str(), partyString, destString, &ssl) != 0) { 
			abort();
		}
	}

	NetIO(std::string addr, int port, int dest, char *tag) {
		int conn, mode;
		char partyString[100], destString[100];

		sprintf(destString, "%d",dest);
		// printf("Starting RelayAuth with certs");
		char *relay_ca = getenv("RELAY_CA");
		char *relay_cert = getenv("RELAY_CERT");
		char *relay_key = getenv("RELAY_KEY");

		char *user_ca = getenv("USER_CA");
		char *party_cert = getenv("PARTY_CERT");
		char *party_key = getenv("PARTY_KEY");
		StartRelayAuthWithCerts(destString, tag, addr.c_str(), port, relay_ca, relay_cert, relay_key, &conn, &mode);

		if (GetSessionE2EWithCerts(conn, mode, user_ca, party_cert, party_key, destString, &ssl) != 0) {
			abort();
		}
	}

	void sync() {
		int tmp = 0;
		if(is_server) {
			send_data_internal(&tmp, 1);
			recv_data_internal(&tmp, 1);
		} else {
			recv_data_internal(&tmp, 1);
			send_data_internal(&tmp, 1);
			flush();
		}
	}

	void initializeSSL() {
        SSL_library_init();
        SSL_load_error_strings();
        OpenSSL_add_all_algorithms();
    }

	void upgradeToTLSServer() {
		ctx = SSL_CTX_new(TLS_server_method());
		std::string cert_file = cert_path + "/client.pem";
		std::string key_file = cert_path + "/client.key";
		if (SSL_CTX_use_certificate_file(ctx, cert_file.c_str(), SSL_FILETYPE_PEM) <= 0) {
			ERR_print_errors_fp(stderr);
			abort();
		}
		if (SSL_CTX_use_PrivateKey_file(ctx, key_file.c_str(), SSL_FILETYPE_PEM) <= 0) {
			ERR_print_errors_fp(stderr);
			abort();
		}
		ssl = SSL_new(ctx);
		SSL_set_fd(ssl, consocket);
		if (SSL_accept(ssl) <= 0) {
			ERR_print_errors_fp(stderr);
		}
	}

	void upgradeToTLSClient() {
		ctx = SSL_CTX_new(TLS_client_method());
		std::string cert_file = cert_path + "/client.pem";
		std::string key_file = cert_path + "/client.key";
		if (SSL_CTX_use_certificate_file(ctx, cert_file.c_str(), SSL_FILETYPE_PEM) <= 0) {
			ERR_print_errors_fp(stderr);
			abort();
		}
		if (SSL_CTX_use_PrivateKey_file(ctx, key_file.c_str(), SSL_FILETYPE_PEM) <= 0) {
			ERR_print_errors_fp(stderr);
			abort();
		}
		ssl = SSL_new(ctx);
		SSL_set_fd(ssl, consocket);
		if (SSL_connect(ssl) <= 0) {
			ERR_print_errors_fp(stderr);
		}
	}

    void send_data_internal(const void * data, size_t len) {
		size_t sent = 0;
		while(sent < len) {
			int res = SSL_write(ssl, (char *)data + sent, len - sent);
			if (res > 0)
				sent += res;
			else
				error("net_send_data\n");
		}
		has_sent = true;
	}

	void recv_data_internal(void * data, size_t len) {
		if(has_sent)
			;  //No flush
		has_sent = false;
		size_t received = 0;
		while(received < len) {
			int res = SSL_read(ssl, (char *)data + received, len - received);
			if (res > 0)
				received += res;
			else
				error("net_recv_data\n");
		}
	}

	~NetIO(){
		SSL_free(ssl);
        SSL_CTX_free(ctx);

		flush();
		fclose(stream);
		delete[] buffer;
	}

	void set_nodelay() {
		const int one=1;
		setsockopt(consocket,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one));
	}

	void set_delay() {
		const int zero = 0;
		setsockopt(consocket,IPPROTO_TCP,TCP_NODELAY,&zero,sizeof(zero));
	}

	void flush() {
		fflush(stream);
	}

};
}
#endif  //NETWORK_IO_CHANNEL

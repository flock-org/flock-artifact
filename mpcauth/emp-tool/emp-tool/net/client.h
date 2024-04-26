#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <malloc.h>
#include <string.h>
#include <sys/socket.h>
#include <resolv.h>
#include <netdb.h>
#include <openssl/ssl.h>
#include <openssl/err.h>

#define FAIL    -1
#define MAX_SIZE 1024

#define TLS_SERVER 1
#define TLS_CLIENT 2

int OpenConnection(const char *hostname, int port)
{   int sd;
    struct hostent *host;
    struct sockaddr_in addr;
 
    if ( (host = gethostbyname(hostname)) == NULL )
    {
        perror(hostname);
        abort();
    }
    sd = socket(PF_INET, SOCK_STREAM, 0);
    bzero(&addr, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = *(long*)(host->h_addr);
    if ( connect(sd, (struct sockaddr*)&addr, sizeof(addr)) != 0 )
    {
        close(sd);
        perror(hostname);
        abort();
    }
    return sd;
}
 
SSL_CTX* InitCTX(void)
{   const SSL_METHOD *method;
    SSL_CTX *ctx;
 
    OpenSSL_add_all_algorithms();  /* Load cryptos, et.al. */
    SSL_load_error_strings();   /* Bring in and register error messages */
    method = SSLv23_client_method();  /* Create new client-method instance */
    ctx = SSL_CTX_new(method);   /* Create new context */
    if ( ctx == NULL )
    {
        ERR_print_errors_fp(stderr);
        abort();
    }
    return ctx;
}

SSL_CTX* InitServerCTX(void)
{   const SSL_METHOD *method;
    SSL_CTX *ctx;
 
    OpenSSL_add_all_algorithms();  /* load & register all cryptos, etc. */
    SSL_load_error_strings();   /* load all error messages */
    method = SSLv23_server_method();  /* create new server-method instance */
    ctx = SSL_CTX_new(method);   /* create new context from method */
    if ( ctx == NULL )
    {
        ERR_print_errors_fp(stderr);
        abort();
    }
    return ctx;
}

int LoadCertificatesFromString(SSL_CTX* ctx, const char *cert_str, const char *key_str) {
    BIO *cert_bio = NULL, *key_bio = NULL;
    X509 *cert = NULL;
    EVP_PKEY *key = NULL;

    // Initialize OpenSSL
    ERR_load_crypto_strings();


    // Create BIOs for certificate and private key
    cert_bio = BIO_new_mem_buf(cert_str, -1);
    key_bio = BIO_new_mem_buf(key_str, -1);

    if (!cert_bio || !key_bio) {
        fprintf(stderr, "Error creating BIOs\n");
        goto cleanup;
    }

    // Load certificate
    cert = PEM_read_bio_X509(cert_bio, NULL, 0, NULL);
    if (!cert) {
        fprintf(stderr, "Error loading certificate\n");
        goto cleanup;
    }

    // Load private key
    key = PEM_read_bio_PrivateKey(key_bio, NULL, 0, NULL);
    if (!key) {
        fprintf(stderr, "Error loading private key\n");
        goto cleanup;
    }

    // Set the certificate and private key
    if (SSL_CTX_use_certificate(ctx, cert) <= 0) {
        fprintf(stderr, "Error setting certificate\n");
        SSL_CTX_free(ctx);
        goto cleanup;
    }

    if (SSL_CTX_use_PrivateKey(ctx, key) <= 0) {
        fprintf(stderr, "Error setting private key\n");
        SSL_CTX_free(ctx);
        goto cleanup;
    }
    // Cleanup
    BIO_free(cert_bio);
    BIO_free(key_bio);
    return 0;

cleanup:
    if (cert_bio) BIO_free(cert_bio);
    if (key_bio) BIO_free(key_bio);
    return -1;
} 

void LoadCertificates(SSL_CTX* ctx, char* CertFile, char* KeyFile)
{
    /* set the local certificate from CertFile */
    if ( SSL_CTX_use_certificate_file(ctx, CertFile, SSL_FILETYPE_PEM) <= 0 )
    {
        ERR_print_errors_fp(stderr);
        abort();
    }
    /* set the private key from KeyFile (may be the same as CertFile) */
    if ( SSL_CTX_use_PrivateKey_file(ctx, KeyFile, SSL_FILETYPE_PEM) <= 0 )
    {
        ERR_print_errors_fp(stderr);
        abort();
    }
    /* verify private key */
    if ( !SSL_CTX_check_private_key(ctx) )
    {
        fprintf(stderr, "Private key does not match the public certificate\n");
        abort();
    }
}
 


int getModeFromResp(char* resp) {
    char *mode;

    char *reply = strtok(resp, ":");
    reply = strtok(NULL,":");
    mode = strtok(reply,"}");
    return atoi(mode);
}

int GetSessionE2E(int conn, int mode, const char *certs_folder, const char *user, const char *name, const char *dest, SSL **ssle2e) {
    char cert[100], key[100], cacert[100];
    SSL_CTX *ctx;
    char *ca_path;
    SSL_library_init();

    if (mode == TLS_CLIENT) {
        ctx = InitCTX();
    } else if (mode == TLS_SERVER) {
        ctx = InitServerCTX();
    }
    sprintf(cacert, "%s/%s/user-ca.pem", certs_folder, user);
    sprintf(cert, "%s/%s/%s/cert.pem", certs_folder, user, name);
    sprintf(key, "%s/%s/%s/key.pem", certs_folder, user, name);
    LoadCertificates(ctx, cert, key); /* load certs */
    if (SSL_CTX_load_verify_locations(ctx, cacert, ca_path) <= 0) {
        ERR_print_errors_fp(stderr);
        return EXIT_FAILURE;
    } 
    *ssle2e = SSL_new(ctx);
    SSL_set_fd(*ssle2e, conn);
    if (mode == TLS_CLIENT) {
        //printf("Setting to ssl connect state\n");
        if ( SSL_connect(*ssle2e) <= 0 ) {
            ERR_print_errors_fp(stderr);
            return EXIT_FAILURE;
        }
    } else if (mode == TLS_SERVER) {
        //printf("Setting to ssl accept state\n");
        if ( SSL_accept(*ssle2e) <= 0 ) {
            ERR_print_errors_fp(stderr);
            return EXIT_FAILURE;
        }
    }
    //printf("Done Handshake\n");
    return 0;
}



int GetSessionE2EWithCerts(int conn, int mode, const char *cacert, const char *cert, const char *key, const char *dest, SSL **ssle2e) {
    SSL_CTX *ctx;
    char *ca_path;
    SSL_library_init();

    if (mode == TLS_CLIENT) {
        ctx = InitCTX();
    } else if (mode == TLS_SERVER) {
        ctx = InitServerCTX();
    }

    LoadCertificatesFromString(ctx, cert, key); /* load certs */
    // if (SSL_CTX_load_verify_locations(ctx, cacert, ca_path) <= 0) {
    //     ERR_print_errors_fp(stderr);
    //     return EXIT_FAILURE;
    // } 
    *ssle2e = SSL_new(ctx);
    SSL_set_fd(*ssle2e, conn);
    if (mode == TLS_CLIENT) {
        // printf("Setting to ssl connect state\n");
        if ( SSL_connect(*ssle2e) <= 0 ) {
            ERR_print_errors_fp(stderr);
            return EXIT_FAILURE;
        }
    } else if (mode == TLS_SERVER) {
        // printf("Setting to ssl accept state\n");
        if ( SSL_accept(*ssle2e) <= 0 ) {
            ERR_print_errors_fp(stderr);
            return EXIT_FAILURE;
        }
    }
    // printf("Done Handshake\n");
    return 0;
}

int StartRelayAuthWithCerts(const char* dest, const char *tag, const char* address, int port, const char *cacert, const char *cert, const char *key, int *conn, int *mode) {
    char json_req[MAX_SIZE];
    char json_resp[MAX_SIZE];
    int bytes;
    SSL *ssl;
    SSL_CTX *ctx;

    SSL_library_init();

    ctx = InitCTX();

    LoadCertificatesFromString(ctx, cert, key); /* load certs */
    *conn = OpenConnection(address, port);
    ssl = SSL_new(ctx);      /* create new SSL connection state */
    SSL_set1_host(ssl, "relay");
    SSL_set_fd(ssl, *conn);    /* attach the socket descriptor */
    if ( SSL_connect(ssl) == FAIL ) {   /* perform the connection */ 
        ERR_print_errors_fp(stderr);
        return EXIT_FAILURE;
    }
    sprintf(json_req,"{\"DestParty\":\"%s\",\"Tag\":\"%s\"}", dest, tag);
    // printf("Sending : %s\n", json_req);

    if (SSL_write(ssl, json_req, strlen(json_req)) == -1)
    {
        perror("write");
        return EXIT_FAILURE;
    }

    bytes = SSL_read(ssl, json_resp, sizeof(json_resp)-1); /* get reply & decrypt */
    json_resp[bytes] = 0;
    if (bytes <= 0) {
        ERR_print_errors_fp(stderr);
        return EXIT_FAILURE;
    }
    //printf("Reply from relay: %s\n", json_resp);
    *mode = getModeFromResp(json_resp);
    bytes = SSL_read(ssl, json_resp, sizeof(json_resp));
    return 0;
}

int StartRelayAuth(const char* name, const char* dest, const char *tag, const char* address, int port, const char *certs_folder, int *conn, int *mode) {
    char cert[100], key[100];
    char json_req[MAX_SIZE];
    char json_resp[MAX_SIZE];
    int bytes;
    SSL *ssl;
    SSL_CTX *ctx;

    SSL_library_init();

    ctx = InitCTX();
    sprintf(cert, "%s/%s/cert.pem", certs_folder, name);
    sprintf(key, "%s/%s/key.pem", certs_folder, name);

    LoadCertificates(ctx, cert, key); /* load certs */
    *conn = OpenConnection(address, port);
    ssl = SSL_new(ctx);      /* create new SSL connection state */
    SSL_set1_host(ssl, "relay");
    SSL_set_fd(ssl, *conn);    /* attach the socket descriptor */
    if ( SSL_connect(ssl) == FAIL ) {   /* perform the connection */ 
        ERR_print_errors_fp(stderr);
        return EXIT_FAILURE;
    }

    sprintf(json_req,"{\"DestParty\":\"%s\",\"Tag\":\"%s\"}", dest, tag);
    // printf("Sending : %s\n", json_req);

    if (SSL_write(ssl, json_req, strlen(json_req)) == -1)
    {
        perror("write");
        return EXIT_FAILURE;
    }

    bytes = SSL_read(ssl, json_resp, sizeof(json_resp)-1); /* get reply & decrypt */
    json_resp[bytes] = 0;
    if (bytes <= 0) {
        ERR_print_errors_fp(stderr);
        return EXIT_FAILURE;
    }
   // printf("Reply from relay: %s\n", json_resp);
    *mode = getModeFromResp(json_resp);
    bytes = SSL_read(ssl, json_resp, sizeof(json_resp));
    return 0;
}

#include "../clib/client.h"

char *CERTS_FOLDER="certs";

void ShowCerts(SSL* ssl)
{   X509 *cert;
    char *line;
 
    cert = SSL_get_peer_certificate(ssl); /* get the server's certificate */
    if ( cert != NULL )
    {
        printf("Server certificates:\n");
        line = X509_NAME_oneline(X509_get_subject_name(cert), 0, 0);
        printf("Subject: %s\n", line);
        free(line);       /* free the malloc'ed string */
        line = X509_NAME_oneline(X509_get_issuer_name(cert), 0, 0);
        printf("Issuer: %s\n", line);
        free(line);       /* free the malloc'ed string */
        X509_free(cert);     /* free the malloc'ed certificate copy */
    }
    else
        printf("No certificates.\n");
}

int main(int count, char *strings[])
{
    int conn, mode;
    SSL *ssle2e;
    char buf[1024];
    int bytes;
    char *hostname, *portnum;
    char msg[] = "hello";

    char *target = getenv("RELAY");
    char *name = getenv("NAME");
    char *dest = getenv("DEST");
    char *user = getenv("USER");
    char *tag = getenv("TAG");

    char *relay_ca = getenv("RELAY_CA");
    char *relay_cert = getenv("RELAY_CERT");
    char *relay_key = getenv("RELAY_KEY");

    char *user_ca = getenv("USER_CA");
    char *party_cert = getenv("PARTY_CERT");
    char *party_key = getenv("PARTY_KEY");

    hostname = strtok(target, ":");
    portnum = strtok(NULL, ":");
    printf("Connecting to %s:%s!!\n", hostname, portnum);

    StartRelayAuthWithCerts(dest, tag, hostname, atoi(portnum), relay_ca, relay_cert, relay_key, &conn, &mode);

    printf("Established Auth, mode =%d\n", mode);

    if (GetSessionE2EWithCerts(conn, mode, user_ca, party_cert, party_key, dest, &ssle2e) != 0) {
        return FAIL;
    }

    // StartRelayAuth(name, dest, tag, hostname, atoi(portnum), CERTS_FOLDER, &conn, &mode);

    // printf("Established Auth, mode =%d\n", mode);

    // if (GetSessionE2E(conn, mode, CERTS_FOLDER, user, name, dest, &ssle2e) != 0) {
    //     return FAIL;
    // }
    printf("Connected with Party!\n");
    ShowCerts(ssle2e);

    while (1) {
        bytes = SSL_write(ssle2e, msg, strlen(msg));
        printf("Written %d bytes, errno =%d\n",bytes, errno);
        SSL_read(ssle2e, buf, sizeof(buf));
        printf("RECV:%s\n", buf);
        sleep(1);
    }
    return 0;
}
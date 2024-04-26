package clientssl

import (
	"encoding/json"
	"log"
	"net"
	"path/filepath"

	"github.com/praveingk/openssl"

	"github.com/relay/config"
	"github.com/relay/pkg/api"
)

var (
	maxDataBufferSize = 64 * 1024
)

func sslClient(conn net.Conn, cacert, cert, key string) (*openssl.Conn, error) {
	ctx, err := openssl.NewCtxFromFiles(cert, key)
	if err != nil {
		log.Fatal(err)
	}
	ctx.LoadVerifyLocations(cacert, "")

	sslConn, err := openssl.Client(conn, ctx)
	if err != nil {
		log.Printf("Failed to connect to socket %+v", err)
		return nil, err
	}
	err = sslConn.Handshake()
	if err != nil {
		log.Printf("Failed handshake %+v", err)
		return nil, err
	}
	log.Printf("Connected to %s:%s", sslConn.LocalAddr().String(), sslConn.RemoteAddr().String())
	return sslConn, nil
}

func sslServer(conn net.Conn, cacert, cert, key string) (*openssl.Conn, error) {
	log.Printf("Starting ssl server")
	ctx, err := openssl.NewCtxFromFiles(cert, key)
	if err != nil {
		return nil, err
	}
	ctx.LoadVerifyLocations(cacert, "")

	sslConn, err := openssl.Server(conn, ctx)
	if err != nil {
		log.Printf("Failed to connect to socket %v", err)
		return nil, err
	}
	err = sslConn.Handshake()
	if err != nil {
		log.Printf("Failed handshake : %v", err)
		return nil, err
	}
	log.Printf("Connected to %s:%s \n", sslConn.LocalAddr().String(), sslConn.RemoteAddr().String())
	return sslConn, nil
}

func requestAuth(conn *openssl.Conn, req api.AuthReq) (*api.Ready, error) {
	readyResp := &api.Ready{}
	bufData := make([]byte, maxDataBufferSize)
	authData, err := json.Marshal(req)
	if err != nil {
		log.Printf("Failed to marshal auth request: %v.", err)
		return nil, err
	}
	log.Printf("Requesting auth: %v. Waiting..", req)
	conn.Write(authData)
	numBytes, err := conn.Read(bufData)
	if err != nil {
		log.Printf("Read error %v\n", err)
		return nil, err
	}
	err = json.Unmarshal(bufData[:numBytes], readyResp)
	if err != nil {
		log.Printf("Failed to unmarshal auth request: %s", err)
		return nil, err
	}
	return readyResp, nil
}

func GetSessionE2E(tcpConn net.Conn, ready *api.Ready, user, party, dest string) (*openssl.Conn, error) {
	log.Printf("Starting E2E TLS Connection (with mode %d) for user %s, with dest %s", ready.Mode, user, dest)
	partyDirectory := config.UserPartyDirectory(user, party)
	userDirectory := config.UserDirectory(user)

	if ready.Mode == api.TLSModeClient {
		return sslClient(tcpConn,
			filepath.Join(userDirectory, config.UserCAFile),
			filepath.Join(partyDirectory, config.CertificateFileName),
			filepath.Join(partyDirectory, config.PrivateKeyFileName))
	}
	return sslServer(tcpConn, filepath.Join(userDirectory, config.UserCAFile),
		filepath.Join(partyDirectory, config.CertificateFileName),
		filepath.Join(partyDirectory, config.PrivateKeyFileName))
}

func StartRelayAuth(name, dest, relay string) (net.Conn, *openssl.Conn, *api.Ready, error) {
	log.Printf("Connecting to Frelay %s", relay)
	tcpConn, err := net.Dial("tcp", relay)
	if err != nil {
		log.Printf("Failed to connect to socket %+v", err)
		return nil, nil, nil, err
	}
	log.Printf("Connected to %s:%s \n", tcpConn.LocalAddr().String(), tcpConn.RemoteAddr().String())

	// TODO @praveingk: Need to check regarding using party's SNI.

	var sslConn *openssl.Conn

	sslConn, err = sslClient(tcpConn, config.FrCAFile,
		filepath.Join(config.PartyDirectory(name), config.CertificateFileName),
		filepath.Join(config.PartyDirectory(name), config.PrivateKeyFileName))

	authReq := api.AuthReq{DestParty: dest}
	readyResp, err := requestAuth(sslConn, authReq)
	if err != nil {
		log.Printf("Failed authorization: %v.", err)
		return nil, nil, nil, err
	}
	log.Printf("Received ready from frelay, Mode = %d\n", readyResp.Mode)

	return tcpConn, sslConn, readyResp, nil
}

package client

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"log"
	"net"
	"path/filepath"
	"time"

	"github.com/relay/config"
	"github.com/relay/pkg/api"
)

var (
	maxDataBufferSize = 64 * 1024
	readDeadline      = 500 * time.Millisecond
)

func tlsClient(conn net.Conn, parsedCertData *parsedCertData, sni string) (*tls.Conn, error) {
	// log.Printf("Upgrading the connection to TLS Client(%+v), SNI=%s", parsedCertData.DNSNames(), sni)
	var err error
	ctx := context.TODO()

	tlsConn := tls.Client(conn, parsedCertData.ClientConfig(sni))
	err = tlsConn.HandshakeContext(ctx)
	if err != nil {
		log.Fatalf("failed to perform handshake : %+v", err)
		return nil, err
	}
	// log.Printf("Handshake complete")
	return tlsConn, nil
}

func tlsServer(conn net.Conn, parsedCertData *parsedCertData) (*tls.Conn, error) {
	// log.Printf("Upgrading the connection to TLS Server(%+v)", parsedCertData.DNSNames())
	var err error
	ctx := context.TODO()
	tlsConn := tls.Server(conn, parsedCertData.ServerConfig())
	err = tlsConn.HandshakeContext(ctx)
	if err != nil {
		log.Fatalf("failed to perform handshake : %+v", err)
		return nil, err
	}
	// log.Printf("Handshake complete")
	return tlsConn, nil
}

func GetSessionE2EGo(tcpConn net.Conn, ready *api.Ready, user, party, dest string) (*tls.Conn, error) {
	// log.Printf("Starting E2E TLS Connection (with mode %d) for user %s, with dest %s", ready.Mode, user, dest)
	partyDirectory := config.UserPartyDirectory(user, party)
	userDirectory := config.UserDirectory(user)

	parsedCertData, _ := parseTLSFiles(filepath.Join(userDirectory, config.UserCAFile),
		filepath.Join(partyDirectory, config.CertificateFileName),

		filepath.Join(partyDirectory, config.PrivateKeyFileName))
	if ready.Mode == api.TLSModeClient {
		return tlsClient(tcpConn, parsedCertData, dest)
	}
	return tlsServer(tcpConn, parsedCertData)
}

func requestAuthGo(conn *tls.Conn, req api.AuthReq) (*api.Ready, error) {
	readyResp := &api.Ready{}
	bufData := make([]byte, maxDataBufferSize)
	authData, err := json.Marshal(req)
	if err != nil {
		log.Printf("Failed to marshal auth request: %v.", err)
		return nil, err
	}
	// log.Printf("Requesting auth: %v. Waiting..", req)
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
	// Read the CloseNotify on the TLS connection
	// Set a deadline so that we are not blocked in this step, and we can retry.
	err = conn.SetReadDeadline(time.Now().Add(readDeadline))
	if err != nil {
		return nil, err
	}
	_, err = conn.Read(bufData)
	if err1, ok := err.(net.Error); ok && err1.Timeout() {
		return nil, err
	}

	// Reset Deadline for future reads, Let application decide to set deadline
	conn.SetReadDeadline(time.Time{})
	// log.Printf("Expected EOF on TLS conn and got: %v", err)
	return readyResp, nil
}

func StartRelayAuthGo(name, dest, tag, relay string) (net.Conn, *tls.Conn, *api.Ready, error) {
	// log.Printf("Connecting to Frelay %s", relay)
	tcpConn, err := net.Dial("tcp", relay)
	if err != nil {
		log.Printf("Failed to connect to socket %+v", err)
		return nil, nil, nil, err
	}

	parsedCertData, err := parseTLSFiles(config.FrCAFile,
		filepath.Join(config.PartyDirectory(name), config.CertificateFileName),
		filepath.Join(config.PartyDirectory(name), config.PrivateKeyFileName))
	if err != nil {
		log.Printf("Parse TLS files %+v", err)
		return nil, nil, nil, err
	}
	// TODO @praveingk: Need to check regarding using party's SNI.

	var tlsConn *tls.Conn

	tlsConn, err = tlsClient(tcpConn, parsedCertData, "frelay")

	authReq := api.AuthReq{DestParty: dest, Tag: tag}
	readyResp, err := requestAuthGo(tlsConn, authReq)
	if err != nil {
		log.Printf("Failed authorization: %v.", err)
		return nil, nil, nil, err
	}
	// log.Printf("Received ready from frelay, Mode = %d\n", readyResp.Mode)

	return tcpConn, tlsConn, readyResp, nil
}

func StartRelayAuthWithCerts(dest, tag, relay, cacert, cert, key string) (net.Conn, *tls.Conn, *api.Ready, error) {
	// log.Printf("Connecting to Frelay %s", relay)
	tcpConn, err := net.Dial("tcp", relay)
	if err != nil {
		log.Printf("Failed to connect to socket %+v", err)
		return nil, nil, nil, err
	}
	// log.Printf("Connected to %s:%s \n", tcpConn.LocalAddr().String(), tcpConn.RemoteAddr().String())

	parsedCertData, err := parseTLSStrings(cacert, cert, key)
	if err != nil {
		log.Printf("Parse TLS files %+v", err)
		return nil, nil, nil, err
	}
	// TODO @praveingk: Need to check regarding using party's SNI.

	var tlsConn *tls.Conn

	tlsConn, err = tlsClient(tcpConn, parsedCertData, "frelay")

	authReq := api.AuthReq{DestParty: dest, Tag: tag}
	readyResp, err := requestAuthGo(tlsConn, authReq)
	if err != nil {
		log.Printf("Failed authorization: %v.", err)
		return nil, nil, nil, err
	}
	// log.Printf("Received ready from frelay, Mode = %d\n", readyResp.Mode)

	return tcpConn, tlsConn, readyResp, nil
}

func GetSessionE2EGoWithCerts(tcpConn net.Conn, ready *api.Ready, dest, cacert, cert, key string) (*tls.Conn, error) {
	// log.Printf("Starting E2E TLS Connection (with mode %d) with dest %s", ready.Mode, dest)

	parsedCertData, _ := parseTLSStrings(cacert, cert, key)
	if ready.Mode == api.TLSModeClient {
		return tlsClient(tcpConn, parsedCertData, dest)
	}
	return tlsServer(tcpConn, parsedCertData)
}

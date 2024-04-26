package server

import (
	"encoding/json"
	"net"

	"github.com/praveingk/openssl"

	"github.com/relay/pkg/api"
)

func (s *Server) authorize(srcParty string, tcpConn net.Conn, tlsConn *openssl.Conn) error {
	authReq := api.AuthReq{}
	buf := make([]byte, 512)
	//partyHandshake := time.Now()

	n, err := tlsConn.Read(buf)
	if err != nil {
		s.logger.Errorf("Failed to read auth request: %s", err)
		return err
	}
	err = json.Unmarshal(buf[:n], &authReq)
	if err != nil {
		s.logger.Errorf("Failed to unmarshal auth request: %s", err)
		return err
	}

	dstConn, err := s.states.GetConnection(authReq.DestParty, srcParty, authReq.Tag)
	if err != nil {
		//s.logger.Infof("Destination party doesnt have an active connection, Waiting")
		//s.logger.Infof("Storing the tcp connection for %s:%s (%s) comms", srcParty, authReq.DestParty, authReq.Tag)
		s.states.StoreTLSConnection(srcParty, authReq.DestParty, authReq.Tag, tlsConn)
		err = s.states.StoreConnection(srcParty, authReq.DestParty, authReq.Tag, tcpConn)
		if err != nil {
			return err
		}
		// go func() {
		// 	connKey := connection{party1: srcParty, party2: authReq.DestParty, tag: authReq.Tag}
		// 	s.timelineMutex.Lock()
		// 	s.relayTimeline[connKey] = &timeline{party1Incoming: incomingConn[tcpConn.RemoteAddr().String()],
		// 		party1Handshake: partyHandshake, party1Auth: time.Now()}
		// 	s.timelineMutex.Unlock()
		// }()
		return nil
	}
	//party2Auth := time.Now()

	destTLSConn, err := s.states.GetTLSConnection(authReq.DestParty, srcParty, authReq.Tag)
	if err != nil {
		return err
	}
	//s.logger.Infof("Ending the TLS Connections(%s, %s, %s) and start TCP forwarding", authReq.DestParty, srcParty, authReq.Tag)
	s.sendReady(tlsConn, api.Ready{Mode: api.TLSModeServer})
	// To synchronize the TLS connections, we wait for the ACK and proceed to next server
	s.sendReady(destTLSConn, api.Ready{Mode: api.TLSModeClient})

	go s.startForwarding(srcParty, tcpConn, tlsConn, authReq.DestParty, dstConn, destTLSConn, authReq.Tag)
	// go func() {
	// 	connKey := connection{party1: authReq.DestParty, party2: srcParty, tag: authReq.Tag}
	// 	s.timelineMutex.Lock()
	// 	s.relayTimeline[connKey].SetupConn = time.Now()
	// 	s.relayTimeline[connKey].party2Auth = party2Auth
	// 	s.relayTimeline[connKey].party2Incoming = incomingConn[tcpConn.RemoteAddr().String()]
	// 	s.relayTimeline[connKey].party2Handshake = partyHandshake
	// 	s.timelineMutex.Unlock()
	// }()

	return nil
}

func (s *Server) sendReady(conn *openssl.Conn, ready api.Ready) error {
	buf := make([]byte, 512)

	readyData, err := json.Marshal(ready)
	if err != nil {
		s.logger.Errorf("Failed to marshal ready response: %v.", err)
	}
	_, err = conn.Write(readyData)
	if err != nil {
		s.logger.Errorf("Failed to write send ready: %s", err)
		return err
	}
	conn.CloseSSL()
	_, err = conn.Read(buf)
	//s.logger.Infof("Ready and closed SSL")
	return nil
}

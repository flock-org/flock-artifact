package server

import (
	"fmt"
	"net"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/go-chi/chi"
	"github.com/praveingk/openssl"
	"github.com/sirupsen/logrus"

	cutil "github.com/clusterlink-net/clusterlink/pkg/util"
	"github.com/relay/config"
	"github.com/relay/pkg/store"

	"github.com/relay/pkg/util"
)

var (
	maxDataBufferSize = 64 * 1024
)

type Server struct {
	router         *chi.Mux
	parsedCertData *cutil.ParsedCertData
	states         *store.State
	//relayTimeline  map[connection]*timeline
	timelineMutex sync.Mutex
	logger        *logrus.Entry
	f1            *os.File
	f2            *os.File
}

type connection struct {
	party1 string
	party2 string
	tag    string
}

type timeline struct {
	party1Incoming  time.Time //Got an incoming connection
	party2Incoming  time.Time
	party1Handshake time.Time
	party2Handshake time.Time
	party1Auth      time.Time
	party2Auth      time.Time
	StartConn       time.Time
	SetupConn       time.Time
}

var incomingConn map[string]time.Time

func (s *Server) startForwarding(srcParty string, conn1 net.Conn, sslConn1 *openssl.Conn, dstParty string, conn2 net.Conn, sslConn2 *openssl.Conn, tag string) {
	forwarder := newForwarder(conn1, conn2)
	b1, b2 := forwarder.run()
	s.logger.Infof("Forwarding finished for %s:%s(%s), bytes transferred(%d, %d)", srcParty, dstParty, tag, b1, b2)
	sslConn1.Close()
	sslConn2.Close()
	s.states.RemoveConnection(srcParty, dstParty, tag)
	s.states.RemoveConnection(dstParty, srcParty, tag)
	s.states.RemoveTLSConnection(srcParty, dstParty, tag)
	s.states.RemoveTLSConnection(dstParty, srcParty, tag)
	//timeline := s.relayTimeline[connection{party1: dstParty, party2: srcParty, tag: tag}]
	//go s.DumpTimelineInfo(connection{party1: dstParty, party2: srcParty, tag: tag}, *timeline)
	//s.timelineMutex.Lock()
	//delete(s.relayTimeline, connection{party1: dstParty, party2: srcParty, tag: tag})
	//s.timelineMutex.Unlock()

	//s.states.Dump()
}

func (s *Server) receiveWaitAndForward(address string, ctx *openssl.Ctx) error {
	acceptor, err := net.Listen("tcp", address)
	if err != nil {
		s.logger.Errorln("Error:", err)
		return err
	}

	for {
		tcpConn, err := acceptor.Accept()
		if err != nil {
			s.logger.Errorln("Accept error:", err)
			continue
		}
		tlsConn, err := openssl.Server(tcpConn, ctx)
		err = tlsConn.Handshake()
		if err != nil {
			s.logger.Errorf("Handshake failed: %v.", err)
			tlsConn.Close()
			continue
		}
		s.logger.Info("Accept incoming connection from ", tlsConn.RemoteAddr().String())
		reqParty, err := util.GetPartyName(tlsConn)
		if err != nil {
			s.logger.Errorf("Failed to get party name: %v.", err)
			tlsConn.Close()
			continue
		}
		s.logger.Infof("Got connection from %s requesting access to %s", reqParty, tlsConn.GetServername())

		err = s.authorize(reqParty, tcpConn, tlsConn)
		if err != nil {
			s.logger.Errorf("Failed to authorize %s; %v", reqParty, err)
			tlsConn.Close()
			continue
		}
	}
}

// StartRelaySSLServer starts the Frelay dataplane server which listens to connections from the user's parties (or functions)
func (s *Server) StartRelaySSLServer(port string) error {
	defer s.f1.Close()
	defer s.f2.Close()
	address := fmt.Sprintf(":%s", port)
	s.logger.Info("Starting relay... Listening to ", address, " for connections")
	ctx, err := openssl.NewCtxFromFiles(filepath.Join(config.FrelayCADirectory(), config.CertificateFileName),
		filepath.Join(config.FrelayCADirectory(), config.PrivateKeyFileName))
	if err != nil {
		s.logger.Fatal(err)
	}
	ctx.LoadVerifyLocations(config.FrCAFileRoot, "")
	ctx.SetVerifyMode(openssl.VerifyPeer)
	//incomingConn = make(map[string]time.Time)
	//s.relayTimeline = make(map[connection]*timeline)
	return s.receiveWaitAndForward(address, ctx)
}

func (s *Server) InitTimelineInfo() {
	var err error
	s.logger.Infof("Init Timeline")
	s.f1, err = os.OpenFile("timeline.log", os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		fmt.Errorf("error opening log file: %v", err.Error())
	}
	s.f2, err = os.OpenFile("timeline-dur.log", os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		fmt.Errorf("error opening log file: %v", err.Error())
	}

	s.f1.WriteString("Connection, Party1Incoming, Party1Handshake, Party1Auth, Party2Incoming, Party2Handshake, Party2Auth, SetupConn\n")
	s.f2.WriteString("Connection, party1AuthTime, party2AuthTime, interarrivalTime, sslShutdownTime(us), setupTimeForParty1, setupTimeForParty2\n")

}
func (s *Server) DumpTimelineInfo(conn connection, timeline timeline) {
	s.logger.Infof("Dumping Timeline")

	line := fmt.Sprintf("%v, %v, %v, %v, %v, %v, %v, %v \n", conn,
		timeline.party1Incoming.UnixMilli(), timeline.party1Handshake.UnixMilli(), timeline.party1Auth.UnixMilli(),
		timeline.party2Incoming.UnixMilli(), timeline.party2Handshake.UnixMilli(), timeline.party2Auth.UnixMilli(),
		timeline.SetupConn.UnixMilli())
	s.f1.WriteString(line)

	party1AuthTime := timeline.party1Auth.Sub(timeline.party1Incoming).Milliseconds()
	party2AuthTime := timeline.party2Auth.Sub(timeline.party2Incoming).Milliseconds()

	interarrivalTime := timeline.party2Incoming.Sub(timeline.party1Incoming).Milliseconds()
	sslShutdownTime := timeline.SetupConn.Sub(timeline.party2Auth).Microseconds()
	setupTimeForParty1 := timeline.SetupConn.Sub(timeline.party1Incoming).Milliseconds()
	setupTimeForParty2 := timeline.SetupConn.Sub(timeline.party2Incoming).Milliseconds()

	line = fmt.Sprintf("%v, %v, %v, %v, %v, %v, %v \n", conn,
		party1AuthTime, party2AuthTime,
		interarrivalTime, sslShutdownTime,
		setupTimeForParty1, setupTimeForParty2,
	)
	s.f2.WriteString(line)
	s.f1.Sync()
	s.f2.Sync()
}

func (s *Server) MonitorConnections() {
	for {
		s.logger.Infof("Active Connections : %d", s.states.Conns())
		time.Sleep(1 * time.Second)
	}
}

// NewRelay returns a new dataplane HTTP server.
func NewRelay(parsedCertData *cutil.ParsedCertData) *Server {
	s := &Server{
		router:         chi.NewRouter(),
		parsedCertData: parsedCertData,
		states:         store.GetState(),
		logger:         logrus.WithField("component", "server.relay"),
	}
	return s
}

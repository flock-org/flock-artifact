package core

import (
	"github.com/clusterlink-net/clusterlink/pkg/util"
	"github.com/sirupsen/logrus"

	"github.com/relay/pkg/server"
)

var clog = logrus.WithField("component", "relay-core")
var queueSize = 100

var localhost = "127.0.0.1"

// Relay struct defines the properties of the relay
type Relay struct {
	url      string
	DPServer *server.Server
}

// StartRelay starts the main function of the relay
func (r *Relay) StartRelay(parsedCertData *util.ParsedCertData, port string) error {
	//err := r.tcpUpgradeServer()
	r.DPServer = server.NewRelay(parsedCertData)
	//r.DPServer.InitTimelineInfo()
	go r.DPServer.MonitorConnections()
	err := r.DPServer.StartRelaySSLServer(port)

	return err
}

// Init initializes the relay
func (r *Relay) Init(ip, port string, loglevel logrus.Level) {
	r.url = ip + ":" + port
	clog.Logger.SetLevel(loglevel)
	clog.Logger.SetFormatter(&logrus.TextFormatter{
		DisableColors: true,
		FullTimestamp: true,
	})
}

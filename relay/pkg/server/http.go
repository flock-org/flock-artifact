package server

import (
	"fmt"

	"github.com/clusterlink-net/clusterlink/pkg/util"
	cutil "github.com/clusterlink-net/clusterlink/pkg/util"
	"github.com/clusterlink-net/clusterlink/pkg/utils/netutils"
	"github.com/go-chi/chi"
	"github.com/sirupsen/logrus"
)

type APIServer struct {
	router         *chi.Mux
	parsedCertData *util.ParsedCertData
	logger         *logrus.Entry
}

// StartFlockAPIServer starts the Dataplane server
func (s *APIServer) StartFlockAPIServer() error {
	address := fmt.Sprintf(":%d", apiPort)
	s.logger.Infof("Flock API server starting at %s.", address)
	server := netutils.CreateResilientHTTPServer(address, s.router, s.parsedCertData.ServerConfig(), nil, nil, nil)

	return server.ListenAndServeTLS("", "")
}

func (s *APIServer) addAPIHandlers() {
	s.router.Route("/user", func(r chi.Router) {
		s.router.Get("/", s.addUser)
		s.router.Post("/", s.addUser)
	})
	s.router.Mount("/", s.router)
}

func NewAPIServer(parsedCertData *cutil.ParsedCertData) *APIServer {
	s := &APIServer{
		router:         chi.NewRouter(),
		parsedCertData: parsedCertData,
		logger:         logrus.WithField("component", "server.frelay"),
	}

	s.addAPIHandlers()

	return s
}

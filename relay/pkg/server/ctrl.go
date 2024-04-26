package server

import (
	"encoding/json"
	"net/http"

	"github.com/relay/pkg/api"
)

// APIs for management
func (s *APIServer) addUser(w http.ResponseWriter, r *http.Request) {
	var userReq api.UserReq
	defer r.Body.Close()
	err := json.NewDecoder(r.Body).Decode(&userReq)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	s.logger.Infof("Got a user requests")
	w.WriteHeader(http.StatusOK)
}

package store

import (
	"fmt"
	"log"
	"net"
	"sync"

	"github.com/praveingk/openssl"
)

// State stores all the connection states in the store
type State struct {
	tlsMutex  sync.RWMutex
	openMutex sync.RWMutex
	openConns map[string]net.Conn      // SrcParty:DstParty -> Sockets mapping
	tlsConns  map[string]*openssl.Conn // SrcParty -> Open TLS connections
}

var state State

func getKey(srcParty, dstParty, tag string) string {
	return srcParty + ":" + dstParty + ":" + tag
}

// StoreConnection stores the connection between srcParty->dstParty
func (s *State) StoreConnection(srcParty string, dstParty string, tag string, conn net.Conn) error {
	key := getKey(srcParty, dstParty, tag)
	if _, exists := s.openConns[key]; exists {
		return fmt.Errorf("connection already exists")
	}
	s.openMutex.Lock()
	s.openConns[key] = conn
	s.openMutex.Unlock()
	return nil
}

// GetConnection gets the connection between srcParty->dstParty
func (s *State) GetConnection(srcParty, dstParty, tag string) (net.Conn, error) {
	key := getKey(srcParty, dstParty, tag)
	s.openMutex.RLock()
	if conn, exists := s.openConns[key]; exists {
		s.openMutex.RUnlock()
		return conn, nil
	}
	s.openMutex.RUnlock()
	return nil, fmt.Errorf("no open connections")
}

// RemoveConnection gets the original TLS connection of srcParty
func (s *State) RemoveConnection(srcParty, dstParty, tag string) {
	key := getKey(srcParty, dstParty, tag)
	s.openMutex.Lock()
	delete(s.openConns, key)
	s.openMutex.Unlock()
}

// StoreTLSConnection stores the original TLS connection of srcParty->dstParty
func (s *State) StoreTLSConnection(srcParty, dstParty, tag string, conn *openssl.Conn) error {
	key := getKey(srcParty, dstParty, tag)
	if _, exists := s.tlsConns[key]; exists {
		return fmt.Errorf("TLS connection already exists")
	}
	s.tlsMutex.Lock()
	s.tlsConns[key] = conn
	s.tlsMutex.Unlock()

	return nil
}

// GetTLSConnection gets the original TLS connection of srcParty-> dstParty
func (s *State) GetTLSConnection(srcParty, dstParty, tag string) (*openssl.Conn, error) {
	key := getKey(srcParty, dstParty, tag)
	s.tlsMutex.RLock()
	if conn, exists := s.tlsConns[key]; exists {
		s.tlsMutex.RUnlock()
		return conn, nil
	}
	s.tlsMutex.RUnlock()
	return nil, fmt.Errorf("Already existing connection from same party")
}

// RemoveTLSConnection gets the original TLS connection of srcParty
func (s *State) RemoveTLSConnection(srcParty, dstParty, tag string) {
	key := getKey(srcParty, dstParty, tag)
	s.tlsMutex.Lock()
	delete(s.tlsConns, key)
	s.tlsMutex.Unlock()
}

// Dump prints the existing open connections
func (s *State) Dump() {
	log.Printf("Open Connections : %+v", s.openConns)
}

func (s *State) Conns() int {
	return len(s.openConns)
}

// GetState initializes the state
func GetState() *State {
	state := &State{
		openConns: make(map[string]net.Conn),
		tlsConns:  make(map[string]*openssl.Conn),
	}
	return state
}

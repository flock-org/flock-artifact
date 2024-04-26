package networking

import (
	"bufio"
	"crypto/tls"
	"encoding/binary"
	"net"
	"sync"
)

type Communicator interface {
	Send(dst int, msg []byte) (int, error)
	Recv(src int) ([]byte, int, error)
	Close() error
}

type P2PComm struct {
	Socks map[int]*net.Conn
	Rank  int
}

type TLSComm struct {
	Socks map[int]*tls.Conn
	Rank  int
}

var sendLocks = make([]sync.Mutex, 10)
var recvLocks = make([]sync.Mutex, 10)

func (comm P2PComm) Send(dst int, msg []byte) (int, error) {
	sendLocks[dst].Lock()
	defer sendLocks[dst].Unlock()

	// Create a buffered writer for the connection
	writer := bufio.NewWriter(*comm.Socks[dst])

	// Prefix each message with a 4-byte length (network byte order)
	length := make([]byte, 4)
	binary.BigEndian.PutUint32(length, uint32(len(msg)))

	// Write the message length and data to the buffered writer
	n, err := writer.Write(length)
	if err != nil {
		return 0, err
	}
	totalBytesSent := n
	n, err = writer.Write(msg)
	if err != nil {
		return 0, err
	}
	totalBytesSent += n

	// Flush the buffered writer to ensure that the data is sent
	err = writer.Flush()
	if err != nil {
		return 0, err
	}

	return totalBytesSent, nil
}

func (comm P2PComm) Recv(src int) ([]byte, int, error) {
	recvLocks[src].Lock()
	defer recvLocks[src].Unlock()

	// Read the message length
	lengthBuf := make([]byte, 4)
	n, err := (*comm.Socks[src]).Read(lengthBuf)
	if err != nil {
		return nil, 0, err
	}
	length := binary.BigEndian.Uint32(lengthBuf)
	totalBytesRead := n

	// Read the message data
	data := make([]byte, length)
	bytesRead := 0
	for bytesRead < int(length) {
		n, err := (*comm.Socks[src]).Read(data[bytesRead:])
		if err != nil {
			return nil, 0, err
		}
		bytesRead += n
		totalBytesRead += n
	}

	return data, totalBytesRead, nil
}

func (comm P2PComm) Close() error {
	for _, sock := range comm.Socks {
		err := (*sock).Close()
		if err != nil {
			return err
		}
	}
	return nil
}

func (comm TLSComm) Send(dst int, msg []byte) (int, error) {
	sendLocks[dst].Lock()
	defer sendLocks[dst].Unlock()

	// Create a buffered writer for the connection
	writer := bufio.NewWriter(comm.Socks[dst])

	// Prefix each message with a 4-byte length (network byte order)
	length := make([]byte, 4)
	binary.BigEndian.PutUint32(length, uint32(len(msg)))

	// Write the message length and data to the buffered writer
	n, err := writer.Write(length)
	if err != nil {
		return 0, err
	}
	totalBytesSent := n
	n, err = writer.Write(msg)
	if err != nil {
		return 0, err
	}
	totalBytesSent += n

	// Flush the buffered writer to ensure that the data is sent
	err = writer.Flush()
	if err != nil {
		return 0, err
	}

	return totalBytesSent, nil
}

func (comm TLSComm) Recv(src int) ([]byte, int, error) {
	recvLocks[src].Lock()
	defer recvLocks[src].Unlock()

	// Read the message length
	lengthBuf := make([]byte, 4)
	n, err := (*comm.Socks[src]).Read(lengthBuf)
	if err != nil {
		return nil, 0, err
	}
	length := binary.BigEndian.Uint32(lengthBuf)
	totalBytesRead := n

	// Read the message data
	data := make([]byte, length)
	bytesRead := 0
	for bytesRead < int(length) {
		n, err := (*comm.Socks[src]).Read(data[bytesRead:])
		if err != nil {
			return nil, 0, err
		}
		bytesRead += n
		totalBytesRead += n
	}

	return data, totalBytesRead, nil
}

func (comm TLSComm) Close() error {
	for _, sock := range comm.Socks {
		err := (*sock).Close()
		if err != nil {
			return err
		}
	}
	return nil
}

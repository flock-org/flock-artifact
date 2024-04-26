package networking

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"net"
	"net/netip"
)

func MsgToAddr(data []byte) *net.TCPAddr {
	dataStr := string(data)
	return net.TCPAddrFromAddrPort(netip.MustParseAddrPort(dataStr))
}

func AddrToMsg(addr net.TCPAddr) []byte {
	return []byte(fmt.Sprintf("%v:%v", addr.IP, addr.Port))
}

func SendMsgStr(sock net.Conn, msg string) error {
	// Convert the string to a byte slice
	msgBytes := []byte(msg)

	// Create a buffered writer for the connection
	writer := bufio.NewWriter(sock)

	// Prefix each message with a 4-byte length (network byte order)
	length := make([]byte, 4)
	binary.BigEndian.PutUint32(length, uint32(len(msgBytes)))

	// Write the message length and data to the buffered writer
	_, err := writer.Write(length)
	if err != nil {
		return err
	}
	_, err = writer.Write(msgBytes)
	if err != nil {
		return err
	}

	// Flush the buffered writer to ensure that the data is sent
	return writer.Flush()
}

func SendMsg(sock net.Conn, msg []byte) error {
	// Create a buffered writer for the connection
	writer := bufio.NewWriter(sock)

	// Prefix each message with a 8-byte length (network byte order)
	length := make([]byte, 4)
	binary.BigEndian.PutUint32(length, uint32(len(msg)))

	// Write the message length and data to the buffered writer
	_, err := writer.Write(length)
	if err != nil {
		return err
	}
	_, err = writer.Write(msg)
	if err != nil {
		return err
	}

	// Flush the buffered writer to ensure that the data is sent
	return writer.Flush()
}

func RecvMsg(sock net.Conn) ([]byte, error) {
	// Create a buffered reader for the connection
	reader := bufio.NewReader(sock)

	// Read the message length
	lengthBuf := make([]byte, 4)
	_, err := reader.Read(lengthBuf)
	if err != nil {
		return nil, err
	}
	length := binary.BigEndian.Uint32(lengthBuf)

	// Read the message data
	data := make([]byte, length)
	bytesRead := 0
	for bytesRead < int(length) {
		n, err := reader.Read(data[bytesRead:])
		if err != nil {
			return nil, err
		}
		bytesRead += n
	}

	return data, nil
}

type Client struct {
	Conn     net.Conn
	Pub      net.TCPAddr
	Priv     net.TCPAddr
	PartyInt int
}

func (c *Client) PeerMsg() []byte {
	return append(append(append(append(AddrToMsg(c.Pub), []byte("|")...), AddrToMsg(c.Priv)...), []byte("|")...), IntToBytes(c.PartyInt)...)
}

// intToBytes converts an integer to a byte array.
func IntToBytes(i int) []byte {
	var buf = make([]byte, 4)
	binary.LittleEndian.PutUint32(buf, uint32(i))
	return buf
}

// bytesToInt converts a byte array to an integer.
func BytesToInt(buf []byte) int {
	return int(binary.LittleEndian.Uint32(buf))
}

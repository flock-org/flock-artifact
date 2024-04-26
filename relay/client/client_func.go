package main

import (
	"crypto/tls"
	"fmt"
	"log"
	"net"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/relay/pkg/api"
	"github.com/relay/pkg/client"
)

var (
	maxDataBufferSize = 64 * 1024
)

var serverOps = []int{0, 0, 1208, 1150, 108, 0, 0, 0, 2874, 4053, 108, 0, 0, 279, 0, 108, 0, 483, 0, 108, 0, 244, 0, 108, 0}
var clientOps = []int{1208, 1150, 0, 0, 0, 108, 2874, 4053, 0, 0, 0, 108, 279, 0, 108, 0, 483, 0, 108, 0, 244, 0, 108, 0, 1}

var scale = 450

func recvServiceData(conn net.Conn, write bool) {
	bufData := make([]byte, maxDataBufferSize)
	for i := 0; i < 10; i++ {
		numBytes, err := conn.Read(bufData)
		if err != nil {
			log.Printf("Read error %v\n", err)
			break
		}
		log.Printf("Received \"%s\"\n", bufData[:numBytes])
	}
}

func handleDispatch(conn net.Conn, data []byte) {
	go recvServiceData(conn, false)
	var i int64
	i = 0
	for i = 0; i < 10; i++ {
		nData := strconv.AppendInt(data, i, 10)
		w, err := conn.Write(nData)
		if err != nil {
			log.Printf("Failed to write to tcp connection: %v", err)
			break
		} else {
			log.Printf("Written %d bytes", w)
		}
		time.Sleep(1 * time.Second)
	}
}

func recvBytes(conn net.Conn, write bool) {

	bufData := make([]byte, maxDataBufferSize)
	//for i := 0; i < 10; i++ {
	_, err := conn.Read(bufData)
	if err != nil {
		log.Printf("Read error %v\n", err)
		//break
	}
	//log.Printf("Received %d bytes", numBytes)
	//}
}

func sendBytes(conn net.Conn, data []byte) {
	_, err := conn.Write(data)
	if err != nil {
		log.Printf("Failed to write to tcp connection: %v", err)
	}
	// } else {
	// 	log.Printf("Written %d bytes", w)
	// }
	recvBytes(conn, false)
}

func emulateSigning(conn net.Conn, readyResp *api.Ready) {
	readBuf := make([]byte, maxDataBufferSize)
	var ops []int
	ops = serverOps
	if readyResp.Mode == api.TLSModeClient {
		ops = clientOps
	}
	for i := 0; i < len(ops); i++ {
		if ops[i] > 0 {
			buf := make([]byte, ops[i])
			//fmt.Printf("Writing %d", ops[i])
			_, err := conn.Write(buf)
			if err != nil {
				log.Printf("Failed to write to tcp connection: %v", err)
			}

		} else {
			_, err := conn.Read(readBuf)
			if err != nil {
				log.Printf("Read error %v\n", err)
			}
			//fmt.Printf("Read %d", b)
		}
	}

}

func emulateDecrypt(conn net.Conn, readyResp *api.Ready) {
	readBuf := make([]byte, maxDataBufferSize)
	var ops []int
	ops = serverOps
	if readyResp.Mode == api.TLSModeClient {
		ops = clientOps
	}
	for a := 0; a < scale; a++ {
		for i := 0; i < len(ops); i++ {
			if ops[i] > 0 {
				buf := make([]byte, ops[i])
				//fmt.Printf("Writing %d", ops[i])
				_, err := conn.Write(buf)
				if err != nil {
					log.Printf("Failed to write to tcp connection: %v", err)
				}

			} else {
				_, err := conn.Read(readBuf)
				if err != nil {
					log.Printf("Read error %v\n", err)
				}
				//fmt.Printf("Read %d", b)
			}
		}
		if a%20 == 0 {
			time.Sleep(1 * time.Millisecond)
		}
	}

}
func direct_client(target string, user, party string) (*tls.Conn, error) {

	log.Printf("Connecting to %s", target)
	tcpConn, err := net.Dial("tcp", target)
	if err != nil {
		log.Fatalf("Failed to connect to socket %+v", err)
	}
	return client.GetSessionE2EGo(tcpConn, &api.Ready{Mode: api.TLSModeClient}, user, party, "1")
}

func direct_server(target string, user, party string) (*tls.Conn, error) {
	acceptor, err := net.Listen("tcp", target)
	if err != nil {
		log.Fatalf("Error:", err)
		return nil, err
	}
	for {
		tcpConn, err := acceptor.Accept()
		if err != nil {
			log.Printf("server: accept: %s", err)
			return nil, err
		}
		client.GetSessionE2EGo(tcpConn, &api.Ready{Mode: api.TLSModeServer}, user, party, "")
	}
	return nil, err
}

func main() {
	relay := os.Getenv("RELAY")
	dest := os.Getenv("DEST")
	name := os.Getenv("NAME")
	user := os.Getenv("USER")
	mode := os.Getenv("MODE")
	target := os.Getenv("TARGET")
	conn, err := strconv.Atoi(os.Getenv("CONN"))
	if err != nil {
		fmt.Printf("Failed to convert conn\n")
	}
	var wg sync.WaitGroup
	// tag := os.Getenv("TAG")
	cacert := os.Getenv("RELAY_CA")
	cert := os.Getenv("RELAY_CERT")
	key := os.Getenv("RELAY_KEY")

	cacertUser := os.Getenv("USER_CA")
	certParty := os.Getenv("PARTY_CERT")
	keyParty := os.Getenv("PARTY_KEY")

	tag := os.Getenv("TAG")
	test := os.Getenv("TEST")
	//var tlsConn *tls.Conn

	// tag := flag.String("tag", "", "tag prefix")
	// //defer tlsConn.Close()
	// flag.Parse()
	// A regular TLS Client which uses tls.Dial to connect to the server's target
	if mode == "client" {
		timeStart := time.Now()
		tlsConn, _ := direct_client(target, user, name)
		e2eTime := time.Now().Sub(timeStart)
		fmt.Printf("%d\n", e2eTime.Milliseconds())
		handleDispatch(tlsConn, []byte("hi"))
	}

	// A regular TLS Server which uses tls.listen to listen to incoming tls connections
	if mode == "server" {
		tlsConn, _ := direct_server(":9000", user, name)
		handleDispatch(tlsConn, []byte("hi"))
	}
	fmt.Printf("Total connections : %d\n", conn)

	if mode == "" {
		time_start := time.Now()
		startTime := time.Now()
		if test == "latency" {
			buf := make([]byte, 14500)
			tcpConn, sslAuthConn, readyResp, err := client.StartRelayAuthWithCerts(dest, tag, relay, cacert, cert, key)
			if err != nil {
				fmt.Printf("Failed to get relay authorization: %v.\n", err)
				wg.Done()
				return
			}
			time_auth := time.Now()
			defer sslAuthConn.Close()
			defer tcpConn.Close()
			tlsConn, err := client.GetSessionE2EGoWithCerts(tcpConn, readyResp, dest, cacertUser, certParty, keyParty)
			if err != nil {
				fmt.Printf("Failed to get E2E session: %v.\n", err)
				sslAuthConn.Close()
				tcpConn.Close()
				wg.Done()
				return
			}
			authTime := time_auth.Sub(time_start)
			e2eTime := time.Now().Sub(time_auth)
			fmt.Printf("%d, %d\n", authTime.Milliseconds(), e2eTime.Milliseconds())
			sendBytes(tlsConn, buf)
			return
		}

		for i := 0; i < conn; i++ {
			wg.Add(1)
			go func(i int) {
				//fmt.Printf("Starting %d\n", i)
				//buf := make([]byte, 14500)
				tcpConn, sslAuthConn, readyResp, err := client.StartRelayAuthWithCerts(dest, tag+strconv.Itoa(i), relay, cacert, cert, key)
				if err != nil {
					fmt.Printf("Failed to get relay authorization: %v.\n", err)
					wg.Done()
					return
				}
				//time_auth := time.Now()
				defer sslAuthConn.Close()
				defer tcpConn.Close()
				tlsConn, err := client.GetSessionE2EGoWithCerts(tcpConn, readyResp, dest, cacertUser, certParty, keyParty)
				if err != nil {
					fmt.Printf("Failed to get E2E session: %v.\n", err)
					sslAuthConn.Close()
					tcpConn.Close()
					wg.Done()
					return
				}
				if test == "signing" {
					emulateSigning(tlsConn, readyResp)
				} else {
					emulateDecrypt(tlsConn, readyResp)
				}
				fmt.Printf(".")
				wg.Done()
				//tlsConn.Close()
			}(i)
		}
		wg.Wait()
		dur := time.Now().Sub(startTime)
		fmt.Print("\nDuration\n", dur.Seconds())

	}
	//tlsConn.Close()
	//log.Printf("%v", tlsConn)

}

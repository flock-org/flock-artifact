package main

import (
	"crypto/tls"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net"
	"os"
	"strconv"
	"time"

	"github.com/bnb-chain/tss-lib/ecdsa/keygen"
	"github.com/daryakaviani/on-demand-dots/internal/networking"
	"github.com/daryakaviani/on-demand-dots/internal/signing"
	"github.com/relay/pkg/client"
)

type Config struct {
	Op         string `json:"op"`
	PartyInt   int    `json:"partyInt"`
	Port       int    `json:"port"`
	Username   string `json:"username"`
	NumParties int    `json:"numParties"`
	PreParams  string `json:"preParams"`
	KeyShard   string `json:"keyShard"`
	Message    string `json:"message"`
	AWSAddr    string `json:"awsAddr"`
	AzureAddr  string `json:"azureAddr"`
	RouterAddr string `json:"routerAddr"`
	GCPAddr    string `json:"gcpAddr"`
	CertPath   string `json:"certPath"`
	AzurePort1 string `json:"azurePort1"`
	AzurePort2 string `json:"azurePort2"`
	RouterPort int    `json:"routerPort"`
	AWSPort    string `json:"awsPort"`
	AWSInt     int    `json:"awsInt"`
	AzureInt   int    `json:"azureInt"`
	GCPInt     int    `json:"gcpInt"`
	UseRouter  bool   `json:"useRouter"`
}

var username = "user1"

var (
	config Config

	// Certs for relay auth (mtls)
	cacert string
	cert   string
	key    string

	// Certs for E2E mtls
	cacertUser string
	certParty  string
	keyParty   string
)

const CertPath = "/app/certs/"

const logFilePath = "/tmp/signing.log"

func main() {
	jsonString := os.Args[1]

	cacert = os.Getenv("RELAY_CA")
	cert = os.Getenv("RELAY_CERT")
	key = os.Getenv("RELAY_KEY")

	cacertUser = os.Getenv("USER_CA")
	certParty = os.Getenv("PARTY_CERT")
	keyParty = os.Getenv("PARTY_KEY")

	err := json.Unmarshal([]byte(jsonString), &config)
	if err != nil {
		fmt.Printf("Error unmarshalling JSON: %v", err)
	}

	// err = initLog()
	// if err != nil {
	// 	fmt.Printf("Failed to init log: %v", err)
	// }
	switch config.Op {
	case "signing_sign":
		signatureString := runSigning()
		fmt.Println(signatureString)
	case "signing_keygen":
		keygenString := runSigningKeyGen()
		fmt.Println(keygenString)
	case "signing_preparams":
		preparamsString := generatePreParams()
		fmt.Println(preparamsString)
	default:
		fmt.Println("Invalid operation: ", config.Op)
	}
}

func initLog() error {
	f, err := os.OpenFile(logFilePath, os.O_APPEND|os.O_CREATE|os.O_RDWR, 0600)
	fmt.Printf("Creating log file: %v\n", logFilePath)
	if err != nil {
		return fmt.Errorf("error opening log file: %v", err.Error())
	}
	log.SetOutput(f)
	return nil
}

func generatePreParams() string {
	log.Print("Generating preparams before reaching out to other parties...")
	tssPreParams, err := keygen.GeneratePreParams(13*time.Minute, 10)
	if err != nil {
		fmt.Printf("Failed to generate preparams %v \n", err)
	}

	return signing.LocalPreParamsToString(tssPreParams)
}

func runSigningKeyGen() string {
	partyIdx := config.PartyInt
	tssPreParamsString := config.PreParams
	tssPreParams := signing.LocalPreParamsFromString(tssPreParamsString)
	comm := &networking.TLSComm{Socks: make(map[int]*tls.Conn), Rank: partyIdx}

	if config.UseRouter {
		setupTLSWithRelay(comm)
	} else {
		setupTLS(comm)
	}
	// log.Printf("Done setting up TLS, now moving on to signing..")
	// comm := &networking.P2PComm{Socks: make(map[int]*net.Conn), Rank: partyIdx}
	// setupTCP(comm)
	keygenResult := signing.KeyGenParty(partyIdx, 3, 2, comm, tssPreParams)
	comm.Close()
	return keygenResult
}

func runSigning() string {
	partyIdx := config.PartyInt

	keyString := config.KeyShard
	key := signing.LocalPartySaveDataFromString(keyString)

	msg_bytes, err := hex.DecodeString(config.Message)
	if err != nil {
		fmt.Println("Error:", err)
	}
	msg := new(big.Int).SetBytes(msg_bytes)

	comm := &networking.TLSComm{Socks: make(map[int]*tls.Conn), Rank: partyIdx}
	if config.UseRouter {
		setupTLSWithRelay(comm)
		//setupTLSWithRouter(comm)
	} else {
		setupTLS(comm)
	}
	signature := signing.SigningParty(partyIdx, 3, 2, comm, *key, msg)
	comm.Close()
	return signature
}

func setupTLS(comm *networking.TLSComm) {
	partyIdx := config.PartyInt
	// Listen for incoming connections based on the VM type
	if partyIdx == config.AWSInt {
		go listenTLS(comm, config.AWSPort)
	} else if partyIdx == config.AzureInt {
		go listenTLS(comm, config.AzurePort1)
		go listenTLS(comm, config.AzurePort2)
	}

	// Outgoing connections
	if partyIdx == config.GCPInt {
		dialTLS(comm, config.AWSInt, config.AWSAddr+config.AWSPort)        // AWS
		dialTLS(comm, config.AzureInt, config.AzureAddr+config.AzurePort2) // AZURE
	} else if partyIdx == config.AWSInt {
		dialTLS(comm, config.AzureInt, config.AzureAddr+config.AzurePort1) // AZURE
	}

	// Print the P2PComm object
	for {
		if len(comm.Socks) == 2 {
			fmt.Println(comm)
			break
		}
	}
}

// func setupTLSWithRouter(comm *networking.TLSComm) {
// 	partyIdx := config.PartyInt
// 	// Listen for incoming connections based on the VM type
// 	// fmt.Prinln("Listen1")

// 	if partyIdx == config.AzureInt {
// 		go listenTLS(comm, config.AzurePort1)
// 		go listenTLS(comm, config.AzurePort2)
// 	}
// 	// fmt.Prinln("Listen2")

// 	// Outgoing connections
// 	if partyIdx == config.GCPInt {
// 		dialRouterTLS(comm, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"signing_aws_gcp") // AWS
// 		dialTLS(comm, config.AzureInt, config.AzureAddr+config.AzurePort2)                                                           // AZURE
// 	} else if partyIdx == config.AWSInt {
// 		dialRouterTLS(comm, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"signing_aws_gcp")
// 		dialTLS(comm, config.AzureInt, config.AzureAddr+config.AzurePort1) // AZURE
// 	}

// 	// Print the P2PComm object
// 	for {
// 		if len(comm.Socks) == 2 {
// 			fmt.Println(comm)
// 			break
// 		}
// 	}
// }

func setupTLSWithRelay(comm *networking.TLSComm) {
	partyIdx := config.PartyInt
	if cert != "" {
		// log.Printf("Setting TLS with relay using env certs")

		if partyIdx == config.AzureInt {
			dialRelayTLSWithCerts(comm, config.AzureInt, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_azure")
			dialRelayTLSWithCerts(comm, config.AzureInt, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_gcp_azure")
		} else if partyIdx == config.GCPInt {
			dialRelayTLSWithCerts(comm, config.GCPInt, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_gcp")
			dialRelayTLSWithCerts(comm, config.GCPInt, config.AzureInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_gcp_azure")
		} else if partyIdx == config.AWSInt {
			dialRelayTLSWithCerts(comm, config.AWSInt, config.AzureInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_azure")
			dialRelayTLSWithCerts(comm, config.AWSInt, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_gcp")
		}
	} else {
		// log.Printf("Setting TLS with relay using image provided certs")

		if partyIdx == config.AzureInt {
			dialRelayTLS(comm, config.AzureInt, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_azure")
			dialRelayTLS(comm, config.AzureInt, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_gcp_azure")
		} else if partyIdx == config.GCPInt {
			dialRelayTLS(comm, config.GCPInt, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_gcp")
			dialRelayTLS(comm, config.GCPInt, config.AzureInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_gcp_azure")
		} else if partyIdx == config.AWSInt {
			dialRelayTLS(comm, config.AWSInt, config.AzureInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_azure")
			dialRelayTLS(comm, config.AWSInt, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_gcp")
		}
	}

	// Print the P2PComm object
	for {
		if len(comm.Socks) == 2 {
			fmt.Println(comm)
			break
		}
	}
}

func setupTLSWithRouter(comm *networking.TLSComm) {
	partyIdx := config.PartyInt

	fmt.Printf("Setting with TLS with router")
	if partyIdx == config.AzureInt {
		dialRouterTLS(comm, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_azure") // AWS
		dialRouterTLS(comm, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_gcp_azure") // AWS
	} else if partyIdx == config.GCPInt {
		dialRouterTLS(comm, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_gcp")     // AWS
		dialRouterTLS(comm, config.AzureInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_gcp_azure") // AWS                             // AZURE
	} else if partyIdx == config.AWSInt {
		dialRouterTLS(comm, config.AzureInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_azure") // AWS
		dialRouterTLS(comm, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), config.Username+"_signing_aws_gcp")
	}

	// Print the P2PComm object
	for {
		if len(comm.Socks) == 2 {
			fmt.Println(comm)
			break
		}
	}
}

func setupTCPWithRouter(comm *networking.P2PComm) {
	partyIdx := config.PartyInt
	// Listen for incoming connections based on the VM type
	if partyIdx == config.AzureInt {
		go listenTCP(comm, config.AzurePort1)
		go listenTCP(comm, config.AzurePort2)
	}

	// Outgoing connections
	if partyIdx == config.GCPInt {
		dialRouter(comm, config.AWSInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), "signing_aws_gcp") // AWS
		dialTCP(comm, config.AzureInt, config.AzureAddr+config.AzurePort2)                                        // AZURE
	} else if partyIdx == config.AWSInt {
		dialRouter(comm, config.GCPInt, config.RouterAddr+":"+strconv.Itoa(config.RouterPort), "signing_aws_gcp")
		dialTCP(comm, config.AzureInt, config.AzureAddr+config.AzurePort1) // AZURE
	}

	// Print the P2PComm object
	for {
		if len(comm.Socks) == 2 {
			fmt.Println(comm)
			break
		}
	}
}

func upgradeToTLSServer(conn net.Conn) (*tls.Conn, error) {
	// certPath := config.CertPath
	certPath := CertPath

	cert, err := tls.LoadX509KeyPair(certPath+"client.pem", certPath+"client.key")
	if err != nil {
		log.Fatalf("server: loadkeys: %s", err)
		return nil, err
	}
	tlsConfig := tls.Config{Certificates: []tls.Certificate{cert}, InsecureSkipVerify: true}
	tlsConn := tls.Server(conn, &tlsConfig)

	err = tlsConn.Handshake()
	if err != nil {
		log.Fatalf("failed to perform handshake : %+v", err)
		return nil, err
	}
	return tlsConn, nil
}

func upgradeToTLSClient(conn net.Conn) (*tls.Conn, error) {
	// certPath := config.CertPath
	certPath := CertPath

	cert, err := tls.LoadX509KeyPair(certPath+"client.pem", certPath+"client.key")
	if err != nil {
		log.Fatalf("client: loadkeys: %s", err)
		return nil, err
	}
	tlsConfig := tls.Config{Certificates: []tls.Certificate{cert}, InsecureSkipVerify: true}

	tlsConn := tls.Client(conn, &tlsConfig)
	err = tlsConn.Handshake()
	if err != nil {
		log.Fatalf("failed to perform handshake : %+v", err)
		return nil, err
	}
	return tlsConn, nil
}

func listenTLS(comm *networking.TLSComm, port string) {
	l, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatal(err)
		return
	}
	defer l.Close()

	for {
		conn, err := l.Accept()
		if err != nil {
			log.Println(err)
			continue
		}

		var tlsConn *tls.Conn
		tlsConn, err = upgradeToTLSServer(conn)

		if err != nil {
			log.Printf("Failed to upgrade connection from %s: %v", conn.RemoteAddr().String(), err)
			continue
		}

		remoteAddr := conn.RemoteAddr().(*net.TCPAddr).IP.String()
		log.Println("Remote addr %s", remoteAddr)
		src := getIndexByIP(remoteAddr)
		comm.Socks[src] = tlsConn
	}
}

func dialTLS(comm *networking.TLSComm, dst int, address string) {
	// conn, err := net.DialTimeout("tcp", address, 5*time.Second)
	// if err != nil {
	// 	log.Fatal(err)
	// 	return
	// }

	// var tlsConn *tls.Conn
	// tlsConn, err = upgradeToTLSClient(conn)

	// if err != nil {
	// 	log.Fatalf("Failed to upgrade connection for destination %d: %v", dst, err)
	// } else {
	// 	comm.Socks[dst] = tlsConn
	// }

	var maxDuration = 5 * time.Second

	var tlsConn *tls.Conn
	// var err error
	start := time.Now()

	for time.Since(start) < maxDuration {
		conn, err := net.Dial("tcp", address)
		if err != nil {
			log.Printf("Dial failed: %v", err)
			// time.Sleep(retryInterval)
			continue
		}

		tlsConn, err = upgradeToTLSClient(conn)

		if err != nil {
			log.Printf("Failed to upgrade connection for destination %d: %v", dst, err)
			conn.Close()
		} else {
			comm.Socks[dst] = tlsConn
			return
		}
	}

	log.Fatalf("Retry duration of %v exceeded. Failed to establish a TLS connection for destination %d", maxDuration, dst)
}

func listenTCP(comm *networking.P2PComm, port string) {
	l, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatal(err)
		return
	}
	defer l.Close()

	for {
		conn, err := l.Accept()
		if err != nil {
			log.Println(err)
			continue
		}

		if err != nil {
			log.Printf("Failed to upgrade connection from %s: %v", conn.RemoteAddr().String(), err)
			continue
		}

		remoteAddr := conn.RemoteAddr().(*net.TCPAddr).IP.String()
		src := getIndexByPort(port)
		log.Println("Remote addr %s", remoteAddr)
		log.Println("src: %s", src)
		comm.Socks[src] = &conn // Changed tlsConn to conn
	}
}

func dialTCP(comm *networking.P2PComm, dst int, address string) {
	conn, err := net.Dial("tcp", address)
	// fmt.Prinln("dial tcp finished")
	if err != nil {
		log.Fatal(err)
		return
	}

	if err != nil {
		log.Fatalf("Failed to upgrade connection for destination %d: %v", dst, err)
	} else {
		comm.Socks[dst] = &conn // Changed tlsConn to conn
	}
}

func dialRouter(comm *networking.P2PComm, dst int, address string, tag string) {
	conn, err := net.Dial("tcp", address)
	// fmt.Prinln("dial tcp finished")
	if err != nil {
		log.Fatal(err)
		return
	}

	if err != nil {
		log.Fatalf("Failed to upgrade connection for destination %d: %v", dst, err)
	} else {
		comm.Socks[dst] = &conn // Changed tlsConn to conn
	}

	networking.SendMsgStr(conn, tag)
}

// Uses the new Relay-provided APIs to connect
func dialRelayTLS(comm *networking.TLSComm, src int, dst int, address string, tag string) {
	var tlsConn *tls.Conn
	// log.Printf("Starting dialRelayTLS for %d:%s", src, dst)
	for {
		tcpConn, sslAuthConn, readyResp, err := client.StartRelayAuthGo(strconv.Itoa(src), strconv.Itoa(dst), tag, address)
		if err != nil {
			log.Printf("Failed to get relay authorization: %v.", err)
			sslAuthConn.Close()
			tcpConn.Close()
			continue
		}
		// tlsConn, err = client.GetSessionE2EGo(tcpConn, readyResp, config.Username, strconv.Itoa(src), strconv.Itoa(dst))
		tlsConn, err = client.GetSessionE2EGo(tcpConn, readyResp, "user1", strconv.Itoa(src), strconv.Itoa(dst))
		if err != nil {
			log.Printf("Failed to get E2E session: %v.", err)
			sslAuthConn.Close()
			tcpConn.Close()
			continue
		}
		break
	}
	comm.Socks[dst] = tlsConn
	// log.Printf("Established connection for %d:%d", src, dst)
}

// Uses the new Relay-provided APIs to connect
func dialRelayTLSWithCerts(comm *networking.TLSComm, src int, dst int, address string, tag string) {
	var tlsConn *tls.Conn
	// log.Printf("Starting dialRelayTLS with certs for %d:%s", src, dst)
	for {
		tcpConn, sslAuthConn, readyResp, err := client.StartRelayAuthWithCerts(strconv.Itoa(dst), tag, address, cacert, cert, key)
		if err != nil {
			log.Printf("Failed to get relay authorization: %v.", err)
			sslAuthConn.Close()
			tcpConn.Close()
			continue
		}
		tlsConn, err = client.GetSessionE2EGoWithCerts(tcpConn, readyResp, strconv.Itoa(dst), cacertUser, certParty, keyParty)
		if err != nil {
			log.Printf("Failed to get E2E session: %v.", err)
			sslAuthConn.Close()
			tcpConn.Close()
			continue
		}
		break
	}
	comm.Socks[dst] = tlsConn
	// log.Printf("Established connection for %d:%d", src, dst)
}

func dialRouterTLS(comm *networking.TLSComm, dst int, address string, tag string) {
	conn, err := net.Dial("tcp", address)
	// fmt.Prinln("dial tcp finished")
	if err != nil {
		log.Fatal(err)
		return
	}

	var tlsConn *tls.Conn
	tlsConn, err = upgradeToTLSClient(conn)
	if err != nil {
		log.Fatalf("Failed to upgrade connection for destination %d: %v", dst, err)
	} else {
		comm.Socks[dst] = tlsConn // Changed tlsConn to conn
	}

	networking.SendMsgStr(tlsConn, tag)
}

func getIndexByPort(port string) int {
	switch port {
	case config.AzurePort1:
		return config.AWSInt
	case config.AzurePort2:
		return config.GCPInt
	default:
		return -1
	}
}

func getIndexByIP(ip string) int {
	switch ip {
	case config.GCPAddr:
		return config.GCPInt
	case config.AWSAddr:
		return config.AWSInt
	case config.AzureAddr:
		return config.AzureInt
	default:
		return config.GCPInt // If the address is unknown, it is from GCP
	}
}

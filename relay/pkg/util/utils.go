package util

import (
	"fmt"

	"github.com/praveingk/openssl"
)

// GetPartyName returns the Common Name from the X509 certificate
func GetPartyName(tlsConn *openssl.Conn) (string, error) {
	cert, err := tlsConn.PeerCertificate()
	if err != nil {
		return "", fmt.Errorf("unable to get certificates: %v", err)
	}
	subjName, err := cert.GetSubjectName()
	if err != nil {
		return "", fmt.Errorf("unable to get subject name: %v", err)
	}
	party, ok := subjName.GetEntry(openssl.NID_commonName)
	if !ok {
		return "", fmt.Errorf("unable to get CommonName :%v", err)
	}
	return party, nil
}

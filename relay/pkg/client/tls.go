package client

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"os"
)

// ParsedCertData contains a parsed CA and TLS certificate.
type parsedCertData struct {
	certificate tls.Certificate
	ca          *x509.CertPool
	x509cert    *x509.Certificate
}

// ParseTLSFiles parses the given TLS-related files.
func parseTLSFiles(ca, cert, key string) (*parsedCertData, error) {
	rawCA, err := os.ReadFile(ca)
	if err != nil {
		return nil, fmt.Errorf("unable to read CA file '%s': %v", ca, err)
	}

	rawCertificate, err := os.ReadFile(cert)
	if err != nil {
		return nil, fmt.Errorf("unable to read certificate file: %v", err)
	}

	rawPrivateKey, err := os.ReadFile(key)
	if err != nil {
		return nil, fmt.Errorf("unable to read private key file: %v", err)
	}

	certificate, err := tls.X509KeyPair(rawCertificate, rawPrivateKey)
	if err != nil {
		return nil, fmt.Errorf("unable to parse certificate keypair: %v", err)
	}

	caCertPool := x509.NewCertPool()
	if !caCertPool.AppendCertsFromPEM(rawCA) {
		return nil, fmt.Errorf("unable to parse CA")
	}

	x509cert, err := x509.ParseCertificate(certificate.Certificate[0])
	if err != nil {
		return nil, fmt.Errorf("unable to parse x509 certificate: %v", err)
	}

	return &parsedCertData{
		certificate: certificate,
		ca:          caCertPool,
		x509cert:    x509cert,
	}, nil
}

// parseTLSFiles parses the given TLS-related files.
func parseTLSStrings(ca, cert, key string) (*parsedCertData, error) {
	rawCA := []byte(ca)
	rawCertificate := []byte(cert)
	rawPrivateKey := []byte(key)

	certificate, err := tls.X509KeyPair(rawCertificate, rawPrivateKey)
	if err != nil {
		return nil, fmt.Errorf("unable to parse certificate keypair: %v", err)
	}

	caCertPool := x509.NewCertPool()
	if !caCertPool.AppendCertsFromPEM(rawCA) {
		return nil, fmt.Errorf("unable to parse CA")
	}

	x509cert, err := x509.ParseCertificate(certificate.Certificate[0])
	if err != nil {
		return nil, fmt.Errorf("unable to parse x509 certificate: %v", err)
	}

	return &parsedCertData{
		certificate: certificate,
		ca:          caCertPool,
		x509cert:    x509cert,
	}, nil
}

// ServerConfig return a TLS configuration for a server.
func (c *parsedCertData) ServerConfig() *tls.Config {
	return &tls.Config{
		MinVersion:   tls.VersionTLS12,
		Certificates: []tls.Certificate{c.certificate},
		ClientCAs:    c.ca,
		ClientAuth:   tls.RequireAndVerifyClientCert,
	}
}

// ClientConfig return a TLS configuration for a client.
func (c *parsedCertData) ClientConfig(sni string) *tls.Config {
	return &tls.Config{
		MinVersion:   tls.VersionTLS12,
		Certificates: []tls.Certificate{c.certificate},
		RootCAs:      c.ca,
		ServerName:   sni,
	}
}

// DNSNames returns the certificate DNS names.
func (c *parsedCertData) DNSNames() []string {
	return c.x509cert.DNSNames
}

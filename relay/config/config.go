package config

import "path/filepath"

const (
	//FrelayServerName is the servername used in frelay router
	FrelayServerName = "frelay"
	//CertsRootDirectory is the directory for storing all certs it can be changed to /etc/ssl/certs
	CertsRootDirectory = "certs"
	//CertsDirectory is the directory for storing all certs it can be changed to /etc/ssl/certs
	CertsDirectory = "certs"
	// FrCAFile is the path to the certificate authority file.
	FrCAFile = CertsRootDirectory + "/frelay-ca.pem"
	// FrCAFile is the path to the certificate authority file.
	FrCAFileRoot = CertsDirectory + "/frelay-ca.pem"
	// FrKeyFile is the path to the private-key file.
	FrKeyFile = CertsDirectory + "/frelay-key.pem"

	// PrivateKeyFileName is the filename used by private key files.
	PrivateKeyFileName = "key.pem"
	// CertificateFileName is the filename used by certificate files.
	CertificateFileName = "cert.pem"

	// UserCAFile is the path to CA cert of the user
	UserCAFile = "user-ca.pem"
	// UserKeyFile is the private key file
	UserKeyFile = "user-key.pem"
)

// BaseDirectory returns the base path of the fabric.
func BaseDirectory() string {
	return CertsRootDirectory
}

func BaseDirectoryRelay() string {
	return CertsDirectory
}

// PartyDirectory returns the base path for a specific party within the frelay's domain for auth.
func PartyDirectory(party string) string {
	return filepath.Join(BaseDirectory(), party)
}

// UserDirectory returns the base path for a specific party.
func UserDirectory(user string) string {
	return filepath.Join(BaseDirectory(), user)
}

// UserPartyDirectory returns the base path for a specific party within a user's domain.
func UserPartyDirectory(user string, party string) string {
	return filepath.Join(BaseDirectory(), user, party)
}

// FrelayDirectory returns the base path for a Frelay
func FrelayDirectory() string {
	return filepath.Join(BaseDirectory(), FrelayServerName)
}

// FrelayCSDirectory returns the base path for a Frelay
func FrelayCADirectory() string {
	return filepath.Join(BaseDirectoryRelay(), FrelayServerName)
}

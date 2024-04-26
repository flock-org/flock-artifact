package api

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/clusterlink-net/clusterlink/cmd/cl-adm/util"

	"github.com/relay/config"
)

func createFrelayCerts(entity string) {
	fmt.Printf("Creating Party %s certs for Frelay auth.\n", entity)
	partyDirectory := config.PartyDirectory(entity)
	if err := os.MkdirAll(partyDirectory, 0755); err != nil {
		fmt.Printf("Unable to create directory :%v\n", err)
		return
	}
	err := util.CreateCertificate(&util.CertificateConfig{
		Name:              entity,
		IsClient:          true,
		DNSNames:          []string{entity},
		CAPath:            config.FrCAFile,
		CAKeyPath:         config.FrKeyFile,
		CertOutPath:       filepath.Join(partyDirectory, config.CertificateFileName),
		PrivateKeyOutPath: filepath.Join(partyDirectory, config.PrivateKeyFileName),
	})
	if err != nil {
		fmt.Printf("Unable to generate certficate/key :%v\n", err)
		return
	}
}

func createUserCerts(user, party string) {
	fmt.Printf("Creating Party %s certs for multi-party comms for user %s\n", user, party)
	partyDirectory := config.UserPartyDirectory(user, party)
	userDirectory := config.UserDirectory(user)

	if err := os.MkdirAll(partyDirectory, 0755); err != nil {
		fmt.Printf("Unable to create directory :%v\n", err)
		return
	}
	err := util.CreateCertificate(&util.CertificateConfig{
		Name:              party,
		IsClient:          true,
		IsServer:          true,
		DNSNames:          []string{party},
		CAPath:            filepath.Join(userDirectory, config.UserCAFile),
		CAKeyPath:         filepath.Join(userDirectory, config.UserKeyFile),
		CertOutPath:       filepath.Join(partyDirectory, config.CertificateFileName),
		PrivateKeyOutPath: filepath.Join(partyDirectory, config.PrivateKeyFileName),
	})
	if err != nil {
		fmt.Printf("Unable to generate certficate/key :%v\n", err)
		return
	}
}

func CreateUser(name string) {
	fmt.Printf("Creating CA Cert for user %s.\n", name)
	userDirectory := config.UserDirectory(name)
	if err := os.MkdirAll(userDirectory, 0755); err != nil {
		fmt.Printf("Unable to create directory :%v\n", err)
		return
	}
	err := util.CreateCertificate(&util.CertificateConfig{
		Name:              name,
		IsCA:              true,
		CertOutPath:       filepath.Join(userDirectory, config.UserCAFile),
		PrivateKeyOutPath: filepath.Join(userDirectory, config.UserKeyFile),
	})
	if err != nil {
		fmt.Printf("Unable to generate CA certficate :%v\n", err)
		return
	}
}

func CreateParty(party string, user string) {
	// Create certs using Frelay's CA cert
	createFrelayCerts(party)
	createUserCerts(user, party)
}

func CreateRelay() {
	fmt.Printf("Creating Frelay CA Cert.\n")
	if err := os.MkdirAll(config.BaseDirectory(), 0755); err != nil {
		fmt.Printf("Unable to create directory :%v\n", err)
		return
	}
	err := util.CreateCertificate(&util.CertificateConfig{
		Name:              config.FrelayServerName,
		IsCA:              true,
		CertOutPath:       config.FrCAFile,
		PrivateKeyOutPath: config.FrKeyFile,
	})
	if err != nil {
		fmt.Printf("Unable to generate CA certficate :%v\n", err)
		return
	}
	fmt.Printf("Generating Certs/Key using CA.\n")

	frelayDirectory := config.FrelayCADirectory()
	if err := os.MkdirAll(frelayDirectory, 0755); err != nil {
		fmt.Printf("Unable to create directory :%v\n", err)
		return
	}
	err = util.CreateCertificate(&util.CertificateConfig{
		Name:              config.FrelayServerName,
		IsServer:          true,
		IsClient:          true,
		DNSNames:          []string{config.FrelayServerName},
		CAPath:            config.FrCAFileRoot,
		CAKeyPath:         config.FrKeyFile,
		CertOutPath:       filepath.Join(frelayDirectory, config.CertificateFileName),
		PrivateKeyOutPath: filepath.Join(frelayDirectory, config.PrivateKeyFileName),
	})
	if err != nil {
		fmt.Printf("Unable to generate certficate/key :%v\n", err)
		return
	}
}

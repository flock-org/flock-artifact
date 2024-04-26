package api

// TLSMode represents the role the party must take for E2E
type TLSMode int

const (
	// TLSModeServer is server
	TLSModeServer TLSMode = 1
	// TLSModeClient is client
	TLSModeClient = 2
)

type UserReq struct {
	// UserName is a unique name associated with the user e.g. alice
	UserName string
	// Parties is the count of the parties/functions to be deployed
	Parties string
}

type UserResp struct {
	// RelayTarget specifies the destionation of the Relays
	RelayTarget string
	PartyInfos  []PartyInfo
}

type PartyInfo struct {
	// PartyIDs specifies the UUIDs to be used for the Parties/functions
	PartyID string
	// Certificates are sent over separately as octets with partyID-cert.pem & pertyID-key.pem
}

// UserSpec contains all the party attributes and access group
type UserSpec struct {
	Party       []string
	AccessGroup string
}

// AuthReq contains the access authorization message sent by a party to the relay
type AuthReq struct {
	DestParty string
	Tag       string // Optional if establishing a specific connection using a tag
}

// Ready contains the message that is sent to party when the connection is ready
type Ready struct {
	Mode TLSMode
}

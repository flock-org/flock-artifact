package signing

import (
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"time"

	"github.com/bnb-chain/tss-lib/common"
	"github.com/bnb-chain/tss-lib/ecdsa/keygen"
	"github.com/bnb-chain/tss-lib/ecdsa/signing"
	"github.com/bnb-chain/tss-lib/tss"
	"github.com/daryakaviani/on-demand-dots/internal/networking"
)

// Conducts multi-party ECDSA signing for n = numParties and t = numThreshold
func SigningParty(partyInt int, numParties int, numThreshold int, comm networking.Communicator, key keygen.LocalPartySaveData, msg *big.Int) string {
	// if err := logger.SetLogLevel("tss-lib", "debug"); err != nil {
	// 	panic(err)
	// }
	msgQueue = make(map[string][]tss.ParsedMessage)

	// Index of next message we must send
	next = 0

	// Number of messages of current type we have processed
	numProcessed = 0

	// Number of other parties
	numOtherParties = numParties - 1

	// Number of bytes received
	totalBytesRead := 0

	// Number of bytes sent
	totalBytesSent := 0

	// List of party IDs
	partyIDs := GetParticipantPartyIDs(numParties)
	ctx := tss.NewPeerContext(partyIDs)
	thisPartyID := partyIDs[partyInt]
	otherPartyIDs := partyIDs.Exclude(thisPartyID)

	// Channels
	errCh := make(chan *tss.Error, 1)
	outCh := make(chan tss.Message, 1)
	endCh := make(chan common.SignatureData, 1)

	// Init the party
	startTime := time.Now()
	var endTime time.Time
	params := tss.NewParameters(tss.S256(), ctx, thisPartyID, numParties, numThreshold)
	party := signing.NewLocalParty(msg, params, key, outCh, endCh).(*signing.LocalParty)
	go func() {
		if err := party.Start(); err != nil {
			errCh <- err
		}
	}()

	go func() {
		select {
		case err := <-errCh:
			log.Fatalf("Error: %s", err)
		}
	}()

	for {
		// Send outgoing messages
		select {
		case msg := <-outCh:
			dest := msg.GetTo()
			if dest == nil { // broadcast!
				for _, partyID := range otherPartyIDs {
					bytesSent := sendTSSMessage(msg, party, *partyID, comm, errCh)
					totalBytesSent += bytesSent
				}
				for _, partyID := range otherPartyIDs {
					recv_msg, bytesRead := recvTSSMessage(party, *partyID, comm, true)
					totalBytesRead += bytesRead
					if recv_msg.Type() == msg.Type() {
						go party.Update(recv_msg)
					} else {
						log.Fatalf("Message received has type %s whereas message sent has type %s", recv_msg.Type(), msg.Type())
					}
				}
			} else { // point-to-point!
				if dest[0].Index == msg.GetFrom().Index {
					log.Fatalf("party %d tried to send a message to itself (%d)", dest[0].Index, msg.GetFrom().Index)
				}
				bytesSent := sendTSSMessage(msg, party, *dest[0], comm, errCh)
				totalBytesSent += bytesSent
				recv_msg, bytesRead := recvTSSMessage(party, *dest[0], comm, false)
				totalBytesRead += bytesRead
				if recv_msg.Type() == msg.Type() {
					go party.Update(recv_msg)
				} else {
					log.Fatalf("Message received has type %s whereas message sent has type %s", recv_msg.Type(), msg.Type())
				}
			}
		case save := <-endCh:
			endTime = time.Now()
			// log.Printf("Signature %v", save)
			// log.Printf("========= PARTY %v SIGNING PROTOCOL BENCHMARKS =========", partyInt)
			// log.Printf("Total bytes read during signing protocol by party %v: %v", partyInt, totalBytesRead)
			// log.Printf("Total bytes sent during signing protocol by party %v: %v", partyInt, totalBytesSent)
			// log.Printf("Time to run signing protocol for party %v: %v", partyInt, endTime.Sub(startTime))
			response := map[string]interface{}{
				"signature":          fmt.Sprintf("%x", save.Signature),
				"signing_bytes_read": totalBytesRead,
				"signing_bytes_sent": totalBytesSent,
				"signing_time":       endTime.Sub(startTime).String(),
			}

			responseJson, err := json.Marshal(response)
			if err != nil {
				log.Fatalf("Failed to convert JSON: %v", err)
			}

			return string(responseJson)
		}
	}
}

package signing

import (
	"encoding/json"
	"log"
	"time"

	"github.com/daryakaviani/on-demand-dots/internal/networking"

	"github.com/bnb-chain/tss-lib/ecdsa/keygen"
	"github.com/bnb-chain/tss-lib/tss"
)

// Conducts multi-party ECDSA keygen for n = numParties and t = numThreshold
func KeyGenParty(partyInt int, numParties int, numThreshold int, comm networking.Communicator, tssPreParams *keygen.LocalPreParams) string {
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
	endCh := make(chan keygen.LocalPartySaveData, 1)

	// Init the party
	startTime := time.Now()
	params := tss.NewParameters(tss.S256(), ctx, thisPartyID, numParties, numThreshold)
	party := keygen.NewLocalParty(params, outCh, endCh, *tssPreParams).(*keygen.LocalParty)
	go func() {
		if err := party.Start(); err != nil {
			errCh <- err
		}
	}()

	go func() {
		for {
			select {
			case err := <-errCh:
				log.Fatalf("Error: %s", err)
			}
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
			endTime := time.Now()
			// log.Printf("========= PARTY %v KEYGEN PROTOCOL BENCHMARKS =========", partyInt)
			// log.Printf("Total bytes read during keygen protocol by party %v: %v", partyInt, totalBytesRead)
			// log.Printf("Total bytes sent during keygen protocol by party %v: %v", partyInt, totalBytesSent)
			// log.Printf("Time to run keygen protocol for party %v: %v", partyInt, endTime.Sub(startTime))

			response := map[string]interface{}{
				"key":               LocalPartySaveDataToString(&save),
				"keygen_bytes_read": totalBytesRead,
				"keygen_bytes_sent": totalBytesSent,
				"keygen_time":       endTime.Sub(startTime).String(),
			}

			responseJson, err := json.Marshal(response)
			if err != nil {
				log.Fatalf("Failed to convert JSON: %v", err)
			}

			// log.Printf("keygen response json: %v", responseJson)
			return string(responseJson)
		}
	}
}

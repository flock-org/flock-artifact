package signing

import (
	"encoding/json"
	"log"
	"math/big"
	"strconv"
	"sync"

	"github.com/bnb-chain/tss-lib/ecdsa/keygen"
	"github.com/bnb-chain/tss-lib/tss"
	"github.com/daryakaviani/on-demand-dots/internal/networking"
)

var msgQueue map[string][]tss.ParsedMessage
var next int
var numProcessed int
var nextMutex sync.Mutex
var numProcessedMutex sync.Mutex
var sockMutex sync.Mutex
var numOtherParties int

var keygenTypes []string = []string{
	"binance.tsslib.ecdsa.keygen.KGRound1Message",
	"binance.tsslib.ecdsa.keygen.KGRound2Message1",
	"binance.tsslib.ecdsa.keygen.KGRound2Message2",
	"binance.tsslib.ecdsa.keygen.KGRound3Message",
}

var signingTypes []string = []string{
	"binance.tsslib.ecdsa.signing.SignRound1Message1",
	"binance.tsslib.ecdsa.signing.SignRound1Message2",
	"binance.tsslib.ecdsa.signing.SignRound2Message",
	"binance.tsslib.ecdsa.signing.SignRound3Message",
	"binance.tsslib.ecdsa.signing.SignRound4Message",
	"binance.tsslib.ecdsa.signing.SignRound5Message",
	"binance.tsslib.ecdsa.signing.SignRound6Message",
	"binance.tsslib.ecdsa.signing.SignRound7Message",
	"binance.tsslib.ecdsa.signing.SignRound8Message",
	"binance.tsslib.ecdsa.signing.SignRound9Message",
}

var isBroadcastMap map[string]bool = map[string]bool{}

func sendTSSMessage(msgToSend tss.Message, party tss.Party, to tss.PartyID, comm networking.Communicator, errCh chan<- *tss.Error) int {
	msgBytes, _, err := msgToSend.WireBytes()
	if err != nil {
		errCh <- party.WrapError(err)
		return 0
	}
	bytesSent, err := comm.Send(to.Index, msgBytes)
	return bytesSent
}

func recvTSSMessage(party tss.Party, from tss.PartyID, comm networking.Communicator, isBroadcast bool) (tss.ParsedMessage, int) {
	bytes, bytesRead, err := comm.Recv(from.Index)
	if err != nil {
		log.Fatalf("Failed to receive message: %v", err)
	}
	msg, err := tss.ParseWireMessage(bytes, &from, isBroadcast)
	if err != nil {
		log.Fatalf("Error parsing message: %v", err)
	}
	return msg, bytesRead
}

// Return list of participant IDs
func GetParticipantPartyIDs(numParties int) tss.SortedPartyIDs {
	var partyIds tss.UnSortedPartyIDs
	for i := 1; i <= numParties; i++ {
		partyIds = append(partyIds, tss.NewPartyID(strconv.Itoa(i), "", big.NewInt(int64(i))))
	}
	return tss.SortPartyIDs(partyIds)
}

func LocalPreParamsToString(params *keygen.LocalPreParams) string {
	data, err := json.Marshal(params)
	if err != nil {
		log.Fatalf("Unable to convert LocalPreParams to string: %v", err)
	}
	return string(data)
}

func LocalPreParamsFromString(s string) *keygen.LocalPreParams {
	var params keygen.LocalPreParams
	err := json.Unmarshal([]byte(s), &params)
	if err != nil {
		log.Fatalf("Unable to convert string to LocalPreParams: %v", err)
	}
	return &params
}

func LocalPartySaveDataToString(saveData *keygen.LocalPartySaveData) string {
	data, err := json.Marshal(saveData)
	if err != nil {
		log.Fatalf("Unable to convert LocalPartySaveData to string: %v", err)
	}
	return string(data)
}

func LocalPartySaveDataFromString(s string) *keygen.LocalPartySaveData {
	var saveData keygen.LocalPartySaveData
	err := json.Unmarshal([]byte(s), &saveData)
	if err != nil {
		log.Fatalf("Unable to convert string to LocalPartySaveData: %v", err)
	}
	return &saveData
}

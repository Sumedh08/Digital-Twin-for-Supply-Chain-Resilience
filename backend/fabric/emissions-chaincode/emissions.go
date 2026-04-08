package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract provides functions for managing emissions
type SmartContract struct {
	contractapi.Contract
}

// EmissionRecord describes the CO2 data
type EmissionRecord struct {
	ID            string  `json:"id"`
	CorrelationID string  `json:"correlationId"`
	PlantID       string  `json:"plantId"`
	SupplierID    string  `json:"supplierId"`
	Stage         string  `json:"stage"`
	CO2Tonnes     float64 `json:"co2Tonnes"`
	Timestamp     string  `json:"timestamp"`
	Verifier      string  `json:"verifier"`
}

// InitLedger adds a base set of emissions to the ledger
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	return nil
}

// RecordEmission adds a new emission record to the world state
func (s *SmartContract) RecordEmission(ctx contractapi.TransactionContextInterface, id string, correlationId string, plantId string, supplierId string, stage string, co2 float64) error {
	exists, err := s.EmissionExists(ctx, id)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("the emission record %s already exists", id)
	}

	record := EmissionRecord{
		ID:            id,
		CorrelationID: correlationId,
		PlantID:       plantId,
		SupplierID:    supplierId,
		Stage:         stage,
		CO2Tonnes:     co2,
		Timestamp:     time.Now().Format(time.RFC3339),
		Verifier:      "DigitalTwinEngine_Fabric_v1",
	}
	recordJSON, err := json.Marshal(record)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(id, recordJSON)
}

// QueryEmission returns the emission record stored in the world state with given id
func (s *SmartContract) QueryEmission(ctx contractapi.TransactionContextInterface, id string) (*EmissionRecord, error) {
	recordJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %v", err)
	}
	if recordJSON == nil {
		return nil, fmt.Errorf("the emission record %s does not exist", id)
	}

	var record EmissionRecord
	err = json.Unmarshal(recordJSON, &record)
	if err != nil {
		return nil, err
	}

	return &record, nil
}

// EmissionExists returns true when asset with given ID exists in world state
func (s *SmartContract) EmissionExists(ctx contractapi.TransactionContextInterface, id string) (bool, error) {
	recordJSON, err := ctx.GetStub().GetState(id)
	if err != nil {
		return false, fmt.Errorf("failed to read from world state: %v", err)
	}

	return recordJSON != nil, nil
}

// GetAllEmissions returns all emission records found in world state
func (s *SmartContract) GetAllEmissions(ctx contractapi.TransactionContextInterface) ([]*EmissionRecord, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var records []*EmissionRecord
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var record EmissionRecord
		err = json.Unmarshal(queryResponse.Value, &record)
		if err != nil {
			return nil, err
		}
		records = append(records, &record)
	}

	return records, nil
}

func main() {
	emissionChaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		log.Panicf("Error creating emissions chaincode: %v", err)
	}

	if err := emissionChaincode.Start(); err != nil {
		log.Panicf("Error starting emissions chaincode: %v", err)
	}
}

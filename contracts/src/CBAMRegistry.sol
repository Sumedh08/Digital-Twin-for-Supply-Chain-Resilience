// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CBAMRegistry
 * @dev On-chain registry for EU CBAM carbon emission compliance records.
 *      Deployed on Ethereum Sepolia Testnet for CarbonShip platform.
 * 
 * Each emission record is immutable once stored, providing:
 * - Tamper-proof audit trail for EU regulators
 * - Cross-border transparency between Indian exporters and EU importers
 * - Cryptographic verification via Etherscan
 */
contract CBAMRegistry {
    
    // ========== STATE VARIABLES ==========
    
    address public owner;
    uint256 public recordCount;
    
    // ========== STRUCTS ==========
    
    struct EmissionRecord {
        string shipmentId;
        string exporter;
        string product;
        uint256 weightTonnes;       // in whole tonnes
        uint256 totalCO2Kg;         // total CO2 in kg (scaled by 100 for 2 decimals)
        uint256 cbamTaxEurCents;    // CBAM tax in euro cents
        uint256 etsPriceEurCents;   // ETS price used, in euro cents
        string originPort;
        string destinationPort;
        address recordedBy;         // wallet that submitted
        uint256 timestamp;          // block.timestamp
        bool exists;
    }
    
    // ========== MAPPINGS ==========
    
    /// @dev shipmentId => EmissionRecord
    mapping(string => EmissionRecord) public records;
    
    /// @dev Array of all shipment IDs for enumeration
    string[] public allShipmentIds;
    
    // ========== EVENTS ==========
    
    /// @dev Emitted when a new emission record is stored on-chain
    event EmissionRecorded(
        string indexed shipmentId,
        string exporter,
        uint256 totalCO2Kg,
        uint256 cbamTaxEurCents,
        address recordedBy,
        uint256 timestamp
    );
    
    // ========== MODIFIERS ==========
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }
    
    // ========== CONSTRUCTOR ==========
    
    constructor() {
        owner = msg.sender;
        recordCount = 0;
    }
    
    // ========== WRITE FUNCTIONS ==========
    
    /**
     * @dev Record a CBAM emission calculation on-chain.
     *      Once recorded, data cannot be modified (immutable compliance).
     * @param _shipmentId Unique shipment identifier (e.g., "SHIP-1710832456789")
     * @param _exporter Name of the exporting company
     * @param _product Product type (e.g., "steel_hot_rolled")
     * @param _weightTonnes Weight in tonnes
     * @param _totalCO2Kg Total CO2 emissions in kg (scaled by 100)
     * @param _cbamTaxEurCents CBAM tax in euro cents
     * @param _etsPriceEurCents ETS price used in euro cents
     * @param _originPort Origin port name
     * @param _destinationPort Destination port name
     */
    function recordEmission(
        string calldata _shipmentId,
        string calldata _exporter,
        string calldata _product,
        uint256 _weightTonnes,
        uint256 _totalCO2Kg,
        uint256 _cbamTaxEurCents,
        uint256 _etsPriceEurCents,
        string calldata _originPort,
        string calldata _destinationPort
    ) external {
        require(bytes(_shipmentId).length > 0, "Shipment ID required");
        require(!records[_shipmentId].exists, "Record already exists");
        
        EmissionRecord memory newRecord = EmissionRecord({
            shipmentId: _shipmentId,
            exporter: _exporter,
            product: _product,
            weightTonnes: _weightTonnes,
            totalCO2Kg: _totalCO2Kg,
            cbamTaxEurCents: _cbamTaxEurCents,
            etsPriceEurCents: _etsPriceEurCents,
            originPort: _originPort,
            destinationPort: _destinationPort,
            recordedBy: msg.sender,
            timestamp: block.timestamp,
            exists: true
        });
        
        records[_shipmentId] = newRecord;
        allShipmentIds.push(_shipmentId);
        recordCount++;
        
        emit EmissionRecorded(
            _shipmentId,
            _exporter,
            _totalCO2Kg,
            _cbamTaxEurCents,
            msg.sender,
            block.timestamp
        );
    }
    
    // ========== READ FUNCTIONS ==========
    
    /**
     * @dev Retrieve a stored emission record by shipment ID
     */
    function getEmission(string calldata _shipmentId) external view returns (
        string memory exporter,
        string memory product,
        uint256 weightTonnes,
        uint256 totalCO2Kg,
        uint256 cbamTaxEurCents,
        uint256 etsPriceEurCents,
        string memory originPort,
        string memory destinationPort,
        address recordedBy,
        uint256 timestamp
    ) {
        require(records[_shipmentId].exists, "Record not found");
        EmissionRecord memory r = records[_shipmentId];
        return (
            r.exporter,
            r.product,
            r.weightTonnes,
            r.totalCO2Kg,
            r.cbamTaxEurCents,
            r.etsPriceEurCents,
            r.originPort,
            r.destinationPort,
            r.recordedBy,
            r.timestamp
        );
    }
    
    /**
     * @dev Verify that a record exists on-chain
     */
    function verifyRecord(string calldata _shipmentId) external view returns (
        bool exists,
        uint256 timestamp,
        address recordedBy
    ) {
        EmissionRecord memory r = records[_shipmentId];
        return (r.exists, r.timestamp, r.recordedBy);
    }
    
    /**
     * @dev Get total number of emission records
     */
    function getRecordCount() external view returns (uint256) {
        return recordCount;
    }
    
    /**
     * @dev Get the most recent N shipment IDs (for UI pagination)
     */
    function getRecentShipmentIds(uint256 count) external view returns (string[] memory) {
        uint256 total = allShipmentIds.length;
        uint256 returnCount = count > total ? total : count;
        string[] memory result = new string[](returnCount);
        
        for (uint256 i = 0; i < returnCount; i++) {
            result[i] = allShipmentIds[total - 1 - i];
        }
        return result;
    }
}

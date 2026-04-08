"""
Carbon Smart Contract System
============================
A simulated Blockchain Smart Contract for CBAM Compliance.

Architecture:
- Oracle Layer: Fetches real-time ETS price
- Compute Layer: Physics-based emission calculation
- Ledger Layer: Immutable record storage
- Verification Layer: Cryptographic proof

This simulates what would be deployed on Hyperledger Fabric or Polygon.
"""

import hashlib
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from backend.services.real_data_service import real_data_service

# ============================================
# BLOCKCHAIN CORE
# ============================================

class CarbonChainBlock:
    def __init__(self, index: int, timestamp: float, transactions: List[Dict], 
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 4):
        """Proof of Work: Find hash with 'difficulty' leading zeros"""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        return self.hash


class CarbonChain:
    def __init__(self):
        self.chain: List[CarbonChainBlock] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty = 4
        self.mining_reward = 0.01  # Carbon Credits
        
        # Create Genesis Block
        self._create_genesis_block()
    
    def _create_genesis_block(self):
        genesis = CarbonChainBlock(0, time.time(), [], "0")
        genesis.hash = genesis.calculate_hash()
        self.chain.append(genesis)
    
    def get_latest_block(self) -> CarbonChainBlock:
        return self.chain[-1]
    
    def add_transaction(self, transaction: Dict) -> int:
        """Add transaction to pending pool"""
        transaction["id"] = hashlib.sha256(
            json.dumps(transaction, sort_keys=True).encode()
        ).hexdigest()[:16]
        self.pending_transactions.append(transaction)
        return len(self.chain)
    
    def mine_pending_transactions(self, miner_address: str = "CarbonShip-Node-1") -> CarbonChainBlock:
        """Mine all pending transactions into a new block"""
        block = CarbonChainBlock(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=self.pending_transactions.copy(),
            previous_hash=self.get_latest_block().hash
        )
        
        # Mine the block
        block.mine_block(self.difficulty)
        
        # Add to chain
        self.chain.append(block)
        
        # Clear pending
        self.pending_transactions = []
        
        return block
    
    def is_chain_valid(self) -> bool:
        """Verify entire chain integrity"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True
    
    def get_chain_data(self) -> List[Dict]:
        """Export chain for API"""
        return [{
            "index": block.index,
            "timestamp": datetime.fromtimestamp(block.timestamp).isoformat(),
            "transactions": block.transactions,
            "hash": block.hash,
            "previous_hash": block.previous_hash,
            "nonce": block.nonce
        } for block in self.chain]


# ============================================
# ORACLE SERVICE (External Data Feeds)
# ============================================

class CarbonOracle:
    """Provides trusted external data to the Smart Contract"""
    
    def __init__(self):
        self.ets_price_eur = 85.0
        self.ets_price_source = "Warm fallback"
        self.ets_price_is_live = False
        self.exchange_rate_eur_inr = 89.5
        # GLEC Framework v3.0 emission factors (kg CO2 per tonne-km)
        self.emission_factors = {
            "sea_container": 0.01614,
            "sea_bulk": 0.004,
            "sea_tanker": 0.00511,
            "sea_roro": 0.0213,
            "sea_general_cargo": 0.0122,
            "container_ship": 0.01614,
            "bulk_carrier": 0.004,
            "oil_tanker": 0.00511,
            "roro_cargo": 0.0213,
            "general_cargo": 0.0122,
            "rail": 0.000230,
            "truck": 0.000800
        }
    
    def get_ets_price(self) -> float:
        """Fetch current EU ETS price from the shared live data service."""
        try:
            price = real_data_service.get_real_carbon_price_sync()
            self.ets_price_eur = float(price.price_eur)
            self.ets_price_source = price.source
            self.ets_price_is_live = bool(price.is_live)
        except Exception as exc:  # noqa: BLE001
            print(f"Oracle ETS refresh failed: {exc}")
        return self.ets_price_eur

    def get_ets_metadata(self) -> Dict[str, object]:
        return {
            "ets_price_eur": self.ets_price_eur,
            "source": self.ets_price_source,
            "is_live": self.ets_price_is_live,
        }
    
    def get_emission_factor(self, transport_mode: str) -> float:
        """Get emission factor for transport mode"""
        return self.emission_factors.get(transport_mode, 0.008)
    
    def get_timestamp(self) -> str:
        return datetime.now().isoformat()


# ============================================
# SMART CONTRACT (Business Logic)
# ============================================

@dataclass
class ShipmentData:
    shipment_id: str
    exporter: str
    product_type: str
    weight_tonnes: float
    origin_port: str
    destination_port: str
    distance_km: float
    transport_mode: str = "container_ship"
    origin_country: str = "India"
    ship_type: str = "Container Ship"
    
@dataclass 
class EmissionReceipt:
    contract_address: str
    shipment_id: str
    transport_co2_kg: float
    manufacturing_co2_kg: float
    total_co2_kg: float
    cbam_tax_eur: float
    cbam_tax_inr: float
    ets_price_used: float
    block_hash: str
    transaction_id: str
    verified: bool
    timestamp: str


class CarbonSmartContract:
    """
    Main Smart Contract for CBAM Compliance
    
    Deployed on: CarbonChain (Private Blockchain)
    Contract Address: 0x71C7656EC7ab88b098defB751B7401B5f6d8976F
    """
    
    CONTRACT_ADDRESS = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    CONTRACT_VERSION = "1.0.0"
    
    # Manufacturing emission factors (tonnes CO2 per tonne product) - from IPCC EFDB
    MANUFACTURING_FACTORS = {
        "steel_hot_rolled": 1.85,
        "steel_cold_rolled": 2.10,
        "steel_pipes": 1.95,
        "steel_wire": 1.80,
        "aluminium_primary": 14.5,
        "aluminium_secondary": 0.6,
        "aluminium_products": 8.0,
        "cement_clinker": 0.85,
        "cement_portland": 0.65,
        "ammonia": 1.80,
        "urea": 0.73,
        "nitric_acid": 2.60,
        "hydrogen_grey": 9.0,
        "hydrogen_blue": 4.5,
        "iron": 1.35
    }
    
    def __init__(self, chain: CarbonChain, oracle: CarbonOracle):
        self.chain = chain
        self.oracle = oracle
        self.execution_count = 0
    
    def calculate_transport_emissions(self, shipment: ShipmentData) -> float:
        """
        GLEC-based transport emission calculation
        
        Formula: CO2 = Weight * Distance * EmissionFactor
        Source: GLEC Framework v3.0 / Clean Cargo 2024
        """
        base_factor = self.oracle.get_emission_factor(shipment.transport_mode)
        
        # Calculate transport CO2 in kg (factor is in kg CO2/tonne-km)
        transport_co2 = (
            shipment.weight_tonnes * 
            shipment.distance_km * 
            base_factor
        )
        
        return round(transport_co2, 2)
    
    def calculate_manufacturing_emissions(self, product_type: str, weight: float) -> float:
        """Calculate embedded manufacturing emissions"""
        factor = self.MANUFACTURING_FACTORS.get(product_type, 1.5)
        return round(weight * factor * 1000, 2)  # Convert to kg
    
    def execute(self, shipment: ShipmentData) -> EmissionReceipt:
        """
        Main contract execution function.
        
        This is the equivalent of calling a Solidity function.
        It calculates emissions and writes to the blockchain.
        """
        self.execution_count += 1
        
        # Step 1: Calculate Transport Emissions
        transport_co2 = self.calculate_transport_emissions(shipment)
        
        # Step 2: Calculate Manufacturing Emissions
        manufacturing_co2 = self.calculate_manufacturing_emissions(
            shipment.product_type, 
            shipment.weight_tonnes
        )
        
        # Step 3: Total Emissions
        total_co2_kg = transport_co2 + manufacturing_co2
        total_co2_tonnes = total_co2_kg / 1000
        
        # Step 4: Get Oracle Price
        ets_price = self.oracle.get_ets_price()
        
        # Step 5: Calculate Tax
        cbam_tax_eur = round(total_co2_tonnes * ets_price, 2)
        cbam_tax_inr = round(cbam_tax_eur * self.oracle.exchange_rate_eur_inr, 2)
        
        # Step 6: Create Transaction
        transaction = {
            "type": "CBAM_CALCULATION",
            "shipment_id": shipment.shipment_id,
            "exporter": shipment.exporter,
            "product": shipment.product_type,
            "weight_tonnes": shipment.weight_tonnes,
            "route": f"{shipment.origin_port} -> {shipment.destination_port}",
            "distance_km": shipment.distance_km,
            "transport_co2_kg": transport_co2,
            "manufacturing_co2_kg": manufacturing_co2,
            "total_co2_kg": total_co2_kg,
            "ets_price_eur": ets_price,
            "cbam_tax_eur": cbam_tax_eur,
            "cbam_tax_inr": cbam_tax_inr,
            "timestamp": self.oracle.get_timestamp(),
            "contract_version": self.CONTRACT_VERSION
        }
        
        # Step 7: Add to Pending Transactions
        self.chain.add_transaction(transaction)
        
        # Step 8: Mine Block (Auto-Settlement)
        block = self.chain.mine_pending_transactions()
        
        # Step 9: Create Receipt
        receipt = EmissionReceipt(
            contract_address=self.CONTRACT_ADDRESS,
            shipment_id=shipment.shipment_id,
            transport_co2_kg=transport_co2,
            manufacturing_co2_kg=manufacturing_co2,
            total_co2_kg=total_co2_kg,
            cbam_tax_eur=cbam_tax_eur,
            cbam_tax_inr=cbam_tax_inr,
            ets_price_used=ets_price,
            block_hash=block.hash,
            transaction_id=transaction.get("id", "unknown"),
            verified=True,
            timestamp=self.oracle.get_timestamp()
        )
        
        return receipt
    
    def verify_receipt(self, block_hash: str) -> Dict:
        """Verify a receipt exists on chain"""
        for block in self.chain.chain:
            if block.hash == block_hash:
                return {
                    "verified": True,
                    "block_index": block.index,
                    "timestamp": datetime.fromtimestamp(block.timestamp).isoformat(),
                    "transactions": len(block.transactions),
                    "chain_valid": self.chain.is_chain_valid()
                }
        return {"verified": False}


# ============================================
# SINGLETON INSTANCES
# ============================================

carbon_chain = CarbonChain()
carbon_oracle = CarbonOracle()
carbon_contract = CarbonSmartContract(carbon_chain, carbon_oracle)

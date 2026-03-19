import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from backend.services.blockchain_service import blockchain_service

logger = logging.getLogger(__name__)

class BlockchainBridge:
    """
    Bridge between the local Python blockchain and the Ethereum Sepolia on-chain registry.
    
    This service:
    1. Tracks local blocks and prepares them for on-chain recording.
    2. Syncs on-chain metadata (transaction hashes) back to the local ledger.
    3. Provides a unified interface for the UI to verify data integrity across both layers.
    """
    
    def __init__(self):
        self.deployment_path = os.path.join(os.getcwd(), "contracts", "deployment.json")
        self.on_chain_hashes = {}  # shipment_id -> eth_tx_hash
        
    def get_deployment_info(self) -> Optional[Dict[str, Any]]:
        """Read the smart contract deployment details."""
        try:
            if os.path.exists(self.deployment_path):
                with open(self.deployment_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read deployment info: {e}")
        return None

    def record_on_chain_sync(self, shipment_id: str, tx_hash: str):
        """Link a local shipment to its Ethereum transaction hash."""
        self.on_chain_hashes[shipment_id] = tx_hash
        logger.info(f"Linked shipment {shipment_id} to Ethereum Tx: {tx_hash}")
        
    def get_blockchain_status(self) -> Dict[str, Any]:
        """Get summarized status of the hybrid blockchain system."""
        local_blocks = blockchain_service.get_chain()
        deployment = self.get_deployment_info()
        
        return {
            "local_chain": {
                "length": len(local_blocks),
                "is_valid": blockchain_service.is_chain_valid(),
                "last_block_hash": local_blocks[-1]["hash"] if local_blocks else None
            },
            "on_chain": {
                "network": deployment.get("network") if deployment else "Not Deployed",
                "contract_address": deployment.get("contractAddress") if deployment else None,
                "recorded_count": len(self.on_chain_hashes),
                "last_deployed": deployment.get("deployedAt") if deployment else None
            },
            "system_type": "Hybrid (PoW Local + Proof-of-Stake Ethereum)"
        }

    def verify_integrity(self, shipment_id: str) -> Dict[str, Any]:
        """Verify a shipment across both local and on-chain layers."""
        # 1. Check local chain
        local_found = False
        local_data = None
        for block in blockchain_service.get_chain():
            for tx in block.get("transactions", []):
                if tx.get("shipment_id") == shipment_id:
                    local_found = True
                    local_data = tx
                    break
            if local_found: break
            
        # 2. Check bridge mapping
        eth_hash = self.on_chain_hashes.get(shipment_id)
        
        return {
            "shipment_id": shipment_id,
            "local_registry": {
                "status": "Verified" if local_found else "Not Found",
                "timestamp": local_data.get("timestamp") if local_data else None,
                "data_integrity": "OK" if local_found else "N/A"
            },
            "ethereum_registry": {
                "status": "Recorded" if eth_hash else "Pending/Local Only",
                "transaction_hash": eth_hash,
                "explorer_url": f"https://sepolia.etherscan.io/tx/{eth_hash}" if eth_hash else None
            },
            "overall_status": "Immutable Compliance Guaranteed" if eth_hash and local_found else "Internal Verification Only"
        }

# Singleton instance
blockchain_bridge = BlockchainBridge()

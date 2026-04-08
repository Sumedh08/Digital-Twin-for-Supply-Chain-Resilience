from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Protocol

from backend.services.india_steel_twin_store import IndiaSteelTwinStore


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class LedgerBackend(Protocol):
    def metadata(self) -> Dict[str, Any]:
        ...

    def record_stage(
        self,
        *,
        correlation_id: str,
        plant_id: str,
        supplier_id: str,
        stage: str,
        thing_id: str,
        emission: float,
        payload: Dict[str, Any],
        timestamp: str,
        world_state_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        ...

    def get_ledger(self, correlation_id: str | None = None) -> Dict[str, Any]:
        ...

    def get_evidence_bundle(
        self,
        *,
        correlation_id: str,
        run: Dict[str, Any],
        system_state: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        ...


class LocalAuditLedgerBackend:
    backend_id = "local_audit"
    phase = "phase_1"
    target = "hyperledger_fabric"
    description = (
        "Local append-only audit chain with Fabric-ready evidence records. "
        "Phase 2 swaps the backend adapter to a real Hyperledger Fabric network."
    )

    def __init__(self, store: IndiaSteelTwinStore) -> None:
        self.store = store

    def metadata(self) -> Dict[str, Any]:
        return {
            "id": self.backend_id,
            "phase": self.phase,
            "target": self.target,
            "description": self.description,
            "fabricReady": True,
        }

    def record_stage(
        self,
        *,
        correlation_id: str,
        plant_id: str,
        supplier_id: str,
        stage: str,
        thing_id: str,
        emission: float,
        payload: Dict[str, Any],
        timestamp: str,
        world_state_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        existing = self.store.list_blocks(correlation_id)
        previous_hash = existing[-1]["current_hash"] if existing else "GENESIS"
        block_index = len(existing) + 1
        world_state_digest = _stable_digest(world_state_snapshot)
        payload_for_chain = {
            **payload,
            "recordType": payload.get("recordType", "EmissionCheckpoint"),
        }

        body = {
            "chain_id": f"{plant_id}:{correlation_id}",
            "correlation_id": correlation_id,
            "index": block_index,
            "stage": stage,
            "thing_id": thing_id,
            "plant_id": plant_id,
            "supplier_id": supplier_id,
            "emission": round(emission, 4),
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "world_state_digest": world_state_digest,
            "payload": payload_for_chain,
        }
        current_hash = _stable_digest(body)
        tx_id = f"local:{block_index}:{current_hash[:16]}"

        record_payload = {
            **payload_for_chain,
            "plantId": plant_id,
            "supplierId": supplier_id,
            "worldStateDigest": world_state_digest,
            "txId": tx_id,
            "priorReference": previous_hash,
        }
        block = {
            "correlationId": correlation_id,
            "chainId": body["chain_id"],
            "index": block_index,
            "stage": stage,
            "thingId": thing_id,
            "emission": round(emission, 4),
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "current_hash": current_hash,
            "payload": record_payload,
        }
        self.store.record_block(block)
        return block

    def get_ledger(self, correlation_id: str | None = None) -> Dict[str, Any]:
        blocks = self.store.list_blocks(correlation_id)
        previous_hash = "GENESIS"
        valid = True
        normalized = []
        for block in blocks:
            normalized_payload = {
                key: value
                for key, value in block["payload"].items()
                if key
                not in {
                    "txId",
                    "priorReference",
                    "plantId",
                    "supplierId",
                    "worldStateDigest",
                }
            }
            body = {
                "chain_id": block["chain_id"],
                "correlation_id": block["correlation_id"],
                "index": block["block_index"],
                "stage": block["stage"],
                "thing_id": block["thing_id"],
                "plant_id": block["payload"].get("plantId"),
                "supplier_id": block["payload"].get("supplierId"),
                "emission": block["emission"],
                "timestamp": block["created_at"],
                "previous_hash": previous_hash,
                "world_state_digest": block["payload"].get("worldStateDigest"),
                "payload": normalized_payload,
            }
            expected = _stable_digest(body)
            if block["previous_hash"] != previous_hash or block["current_hash"] != expected:
                valid = False
            previous_hash = block["current_hash"]
            normalized.append(
                {
                    "index": block["block_index"],
                    "stage": block["stage"],
                    "thingId": block["thing_id"],
                    "emission": block["emission"],
                    "timestamp": block["created_at"],
                    "previousHash": block["previous_hash"],
                    "currentHash": block["current_hash"],
                    "txId": block["payload"].get("txId"),
                    "worldStateDigest": block["payload"].get("worldStateDigest"),
                    "payload": block["payload"],
                }
            )

        return {
            **self.metadata(),
            "chainLength": len(normalized),
            "isValid": valid,
            "blocks": normalized,
        }

    def get_evidence_bundle(
        self,
        *,
        correlation_id: str,
        run: Dict[str, Any],
        system_state: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        ledger = self.get_ledger(correlation_id)
        stage_events = []
        for event in events:
            snapshot = event.get("payload", {}).get("worldStateSnapshot", {})
            stage_events.append(
                {
                    "recordType": "StageEvent",
                    "eventId": event["event_id"],
                    "correlationId": event["correlation_id"],
                    "thingId": event["thing_id"],
                    "eventType": event["event_type"],
                    "stage": event["stage"],
                    "fromState": event["from_state"],
                    "toState": event["to_state"],
                    "timestamp": event["created_at"],
                    "worldStateDigest": _stable_digest(snapshot),
                }
            )

        emission_checkpoints = [
            {
                "recordType": "EmissionCheckpoint",
                "correlationId": correlation_id,
                "stage": block["stage"],
                "thingId": block["thingId"],
                "timestamp": block["timestamp"],
                "txId": block["txId"],
                "currentHash": block["currentHash"],
                "previousHash": block["previousHash"],
                "worldStateDigest": block["worldStateDigest"],
                "emission": block["payload"].get("emission", {}),
                "totalTco2": block["emission"],
            }
            for block in ledger["blocks"]
        ]

        batch_run = {
            "recordType": "BatchRun",
            "correlationId": correlation_id,
            "plantId": run["result"]["plantId"],
            "scenarioId": run["scenario_id"],
            "supplierThingId": run["supplier_thing_id"],
            "batchTonnes": run["batch_tonnes"],
            "status": run["status"],
            "createdAt": run["created_at"],
            "updatedAt": run["updated_at"],
            "ledgerBackend": self.metadata(),
        }

        return {
            "recordType": "EvidenceBundle",
            "correlationId": correlation_id,
            "ledgerBackend": self.metadata(),
            "batchRun": batch_run,
            "finalEmissions": system_state["aggregatedEmissions"],
            "ledgerReferences": [
                {
                    "index": block["index"],
                    "stage": block["stage"],
                    "txId": block["txId"],
                    "timestamp": block["timestamp"],
                    "currentHash": block["currentHash"],
                    "previousHash": block["previousHash"],
                }
                for block in ledger["blocks"]
            ],
            "stageEvents": stage_events,
            "emissionCheckpoints": emission_checkpoints,
            "verification": {
                "chainLength": ledger["chainLength"],
                "isValid": ledger["isValid"],
                "backend": self.backend_id,
                "target": self.target,
            },
        }

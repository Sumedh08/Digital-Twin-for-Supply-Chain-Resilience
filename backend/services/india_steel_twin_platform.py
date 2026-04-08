from __future__ import annotations

import json
import math
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.india_steel_twin_store import IndiaSteelTwinStore
from backend.services.twin_ledger import LedgerBackend, LocalAuditLedgerBackend
from backend.services.hyperledger_fabric_backend import HyperledgerFabricBackend
import logging
logger = logging.getLogger(__name__)
if not hasattr(logger, "bind"):
    logger.bind = lambda **kwargs: logger


DATA_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "india_steel_hrc_supply_chain.json"
)
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class IndiaSteelTwinError(Exception):
    pass


class RevisionConflictError(IndiaSteelTwinError):
    pass


class InvalidTransitionError(IndiaSteelTwinError):
    pass


class IndiaSteelTwinPlatform:
    POLICY_ID = "org.carbonship.india.steel.policy.sail.phase1"
    SUPPLIER_DEFINITION = "org.eclipse.ditto:SupplierTwin:3.0.0"
    PLANT_DEFINITION = "org.eclipse.ditto:PlantTwin:3.0.0"
    TRANSPORT_DEFINITION = "org.eclipse.ditto:TransportTwin:3.0.0"
    PORT_DEFINITION = "org.eclipse.ditto:PortTwin:3.0.0"
    STAGE_SEQUENCE = [
        "supplier.selected",
        "supplier.dispatched",
        "plant.received_material",
        "plant.production_completed",
        "transport.assigned",
        "transport.departed",
        "transport.arrived_port",
        "transport.unloaded",
        "port.received",
        "port.customs_cleared",
        "port.delivered",
    ]
    SUPPLIER_FLOW = ["raw", "allocated", "dispatched", "received_by_plant"]
    PLANT_FLOW = ["idle", "processing", "packed", "handed_to_transport"]
    TRANSPORT_FLOW = ["created", "assigned", "in_transit", "at_port", "unloaded"]
    PORT_FLOW = ["queued", "received", "customs_cleared", "delivered"]

    def __init__(
        self,
        data_path: Path = DATA_PATH,
        store: Optional[IndiaSteelTwinStore] = None,
        ledger_backend: Optional[LedgerBackend] = None,
    ) -> None:
        with open(data_path, "r", encoding="utf-8") as handle:
            self.data = json.load(handle)
        self.store = store or IndiaSteelTwinStore()
        
        # Priority: Hyperledger Fabric -> Local Audit Ledger Fallback
        self.ledger_backend: LedgerBackend = ledger_backend
        if self.ledger_backend is None:
            try:
                # Try real Fabric first
                self.ledger_backend = HyperledgerFabricBackend(self.store)
                logger.info("IndiaSteelTwin: Initialized real Hyperledger Fabric backend.")
            except Exception as e:
                logger.warning(f"IndiaSteelTwin: Fabric init failed, falling back to local. Error: {e}")
                self.ledger_backend = LocalAuditLedgerBackend(self.store)
        assert self.ledger_backend is not None

        self.plants_by_id = {
            plant["id"]: plant for plant in self.data["plants"].values()
        }
        self.suppliers_by_id = {
            supplier["id"]: supplier for supplier in self.data["suppliers"].values()
        }
        self.ports_by_id = {
            port["id"]: port for port in self.data["ports"].values()
        }
        self.scenarios_by_id = {
            scenario["scenarioId"]: scenario for scenario in self.data["plantSupplierScenarios"]
        }
        self.scenarios_by_plant: Dict[str, List[Dict[str, Any]]] = {}
        for scenario in self.data["plantSupplierScenarios"]:
            self.scenarios_by_plant.setdefault(scenario["plantId"], []).append(scenario)
        for scenarios in self.scenarios_by_plant.values():
            scenarios.sort(key=lambda item: item["label"])

    def get_context(self, plant_id: Optional[str] = None) -> Dict[str, Any]:
        selected_plant = self._maybe_plant(plant_id)
        selected_port = None if not selected_plant else self._port_profile(selected_plant["port_id"])
        scenarios = self.list_scenarios(plant_id) if selected_plant else []
        benchmark = None
        if selected_plant:
            benchmark = self.compare_scenarios(
                plant_id,
                self.data["execution_defaults"]["default_batch_tonnes"],
            )

        return {
            "title": "SAIL Multi-Plant Steel Digital Twin",
            "summary": (
                f"Monitor supplier choice, plant processing, dispatch, and port delivery for "
                f"{selected_plant['label']}."
                if selected_plant
                else "Select a SAIL integrated steel plant to load suppliers, corridor context, and the active simulation network."
            ),
            "ledgerBackend": self.ledger_backend.metadata(),
            "plant_selection": {
                "selectedPlantId": plant_id,
                "plants": self.list_plants(),
            },
            "product_selection": {
                "product": self.data["project"]["product_label"],
                "supply_chain": (
                    f"Supplier -> {selected_plant['label']} -> {selected_port['label']}"
                    if selected_plant and selected_port
                    else "Choose a plant to activate its supplier and export corridor graph."
                ),
                "suppliers": scenarios,
            },
            "spatialReference": {
                "overviewPlants": [self._spatial_node_ref(plant) for plant in self.list_plants(raw=True)],
                "overviewPorts": [self._spatial_port_ref(port) for port in self.ports_by_id.values()],
                "selectedPlant": None if not selected_plant else self._spatial_node_ref(selected_plant),
                "selectedPort": None if not selected_port else self._spatial_port_ref(selected_port),
                "supplierCandidates": [
                    self._spatial_supplier_ref(self._supplier_profile(scenario["supplierId"]))
                    for scenario in self._scenarios_for_plant(plant_id)
                ]
                if selected_plant
                else [],
            },
            "architecture": self._architecture(),
            "framework_alignment": self.framework_alignment(),
            "benchmark": None if benchmark is None else benchmark["benchmarks"],
            "source_traceability": self.data["sources"],
        }

    def list_plants(self, raw: bool = False) -> List[Dict[str, Any]]:
        plants = []
        for plant in sorted(self.plants_by_id.values(), key=lambda item: item["label"]):
            if raw:
                plants.append(plant)
                continue
            port = self._port_profile(plant["port_id"])
            plants.append(
                {
                    "plantId": plant["id"],
                    "label": plant["label"],
                    "shortLabel": self._short_label(plant["label"]),
                    "operator": plant["operator"],
                    "state": plant["state"],
                    "district": plant["district"],
                    "lat": plant["lat"],
                    "lon": plant["lon"],
                    "portLabel": port["label"],
                    "supplierCount": len(self._scenarios_for_plant(plant["id"])),
                    "processRoute": "Integrated BF-BOF + HSM",
                }
            )
        return plants

    def list_scenarios(self, plant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        scenarios = []
        for scenario in self._scenarios_for_plant(plant_id):
            supplier = self._supplier_profile(scenario["supplierId"])
            plant = self._plant_profile(scenario["plantId"])
            scenarios.append(
                {
                    "scenarioId": scenario["scenarioId"],
                    "plantId": plant["id"],
                    "thingId": supplier["id"],
                    "label": supplier["label"],
                    "shortLabel": self._short_label(supplier["label"]),
                    "story": scenario["story"],
                    "lat": supplier["lat"],
                    "lon": supplier["lon"],
                    "distanceToPlantKm": round(
                        float(self._distance_km(
                            supplier["lat"],
                            supplier["lon"],
                            plant["lat"],
                            plant["lon"],
                            scenario["distanceMultiplier"],
                        )),
                        1,
                    ),
                    "modeToPlant": scenario["modeToPlant"],
                }
            )
        return scenarios

    def framework_alignment(self) -> Dict[str, Any]:
        return {
            "viewerMode": "globe-3d",
            "ledgerBackend": self.ledger_backend.metadata(),
            "frameworks": [
                {
                    "name": "Eclipse Ditto",
                    "whatIsImplemented": [
                        "Thing-style contracts with plant, supplier, transport, and port twins",
                        "Desired, reported, and current state layers on each feature",
                        "Scenario execution through persisted event transitions",
                    ],
                    "visibleOnPage": "Twin registry, inspector, transition timeline",
                    "reference": "https://eclipse.dev/ditto/",
                },
                {
                    "name": "Local Audit Ledger",
                    "whatIsImplemented": [
                        "Append-only hashed checkpoint chain for every simulated run",
                        "Fabric-ready record envelopes for BatchRun, StageEvent, EmissionCheckpoint, and EvidenceBundle",
                        "Stable ledger backend interface ready for a Hyperledger Fabric adapter",
                    ],
                    "visibleOnPage": "Ledger panel and evidence endpoint",
                    "reference": "https://hyperledger-fabric.readthedocs.io/",
                },
                {
                    "name": "Hyperledger Fabric",
                    "whatIsImplemented": [
                        "Phase 1 abstraction completed so the twin writes normalized ledger records through a backend interface",
                        "Phase 2 target is a real Fabric adapter and chaincode-backed authority ledger",
                        "Current UI already surfaces normalized tx and checkpoint metadata that can be mapped to Fabric later",
                    ],
                    "visibleOnPage": "Ledger metadata and authority evidence output",
                    "reference": "https://hyperledger-fabric.readthedocs.io/",
                },
                {
                    "name": "LF Energy",
                    "whatIsImplemented": [
                        "Structured Scope 1, 2, and 3 fields across every twin and checkpoint",
                        "Explainable carbon accounting fields for authority review",
                        "Open telemetry semantics aligned to interoperable decarbonisation workflows",
                    ],
                    "visibleOnPage": "Emission snapshot and ledger evidence",
                    "reference": "https://lfenergy.org/",
                },
                {
                    "name": "iTwin.js",
                    "whatIsImplemented": [
                        "Plant overview plus active scenario overlay on a 3D globe",
                        "Supplier, plant, transport, and port topology rendering",
                        "Replayable corridor transitions driven by the twin event history",
                    ],
                    "visibleOnPage": "Center spatial canvas",
                    "reference": "https://developer.bentley.com/apis/visualization/",
                },
            ],
        }

    def create_twin(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        entity_type = self._entity_type_for_definition(payload["definition"])
        normalized = self._normalize_thing(payload, entity_type, correlation_id=None)
        return self.store.upsert_twin(
            normalized,
            entity_type=entity_type,
            updated_at=now_ist(),
            correlation_id=None,
            event_id=None,
        )

    def list_twins(self) -> List[Dict[str, Any]]:
        return [json.loads(row["thing_json"]) for row in self.store.list_twins()]

    def get_twin(self, thing_id: str) -> Dict[str, Any]:
        row = self.store.get_twin(thing_id)
        if row is None:
            raise IndiaSteelTwinError(f"Twin '{thing_id}' not found")
        return json.loads(row["thing_json"])

    def get_events(
        self,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        effective = correlation_id
        if effective is None:
            active = self.store.get_active_run()
            effective = None if active is None else active["correlation_id"]
        return self.store.list_events(effective, limit=limit)

    def stream_events(self, correlation_id: Optional[str] = None) -> str:
        events = self.get_events(correlation_id)
        payload = []
        for event in events:
            payload.append(f"event: {event['event_type']}\ndata: {json.dumps(event)}\n")
        payload.append("event: heartbeat\ndata: {\"status\":\"open\"}\n")
        return "\n".join(payload) + "\n\n"

    def get_evidence_bundle(self, correlation_id: str) -> Dict[str, Any]:
        run = self.store.get_run(correlation_id)
        if run is None:
            raise IndiaSteelTwinError(f"Run '{correlation_id}' not found")
        system_state = self.get_system_state(correlation_id)
        events = self.get_events(correlation_id)
        evidence = self.ledger_backend.get_evidence_bundle(
            correlation_id=correlation_id,
            run=run,
            system_state=system_state,
            events=events,
        )
        return {
            "correlationId": correlation_id,
            "plantId": run["result"]["plantId"],
            "supplierThingId": run["supplier_thing_id"],
            "ledgerBackend": self.ledger_backend.metadata(),
            "evidenceBundle": evidence,
        }

    def patch_twin(
        self,
        thing_id: str,
        layer: str,
        feature_name: str,
        properties: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
        expected_revision: Optional[int],
    ) -> Dict[str, Any]:
        row = self.store.get_twin(thing_id)
        if row is None:
            raise IndiaSteelTwinError(f"Twin '{thing_id}' not found")
        thing = json.loads(row["thing_json"])
        current_revision = int(row["revision"])
        if expected_revision is not None and current_revision != expected_revision:
            raise RevisionConflictError(
                f"Revision mismatch for '{thing_id}': expected {expected_revision}, found {current_revision}"
            )
        if feature_name == "lifecycle":
            raise InvalidTransitionError(
                "Lifecycle state can only be changed through the transition engine"
            )
        if feature_name not in thing["features"]:
            raise IndiaSteelTwinError(f"Feature '{feature_name}' not found on '{thing_id}'")

        feature = thing["features"][feature_name]
        feature["properties"][layer] = deep_merge(
            feature["properties"].get(layer, {}), properties
        )
        if layer == "reported":
            feature["properties"]["current"] = deepcopy(feature["properties"]["reported"])
        elif feature_name in {"location", "materialFlow"}:
            feature["properties"]["current"] = deep_merge(
                feature["properties"].get("current", {}),
                feature["properties"]["desired"],
            )

        feature["metadata"] = deep_merge(feature.get("metadata", {}), metadata or {})
        feature["metadata"]["lastUpdated"] = now_ist()
        feature["metadata"]["source"] = layer

        return self.store.upsert_twin(
            thing,
            entity_type=thing["metadata"]["entityType"],
            updated_at=feature["metadata"]["lastUpdated"],
            correlation_id=thing["metadata"].get("correlationId"),
            event_id=None,
        )

    def execute_scenario(
        self,
        plant_id: Optional[str],
        scenario_id: Optional[str] = None,
        supplier_thing_id: str | float = "",
        batch_tonnes: Optional[float] = None,
    ) -> Dict[str, Any]:
        if batch_tonnes is None and isinstance(supplier_thing_id, (int, float, str)) and str(supplier_thing_id).replace('.', '', 1).isdigit():
            batch_tonnes = float(supplier_thing_id)
            supplier_thing_id = scenario_id or ""
            scenario_id = None
            plant_id = None
        if batch_tonnes is None:
            raise IndiaSteelTwinError("Batch tonnes are required to execute a scenario")
        scenario = self._resolve_scenario(plant_id, scenario_id, supplier_thing_id)
        correlation_id = f"run-{uuid.uuid4().hex[:12]}"
        run = self._bootstrap_run(correlation_id, scenario, batch_tonnes)
        while run["result"]["stepIndex"] < len(self.STAGE_SEQUENCE):
            run = self._advance_run(
                run,
                action="next",
                supplier_thing_id=supplier_thing_id,
                truck_ids=run["result"]["dispatchUnitIds"],
            )
        result = self._build_run_result(
            correlation_id,
            scenario,
            batch_tonnes,
            run_status=run["status"],
            current_stage=run["result"]["currentStage"],
            last_applied_action=run["result"]["lastAppliedAction"],
            step_index=run["result"]["stepIndex"],
            metrics=run["result"]["metrics"],
            dispatch_unit_ids=run["result"]["dispatchUnitIds"],
            thing_ids=run["result"]["thingIds"],
            port_id=run["result"]["portId"],
        )
        self.store.upsert_scenario_run(
            correlation_id=correlation_id,
            scenario_id=scenario["scenarioId"],
            supplier_thing_id=supplier_thing_id,
            batch_tonnes=batch_tonnes,
            status="completed",
            result=result,
            timestamp=now_ist(),
            is_active=True,
        )
        return result

    def advance_transition(
        self,
        correlation_id: str,
        action: str,
        plant_id: Optional[str],
        source_thing_id: Optional[str],
        target_thing_id: Optional[str],
        batch_tonnes: float,
        truck_ids: Optional[List[str]],
    ) -> Dict[str, Any]:
        del target_thing_id
        run = self.store.get_run(correlation_id)
        if run is None:
            scenario = self._resolve_scenario(plant_id, None, source_thing_id)
            run = self._bootstrap_run(correlation_id, scenario, batch_tonnes)

        run = self._advance_run(
            run,
            action=action or "next",
            supplier_thing_id=source_thing_id,
            truck_ids=truck_ids or run["result"]["dispatchUnitIds"],
        )
        scenario = self.scenarios_by_id[run["scenario_id"]]
        result = self._build_run_result(
            correlation_id,
            scenario,
            run["batch_tonnes"],
            run_status=run["status"],
            current_stage=run["result"]["currentStage"],
            last_applied_action=run["result"]["lastAppliedAction"],
            step_index=run["result"]["stepIndex"],
            metrics=run["result"]["metrics"],
            dispatch_unit_ids=run["result"]["dispatchUnitIds"],
            thing_ids=run["result"]["thingIds"],
            port_id=run["result"]["portId"],
        )
        self.store.upsert_scenario_run(
            correlation_id=correlation_id,
            scenario_id=run["scenario_id"],
            supplier_thing_id=run["supplier_thing_id"],
            batch_tonnes=run["batch_tonnes"],
            status=run["status"],
            result=result,
            timestamp=now_ist(),
            is_active=True,
        )
        return result

    def compare_scenarios(
        self,
        plant_id: Optional[str] | float,
        batch_tonnes: Optional[float] = None,
    ) -> Dict[str, Any]:
        if batch_tonnes is None and isinstance(plant_id, (int, float)):
            batch_tonnes = float(plant_id)
            plant_id = self.data["execution_defaults"]["default_plant_id"]
        if batch_tonnes is None:
            raise IndiaSteelTwinError("Batch tonnes are required for scenario comparison")
        plant = self._maybe_plant(plant_id)
        if plant is None:
            return {
                "plantId": None,
                "batchTonnes": batch_tonnes,
                "rankedScenarios": [],
                "deltaAnalysis": None,
                "benchmarks": None,
            }

        runs = []
        for scenario in self._scenarios_for_plant(plant_id):
            metrics = self._calculate_metrics(
                scenario["plantId"],
                scenario["supplierId"],
                batch_tonnes,
                scenario,
            )
            runs.append(
                {
                    "scenarioId": scenario["scenarioId"],
                    "plantId": plant["id"],
                    "supplier": metrics["supplier"]["label"],
                    "supplierThingId": metrics["supplier"]["id"],
                    "distanceToPlantKm": round(metrics["distanceProfile"]["supplierToPlantKm"], 1),
                    "totalTco2": round(metrics["totals"]["total_tco2"], 4),
                    "scope1Tco2": round(metrics["totals"]["scope_1_tco2"], 4),
                    "scope2Tco2": round(metrics["totals"]["scope_2_tco2"], 4),
                    "scope3Tco2": round(metrics["totals"]["scope_3_tco2"], 4),
                    "intensityTco2PerTonne": round(
                        metrics["totals"]["total_tco2"] / batch_tonnes, 4
                    ),
                }
            )
        runs.sort(key=lambda item: item["totalTco2"])
        best = runs[0]
        worst = runs[-1]
        delta = worst["totalTco2"] - best["totalTco2"]
        return {
            "plantId": plant["id"],
            "plantLabel": plant["label"],
            "batchTonnes": batch_tonnes,
            "rankedScenarios": runs,
            "deltaAnalysis": {
                "bestScenario": best["scenarioId"],
                "worstScenario": worst["scenarioId"],
                "absoluteSavingsTco2": round(delta, 4),
                "relativeSavingsPct": round((delta / worst["totalTco2"]) * 100, 3),
                "narrative": (
                    f"{best['supplier']} is the lowest-carbon supplier for {plant['label']} in this model "
                    f"because its rail profile and mine-intensity assumptions outweigh the alternative corridors."
                ),
            },
            "benchmarks": {
                "modelIntensityTco2PerTonne": best["intensityTco2PerTonne"],
                "indiaCrudeSteelReferenceTco2PerTonne": 2.54,
                "worldsteelBfBofReferenceTco2PerTonne": 2.32,
            },
        }

    def get_system_state(self, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        active_run = self.store.get_run(correlation_id) if correlation_id else self.store.get_active_run()
        effective_correlation = None if active_run is None else active_run["correlation_id"]
        twins = self._resolve_world_state_things(effective_correlation)
        aggregated = {
            "scope_1_tco2": 0.0,
            "scope_2_tco2": 0.0,
            "scope_3_tco2": 0.0,
            "total_tco2": 0.0,
        }
        by_type = {"suppliers": [], "plant": None, "transportUnits": [], "port": None}
        for thing in twins:
            emission = thing["features"]["emission"]["properties"]["current"]
            aggregated["scope_1_tco2"] += emission.get("scope_1_tco2", 0.0)
            aggregated["scope_2_tco2"] += emission.get("scope_2_tco2", 0.0)
            aggregated["scope_3_tco2"] += emission.get("scope_3_tco2", 0.0)
            aggregated["total_tco2"] += emission.get("total_tco2", 0.0)

            entity_type = thing["metadata"]["entityType"]
            if entity_type == "supplier":
                by_type["suppliers"].append(thing)
            elif entity_type == "plant":
                by_type["plant"] = thing
            elif entity_type == "transport":
                by_type["transportUnits"].append(thing)
            elif entity_type == "port":
                by_type["port"] = thing

        recent_events = self.get_events(effective_correlation, limit=20)
        network = None if active_run is None else self._network_metadata_from_run(active_run)
        return {
            "worldState": {"things": twins, "byType": by_type},
            "aggregatedEmissions": {
                key: round(value, 4) for key, value in aggregated.items()
            },
            "activeCorrelation": effective_correlation,
            "currentStage": None if active_run is None else active_run["result"].get("currentStage"),
            "plantId": None if active_run is None else active_run["result"].get("plantId"),
            "ledgerBackend": self.ledger_backend.metadata(),
            "network": network,
            "recentEvents": recent_events,
        }

    def get_ledger(self, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        effective = correlation_id
        if effective is None:
            active = self.store.get_active_run()
            effective = None if active is None else active["correlation_id"]
        ledger = self.ledger_backend.get_ledger(effective)
        active = self.store.get_run(effective) if effective else self.store.get_active_run()
        if active is not None:
            ledger["plantId"] = active["result"].get("plantId")
            ledger["scenarioId"] = active["scenario_id"]
            ledger["network"] = self._network_metadata_from_run(active)
        return ledger

    def get_spatial_overlay(
        self,
        correlation_id: Optional[str] = None,
        plant_id: Optional[str] = None,
        supplier_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        # Do not implicitly load active_run if correlation_id is not provided
        active_run = self.store.get_run(correlation_id) if correlation_id else None
        
        if active_run is None:
            return self._build_preview_spatial_overlay(plant_id, supplier_ids)
        
        selected_plant_id = active_run["result"].get("plantId")
        system_state = self.get_system_state(correlation_id)
        things = system_state["worldState"]["things"]
        active_thing_ids = {thing["thingId"]: thing for thing in things}
        stage_state = self._stage_visibility(system_state["currentStage"])

        nodes: List[Dict[str, Any]] = []
        trucks: List[Dict[str, Any]] = []

        # Only show the selected plant (not all plants)
        if selected_plant_id and selected_plant_id in self.plants_by_id:
            plant = self.plants_by_id[selected_plant_id]
            live = active_thing_ids.get(plant["id"])
            if live:
                nodes.append(self._node_from_thing(live, True, muted=False))
            else:
                nodes.append(
                    {
                        "id": plant["id"],
                        "label": plant["label"],
                        "type": "plant",
                        "lat": plant["lat"],
                        "lon": plant["lon"],
                        "state": "selected",
                        "selected": True,
                        "muted": False,
                        "overview": False,
                        "totalTco2": 0.0,
                    }
                )

        # Always show JNPT port
        for port in self.ports_by_id.values():
            live = active_thing_ids.get(port["id"])
            if live:
                nodes.append(self._node_from_thing(live, False, muted=False))
            else:
                nodes.append(
                    {
                        "id": port["id"],
                        "label": port["label"],
                        "type": "port",
                        "lat": port["lat"],
                        "lon": port["lon"],
                        "state": "linked" if selected_plant_id else "standby",
                        "selected": False,
                        "muted": False,
                        "overview": True,
                        "totalTco2": 0.0,
                    }
                )

        for thing in things:
            entity_type = thing["metadata"]["entityType"]
            if entity_type == "supplier":
                nodes.append(self._node_from_thing(thing, thing["attributes"].get("selected", False), muted=False))
            elif entity_type == "transport":
                trucks.append(self._truck_from_thing(thing))

        edges: List[Dict[str, Any]] = []
        if active_run is not None:
            plant_id = active_run["result"]["plantId"]
            port_id = active_run["result"]["portId"]
            supplier_id = active_run["result"]["supplierThingId"]
            if stage_state["showSupplierPath"]:
                edges.append(
                    {
                        "id": f"{supplier_id}-{plant_id}",
                        "from": supplier_id,
                        "to": plant_id,
                        "kind": "material",
                        "label": "Supplier to plant",
                    }
                )
            if stage_state["showDispatchPaths"]:
                for truck in active_run["result"]["dispatchUnitIds"]:
                    edges.append(
                        {
                            "id": f"{plant_id}-{truck}",
                            "from": plant_id,
                            "to": truck,
                            "kind": "dispatch",
                            "label": "Dispatch assignment",
                        }
                    )
            if stage_state["showDeliveryPaths"]:
                for truck in active_run["result"]["dispatchUnitIds"]:
                    edges.append(
                        {
                            "id": f"{truck}-{port_id}",
                            "from": truck,
                            "to": port_id,
                            "kind": "delivery",
                            "label": "Dispatch to port",
                        }
                    )

        return {
            "correlationId": system_state["activeCorrelation"],
            "plantId": selected_plant_id,
            "ledgerBackend": self.ledger_backend.metadata(),
            "viewerMode": self.framework_alignment()["viewerMode"],
            "nodes": nodes,
            "trucks": trucks if stage_state["showTransportUnits"] else [],
            "edges": edges,
            "activeStage": system_state["currentStage"] or "Plant overview",
            "network": self._network_metadata_from_run(active_run),
        }

    def _build_preview_spatial_overlay(
        self,
        plant_id: Optional[str],
        supplier_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Step-by-step overlay logic:
        - No plant → only JNPT port visible
        - Plant selected → plant + JNPT, no suppliers, no edges
        - Suppliers selected → plant + JNPT + selected suppliers, no edges
        """
        selected_plant = self._maybe_plant(plant_id)
        selected_port = None if selected_plant is None else self._port_profile(selected_plant["port_id"])
        effective_supplier_ids = set(supplier_ids or [])

        nodes: List[Dict[str, Any]] = []

        # Only show the selected plant, not all plants
        if selected_plant is not None:
            nodes.append(
                {
                    "id": selected_plant["id"],
                    "label": selected_plant["label"],
                    "type": "plant",
                    "lat": selected_plant["lat"],
                    "lon": selected_plant["lon"],
                    "state": "selected",
                    "selected": True,
                    "muted": False,
                    "overview": False,
                    "totalTco2": 0.0,
                }
            )

        # Always show the port (JNPT)
        for port in self.ports_by_id.values():
            nodes.append(
                {
                    "id": port["id"],
                    "label": port["label"],
                    "type": "port",
                    "lat": port["lat"],
                    "lon": port["lon"],
                    "state": "linked" if selected_port and selected_port["id"] == port["id"] else "standby",
                    "selected": False,
                    "muted": False,
                    "overview": True,
                    "totalTco2": 0.0,
                }
            )

        # Only add selected suppliers (not all), and never add edges in preview
        edges: List[Dict[str, Any]] = []
        shown_supplier_ids: List[str] = []
        if selected_plant is not None and effective_supplier_ids:
            for scenario in self._scenarios_for_plant(selected_plant["id"]):
                supplier = self._supplier_profile(scenario["supplierId"])
                if supplier["id"] in effective_supplier_ids:
                    shown_supplier_ids.append(supplier["id"])
                    nodes.append(
                        {
                            "id": supplier["id"],
                            "label": supplier["label"],
                            "type": "supplier",
                            "lat": supplier["lat"],
                            "lon": supplier["lon"],
                            "state": "candidate",
                            "selected": True,
                            "muted": False,
                            "overview": False,
                            "totalTco2": 0.0,
                        }
                    )

        return {
            "correlationId": None,
            "plantId": plant_id,
            "ledgerBackend": self.ledger_backend.metadata(),
            "viewerMode": self.framework_alignment()["viewerMode"],
            "nodes": nodes,
            "trucks": [],
            "edges": edges,
            "activeStage": "Suppliers selected" if shown_supplier_ids else ("Plant selected" if selected_plant is not None else "Initial"),
            "network": {
                "plantId": None if selected_plant is None else selected_plant["id"],
                "plantLabel": None if selected_plant is None else selected_plant["label"],
                "portId": None if selected_port is None else selected_port["id"],
                "portLabel": None if selected_port is None else selected_port["label"],
                "supplierThingIds": shown_supplier_ids,
            },
        }

    def _network_metadata_from_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        plant_id = run["result"]["plantId"]
        port_id = run["result"]["portId"]
        supplier_id = run["result"]["supplierThingId"]
        return {
            "plantId": plant_id,
            "plantLabel": self._plant_profile(plant_id)["label"],
            "portId": port_id,
            "portLabel": self._port_profile(port_id)["label"],
            "supplierThingId": supplier_id,
            "supplierLabel": self._supplier_profile(supplier_id)["label"],
            "scenarioId": run["scenario_id"],
        }

    def _bootstrap_run(
        self,
        correlation_id: str,
        scenario: Dict[str, Any],
        batch_tonnes: float,
    ) -> Dict[str, Any]:
        timestamp = now_ist()
        metrics = self._calculate_metrics(
            scenario["plantId"],
            scenario["supplierId"],
            batch_tonnes,
            scenario,
        )
        twins = self._seed_world_state(correlation_id, metrics, batch_tonnes)
        result = {
            "correlationId": correlation_id,
            "plantId": scenario["plantId"],
            "scenarioId": scenario["scenarioId"],
            "supplierThingId": scenario["supplierId"],
            "portId": metrics["port"]["id"],
            "batchTonnes": batch_tonnes,
            "stepIndex": 0,
            "currentStage": "initialized",
            "lastAppliedAction": None,
            "metrics": metrics,
            "dispatchUnitIds": metrics["dispatch"]["unitIds"],
            "thingIds": [thing["thingId"] for thing in twins],
        }
        self.store.upsert_scenario_run(
            correlation_id=correlation_id,
            scenario_id=scenario["scenarioId"],
            supplier_thing_id=scenario["supplierId"],
            batch_tonnes=batch_tonnes,
            status="running",
            result=result,
            timestamp=timestamp,
            is_active=True,
        )
        return self.store.get_run(correlation_id)  # type: ignore[return-value]

    def _advance_run(
        self,
        run: Dict[str, Any],
        action: str,
        supplier_thing_id: Optional[str],
        truck_ids: List[str],
    ) -> Dict[str, Any]:
        step_index = run["result"]["stepIndex"]
        if step_index >= len(self.STAGE_SEQUENCE):
            raise InvalidTransitionError("Scenario already completed")
        expected_action = self.STAGE_SEQUENCE[step_index]
        if action not in {"next", expected_action}:
            raise InvalidTransitionError(
                f"Expected '{expected_action}' but received '{action}'"
            )

        if expected_action.startswith("supplier.") and supplier_thing_id and supplier_thing_id != run["result"]["supplierThingId"]:
            raise InvalidTransitionError("Cannot switch suppliers mid-run")

        self._apply_step(
            correlation_id=run["correlation_id"],
            action=expected_action,
            metrics=run["result"]["metrics"],
            truck_ids=truck_ids,
        )
        new_step_index = step_index + 1
        run["result"]["stepIndex"] = new_step_index
        run["result"]["currentStage"] = expected_action
        run["result"]["lastAppliedAction"] = expected_action
        run["status"] = "completed" if new_step_index == len(self.STAGE_SEQUENCE) else "running"

        self.store.upsert_scenario_run(
            correlation_id=run["correlation_id"],
            scenario_id=run["scenario_id"],
            supplier_thing_id=run["supplier_thing_id"],
            batch_tonnes=run["batch_tonnes"],
            status=run["status"],
            result=run["result"],
            timestamp=now_ist(),
            is_active=True,
        )
        return self.store.get_run(run["correlation_id"])  # type: ignore[return-value]

    def _build_run_result(
        self,
        correlation_id: str,
        scenario: Dict[str, Any],
        batch_tonnes: float,
        run_status: str = "completed",
        current_stage: Optional[str] = None,
        last_applied_action: Optional[str] = None,
        step_index: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
        dispatch_unit_ids: Optional[List[str]] = None,
        thing_ids: Optional[List[str]] = None,
        port_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        system_state = self.get_system_state(correlation_id)
        result = {
            "correlationId": correlation_id,
            "plantId": scenario["plantId"],
            "scenarioId": scenario["scenarioId"],
            "supplierThingId": scenario["supplierId"],
            "batchTonnes": batch_tonnes,
            "completed": run_status == "completed",
            "currentStage": current_stage or system_state["currentStage"],
            "lastAppliedAction": last_applied_action,
            "systemState": system_state,
            "ledger": self.get_ledger(correlation_id),
            "events": self.get_events(correlation_id),
            "spatialOverlay": self.get_spatial_overlay(correlation_id),
            "ledgerBackend": self.ledger_backend.metadata(),
        }
        if step_index is not None:
            result["stepIndex"] = step_index
        if metrics is not None:
            result["metrics"] = metrics
        if dispatch_unit_ids is not None:
            result["dispatchUnitIds"] = dispatch_unit_ids
        if thing_ids is not None:
            result["thingIds"] = thing_ids
        if port_id is not None:
            result["portId"] = port_id
        return result

    def _apply_step(
        self,
        correlation_id: str,
        action: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        handlers = {
            "supplier.selected": self._handle_supplier_selected,
            "supplier.dispatched": self._handle_supplier_dispatched,
            "plant.received_material": self._handle_plant_received,
            "plant.production_completed": self._handle_plant_completed,
            "transport.assigned": self._handle_transport_assigned,
            "transport.departed": self._handle_transport_departed,
            "transport.arrived_port": self._handle_transport_arrived,
            "transport.unloaded": self._handle_transport_unloaded,
            "port.received": self._handle_port_received,
            "port.customs_cleared": self._handle_port_cleared,
            "port.delivered": self._handle_port_delivered,
        }
        return handlers[action](correlation_id, metrics, truck_ids)

    def _handle_supplier_selected(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        del truck_ids
        timestamp = now_ist()
        plant = metrics["plant"]
        selected_supplier_id = metrics["supplier"]["id"]
        selected_name = metrics["supplier"]["label"]

        for scenario in self._scenarios_for_plant(plant["id"]):
            supplier = self.get_twin(scenario["supplierId"])
            is_selected = supplier["thingId"] == selected_supplier_id
            supplier["attributes"]["selected"] = is_selected
            if is_selected:
                self._set_lifecycle(supplier, "allocated", timestamp)
                supplier["features"]["materialFlow"]["properties"]["current"] = {
                    "material": "iron_ore_fines",
                    "batchTonnes": round(metrics["materialFlow"]["ore_tonnes"], 3),
                    "destination": plant["id"],
                }
                supplier["features"]["materialFlow"]["metadata"]["lastUpdated"] = timestamp
            self.store.upsert_twin(
                supplier,
                entity_type="supplier",
                updated_at=timestamp,
                correlation_id=correlation_id,
            )

        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            selected_supplier_id,
            "supplier.selected",
            "Supplier Planning",
            "raw",
            "allocated",
            {
                "selectedSupplier": selected_name,
                "plantId": plant["id"],
                "batchTonnes": metrics["materialFlow"]["batch_tonnes_hrc"],
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        self._record_block(
            correlation_id=correlation_id,
            stage="Planning",
            thing_id=selected_supplier_id,
            plant_id=plant["id"],
            supplier_id=selected_supplier_id,
            emission=0.0,
            payload={
                "eventType": "supplier.selected",
                "selectedSupplier": selected_name,
                "recordType": "StageEvent",
            },
            timestamp=timestamp,
            world_state_snapshot=snapshot,
        )
        return [event]

    def _handle_supplier_dispatched(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        del truck_ids
        timestamp = now_ist()
        supplier = self.get_twin(metrics["supplier"]["id"])
        self._set_lifecycle(supplier, "dispatched", timestamp)
        supplier["features"]["emission"]["properties"]["current"] = deepcopy(metrics["supplierEmission"])
        supplier["features"]["emission"]["properties"]["reported"] = deepcopy(metrics["supplierEmission"])
        supplier["features"]["materialFlow"]["properties"]["current"] = {
            "material": "iron_ore_fines",
            "batchTonnes": round(metrics["materialFlow"]["ore_tonnes"], 3),
            "destination": metrics["plant"]["id"],
            "modeToPlant": metrics["distanceProfile"]["supplierMode"],
            "distanceKm": round(metrics["distanceProfile"]["supplierToPlantKm"], 1),
        }
        supplier["features"]["materialFlow"]["metadata"]["lastUpdated"] = timestamp
        self.store.upsert_twin(
            supplier,
            entity_type="supplier",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )

        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            supplier["thingId"],
            "supplier.dispatched",
            "Supplier Dispatch",
            "allocated",
            "dispatched",
            {
                "plantId": metrics["plant"]["id"],
                "emission": metrics["supplierEmission"],
                "distanceProfile": metrics["distanceProfile"],
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        self._record_block(
            correlation_id=correlation_id,
            stage="Supplier",
            thing_id=supplier["thingId"],
            plant_id=metrics["plant"]["id"],
            supplier_id=supplier["thingId"],
            emission=metrics["supplierEmission"]["total_tco2"],
            payload={
                "eventType": "supplier.dispatched",
                "emission": metrics["supplierEmission"],
            },
            timestamp=timestamp,
            world_state_snapshot=snapshot,
        )
        return [event]

    def _handle_plant_received(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        del truck_ids
        timestamp = now_ist()
        plant = self.get_twin(metrics["plant"]["id"])
        self._set_lifecycle(plant, "processing", timestamp)
        plant["features"]["materialFlow"]["properties"]["current"] = {
            "inputMaterial": "iron_ore_fines",
            "inputTonnes": round(metrics["materialFlow"]["ore_tonnes"], 3),
            "supplierThingId": metrics["supplier"]["id"],
            "batchTonnes": round(metrics["materialFlow"]["batch_tonnes_hrc"], 3),
        }
        plant["features"]["materialFlow"]["metadata"]["lastUpdated"] = timestamp
        self.store.upsert_twin(
            plant,
            entity_type="plant",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )

        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            plant["thingId"],
            "plant.received_material",
            "Plant Receipt",
            "idle",
            "processing",
            {
                "supplierThingId": metrics["supplier"]["id"],
                "inputTonnes": metrics["materialFlow"]["ore_tonnes"],
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        return [event]

    def _handle_plant_completed(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        del truck_ids
        timestamp = now_ist()
        plant = self.get_twin(metrics["plant"]["id"])
        self._set_lifecycle(plant, "packed", timestamp)
        plant["features"]["emission"]["properties"]["current"] = deepcopy(metrics["plantEmission"])
        plant["features"]["emission"]["properties"]["reported"] = deepcopy(metrics["plantEmission"])
        plant["features"]["materialFlow"]["properties"]["current"] = {
            "inputTonnes": round(metrics["materialFlow"]["ore_tonnes"], 3),
            "pelletTonnes": round(metrics["materialFlow"]["pellets_tonnes"], 3),
            "outputMaterial": self.data["project"]["product"],
            "outputTonnes": round(metrics["materialFlow"]["batch_tonnes_hrc"], 3),
        }
        plant["features"]["materialFlow"]["metadata"]["lastUpdated"] = timestamp
        self.store.upsert_twin(
            plant,
            entity_type="plant",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )

        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            plant["thingId"],
            "plant.production_completed",
            "Plant Production",
            "processing",
            "packed",
            {
                "emission": metrics["plantEmission"],
                "outputTonnes": metrics["materialFlow"]["batch_tonnes_hrc"],
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        self._record_block(
            correlation_id=correlation_id,
            stage="Plant",
            thing_id=plant["thingId"],
            plant_id=metrics["plant"]["id"],
            supplier_id=metrics["supplier"]["id"],
            emission=metrics["plantEmission"]["total_tco2"],
            payload={
                "eventType": "plant.production_completed",
                "emission": metrics["plantEmission"],
            },
            timestamp=timestamp,
            world_state_snapshot=snapshot,
        )
        return [event]

    def _handle_transport_assigned(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        timestamp = now_ist()
        events = []
        plant = self.get_twin(metrics["plant"]["id"])
        self._set_lifecycle(plant, "handed_to_transport", timestamp)
        self.store.upsert_twin(
            plant,
            entity_type="plant",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )

        for index, truck_id in enumerate(truck_ids):
            truck = self.get_twin(truck_id)
            self._set_lifecycle(truck, "assigned", timestamp)
            truck["features"]["location"]["properties"]["current"] = self._interpolate_location(
                metrics["plant"],
                metrics["port"],
                0.0,
                self._transport_lateral_offset(index, len(truck_ids)),
            )
            truck["features"]["materialFlow"]["properties"]["current"] = {
                "material": self.data["project"]["product"],
                "batchTonnes": metrics["transportEmission"]["perUnitTonnes"],
                "destination": metrics["port"]["id"],
            }
            self.store.upsert_twin(
                truck,
                entity_type="transport",
                updated_at=timestamp,
                correlation_id=correlation_id,
            )
            snapshot = self.get_system_state(correlation_id)["worldState"]
            events.append(
                self._record_event(
                    correlation_id,
                    truck_id,
                    "transport.assigned",
                    "Dispatch Assignment",
                    "created",
                    "assigned",
                    {
                        "portThingId": metrics["port"]["id"],
                        "worldStateSnapshot": snapshot,
                    },
                    timestamp,
                )
            )
        return events

    def _handle_transport_departed(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        timestamp = now_ist()
        events = []
        for index, truck_id in enumerate(truck_ids):
            truck = self.get_twin(truck_id)
            self._set_lifecycle(truck, "in_transit", timestamp)
            truck["features"]["location"]["properties"]["current"] = self._interpolate_location(
                metrics["plant"],
                metrics["port"],
                0.58,
                self._transport_lateral_offset(index, len(truck_ids)) * 0.65,
            )
            truck["features"]["emission"]["properties"]["current"] = deepcopy(
                metrics["transportEmission"]["perUnitEmission"]
            )
            truck["features"]["emission"]["properties"]["reported"] = deepcopy(
                metrics["transportEmission"]["perUnitEmission"]
            )
            self.store.upsert_twin(
                truck,
                entity_type="transport",
                updated_at=timestamp,
                correlation_id=correlation_id,
            )
            snapshot = self.get_system_state(correlation_id)["worldState"]
            events.append(
                self._record_event(
                    correlation_id,
                    truck_id,
                    "transport.departed",
                    "Dispatch Departure",
                    "assigned",
                    "in_transit",
                    {
                        "distanceKm": metrics["distanceProfile"]["plantToPortKm"],
                        "worldStateSnapshot": snapshot,
                    },
                    timestamp,
                )
            )
        return events

    def _handle_transport_arrived(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        timestamp = now_ist()
        events = []
        for index, truck_id in enumerate(truck_ids):
            truck = self.get_twin(truck_id)
            self._set_lifecycle(truck, "at_port", timestamp)
            truck["features"]["location"]["properties"]["current"] = self._interpolate_location(
                metrics["plant"],
                metrics["port"],
                1.0,
                self._transport_lateral_offset(index, len(truck_ids)) * 0.42,
            )
            self.store.upsert_twin(
                truck,
                entity_type="transport",
                updated_at=timestamp,
                correlation_id=correlation_id,
            )
            snapshot = self.get_system_state(correlation_id)["worldState"]
            events.append(
                self._record_event(
                    correlation_id,
                    truck_id,
                    "transport.arrived_port",
                    "Transport Arrival",
                    "in_transit",
                    "at_port",
                    {
                        "portThingId": metrics["port"]["id"],
                        "worldStateSnapshot": snapshot,
                    },
                    timestamp,
                )
            )
        return events

    def _handle_transport_unloaded(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        timestamp = now_ist()
        events = []
        last_snapshot = None
        for truck_id in truck_ids:
            truck = self.get_twin(truck_id)
            self._set_lifecycle(truck, "unloaded", timestamp)
            self.store.upsert_twin(
                truck,
                entity_type="transport",
                updated_at=timestamp,
                correlation_id=correlation_id,
            )
            last_snapshot = self.get_system_state(correlation_id)["worldState"]
            events.append(
                self._record_event(
                    correlation_id,
                    truck_id,
                    "transport.unloaded",
                    "Transport Unload",
                    "at_port",
                    "unloaded",
                    {
                        "upstreamSupplierLogisticsTco2": metrics["transportEmission"]["upstreamInboundTco2"],
                        "worldStateSnapshot": last_snapshot,
                    },
                    timestamp,
                )
            )
        self._record_block(
            correlation_id=correlation_id,
            stage="Transport",
            thing_id=truck_ids[0],
            plant_id=metrics["plant"]["id"],
            supplier_id=metrics["supplier"]["id"],
            emission=metrics["transportEmission"]["total_tco2"],
            payload={
                "eventType": "transport.unloaded",
                "emission": metrics["transportEmission"],
            },
            timestamp=timestamp,
            world_state_snapshot=last_snapshot or {},
        )
        return events

    def _handle_port_received(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        timestamp = now_ist()
        port = self.get_twin(metrics["port"]["id"])
        self._set_lifecycle(port, "received", timestamp)
        port["features"]["materialFlow"]["properties"]["current"] = {
            "material": self.data["project"]["product"],
            "batchTonnes": round(metrics["materialFlow"]["batch_tonnes_hrc"], 3),
            "receivedFrom": truck_ids,
        }
        self.store.upsert_twin(
            port,
            entity_type="port",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )
        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            port["thingId"],
            "port.received",
            "Port Receipt",
            "queued",
            "received",
            {
                "receivedTonnes": metrics["materialFlow"]["batch_tonnes_hrc"],
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        return [event]

    def _handle_port_cleared(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        del truck_ids
        timestamp = now_ist()
        port = self.get_twin(metrics["port"]["id"])
        self._set_lifecycle(port, "customs_cleared", timestamp)
        self.store.upsert_twin(
            port,
            entity_type="port",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )
        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            port["thingId"],
            "port.customs_cleared",
            "Port Customs",
            "received",
            "customs_cleared",
            {
                "clearanceStatus": "approved",
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        return [event]

    def _handle_port_delivered(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        truck_ids: List[str],
    ) -> List[Dict[str, Any]]:
        del truck_ids
        timestamp = now_ist()
        port = self.get_twin(metrics["port"]["id"])
        self._set_lifecycle(port, "delivered", timestamp)
        port["features"]["emission"]["properties"]["current"] = deepcopy(metrics["portEmission"])
        port["features"]["emission"]["properties"]["reported"] = deepcopy(metrics["portEmission"])
        self.store.upsert_twin(
            port,
            entity_type="port",
            updated_at=timestamp,
            correlation_id=correlation_id,
        )
        snapshot = self.get_system_state(correlation_id)["worldState"]
        event = self._record_event(
            correlation_id,
            port["thingId"],
            "port.delivered",
            "Port Delivery",
            "customs_cleared",
            "delivered",
            {
                "emission": metrics["portEmission"],
                "worldStateSnapshot": snapshot,
            },
            timestamp,
        )
        self._record_block(
            correlation_id=correlation_id,
            stage="Port",
            thing_id=port["thingId"],
            plant_id=metrics["plant"]["id"],
            supplier_id=metrics["supplier"]["id"],
            emission=metrics["portEmission"]["total_tco2"],
            payload={
                "eventType": "port.delivered",
                "emission": metrics["portEmission"],
            },
            timestamp=timestamp,
            world_state_snapshot=snapshot,
        )
        return [event]

    def _record_event(
        self,
        correlation_id: str,
        thing_id: str,
        event_type: str,
        stage: str,
        from_state: str,
        to_state: str,
        payload: Dict[str, Any],
        timestamp: str,
    ) -> Dict[str, Any]:
        event = {
            "eventId": f"evt-{uuid.uuid4().hex[:12]}",
            "thingId": thing_id,
            "correlationId": correlation_id,
            "eventType": event_type,
            "stage": stage,
            "fromState": from_state,
            "toState": to_state,
            "timestamp": timestamp,
            "payload": payload,
        }
        self.store.record_event(event)
        return event

    def _record_block(
        self,
        *,
        correlation_id: str,
        stage: str,
        thing_id: str,
        plant_id: str,
        supplier_id: str,
        emission: float,
        payload: Dict[str, Any],
        timestamp: str,
        world_state_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.ledger_backend.record_stage(
            correlation_id=correlation_id,
            plant_id=plant_id,
            supplier_id=supplier_id,
            stage=stage,
            thing_id=thing_id,
            emission=emission,
            payload=payload,
            timestamp=timestamp,
            world_state_snapshot=world_state_snapshot,
        )

    def _calculate_metrics(
        self,
        plant_id: str,
        supplier_id: str,
        batch_tonnes: float,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scenario = scenario or self._resolve_scenario(plant_id, None, supplier_id)
        plant = self._plant_profile(plant_id)
        supplier = self._supplier_profile(supplier_id)
        port = self._port_profile(plant["port_id"])
        factors = self.data["factors"]

        ore_tonnes = batch_tonnes * supplier["ore_requirement_t_per_t_hrc"]
        pellets_tonnes = batch_tonnes * plant["pellets_t_per_t_hrc"]
        supplier_to_plant_km = self._distance_km(
            supplier["lat"],
            supplier["lon"],
            plant["lat"],
            plant["lon"],
            scenario["distanceMultiplier"],
        )
        plant_to_port_km = self._distance_km(
            plant["lat"],
            plant["lon"],
            port["lat"],
            port["lon"],
            plant["outbound_distance_multiplier"],
        )

        supplier_scope3 = ore_tonnes * (
            supplier["diesel_l_per_t_ore"] * factors["diesel_tco2_per_litre"]
            + (supplier["electricity_kwh_per_t_ore"] / 1000.0) * factors["grid_tco2_per_mwh"]
        )
        plant_scope1 = (
            pellets_tonnes * plant["pellet_thermal_gj_per_t_pellet"] * factors["solid_fuel_tco2_per_gj"]
            + batch_tonnes
            * (
                plant["ironmaking_and_steelmaking_gj_per_t_hrc"] * factors["solid_fuel_tco2_per_gj"]
                + plant["hot_rolling_gj_per_t_hrc"] * factors["reheat_fuel_tco2_per_gj"]
            )
        )
        plant_scope2 = (
            pellets_tonnes * plant["pellet_electricity_mwh_per_t_pellet"] * factors["grid_tco2_per_mwh"]
            + batch_tonnes * plant["electricity_mwh_per_t_hrc"] * factors["grid_tco2_per_mwh"]
        )
        inbound_supplier_logistics = ore_tonnes * supplier_to_plant_km * factors[
            f"{scenario['modeToPlant']}_tco2_per_tkm"
        ]
        outbound_dispatch = batch_tonnes * plant_to_port_km * factors[
            f"{plant['outbound_mode']}_tco2_per_tkm"
        ]
        port_scope2 = batch_tonnes * port["port_handling_mwh_per_t_hrc"] * factors["grid_tco2_per_mwh"]

        dispatch_unit_count = int(plant["dispatch_unit_count"])
        dispatch_unit_ids = self._dispatch_unit_ids(plant_id, dispatch_unit_count)
        per_unit_emission = outbound_dispatch / dispatch_unit_count
        per_unit_tonnes = batch_tonnes / dispatch_unit_count

        return {
            "scenario": deepcopy(scenario),
            "plant": deepcopy(plant),
            "supplier": deepcopy(supplier),
            "port": deepcopy(port),
            "supplierEmission": {
                "scope_1_tco2": 0.0,
                "scope_2_tco2": 0.0,
                "scope_3_tco2": round(supplier_scope3, 4),
                "total_tco2": round(supplier_scope3, 4),
            },
            "plantEmission": {
                "scope_1_tco2": round(plant_scope1, 4),
                "scope_2_tco2": round(plant_scope2, 4),
                "scope_3_tco2": 0.0,
                "total_tco2": round(plant_scope1 + plant_scope2, 4),
            },
            "transportEmission": {
                "scope_1_tco2": round(inbound_supplier_logistics + outbound_dispatch, 4),
                "scope_2_tco2": 0.0,
                "scope_3_tco2": 0.0,
                "total_tco2": round(inbound_supplier_logistics + outbound_dispatch, 4),
                "upstreamInboundTco2": round(inbound_supplier_logistics, 4),
                "outboundDispatchTco2": round(outbound_dispatch, 4),
                "perUnitEmission": {
                    "scope_1_tco2": round(per_unit_emission, 4),
                    "scope_2_tco2": 0.0,
                    "scope_3_tco2": 0.0,
                    "total_tco2": round(per_unit_emission, 4),
                },
                "perUnitTonnes": round(per_unit_tonnes, 3),
            },
            "portEmission": {
                "scope_1_tco2": 0.0,
                "scope_2_tco2": round(port_scope2, 4),
                "scope_3_tco2": 0.0,
                "total_tco2": round(port_scope2, 4),
            },
            "totals": {
                "scope_1_tco2": round(plant_scope1 + inbound_supplier_logistics + outbound_dispatch, 4),
                "scope_2_tco2": round(plant_scope2 + port_scope2, 4),
                "scope_3_tco2": round(supplier_scope3, 4),
                "total_tco2": round(
                    supplier_scope3
                    + plant_scope1
                    + plant_scope2
                    + inbound_supplier_logistics
                    + outbound_dispatch
                    + port_scope2,
                    4,
                ),
            },
            "materialFlow": {
                "batch_tonnes_hrc": batch_tonnes,
                "ore_tonnes": round(ore_tonnes, 3),
                "pellets_tonnes": round(pellets_tonnes, 3),
            },
            "distanceProfile": {
                "supplierToPlantKm": round(supplier_to_plant_km, 1),
                "plantToPortKm": round(plant_to_port_km, 1),
                "supplierMode": scenario["modeToPlant"],
                "portMode": plant["outbound_mode"],
            },
            "dispatch": {
                "unitIds": dispatch_unit_ids,
                "operator": plant["dispatch_operator"],
            },
        }

    def _build_supplier_thing(
        self,
        profile: Dict[str, Any],
        scenario: Dict[str, Any],
        correlation_id: str,
        selected: bool,
    ) -> Dict[str, Any]:
        timestamp = now_ist()
        return {
            "thingId": profile["id"],
            "definition": self.SUPPLIER_DEFINITION,
            "policyId": self.POLICY_ID,
            "revision": 0,
            "attributes": {
                "name": profile["label"],
                "operator": profile["operator"],
                "state": profile["state"],
                "district": profile["district"],
                "selected": selected,
                "scenarioId": scenario["scenarioId"],
                "supplyRole": "iron_ore_supplier",
                "coordinateQuality": profile["coordinate_quality"],
                "inferenceNote": profile["inference_note"],
            },
            "features": {
                "location": self._feature(
                    current={"lat": profile["lat"], "lon": profile["lon"]},
                    unit="geo",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "materialFlow": self._feature(
                    current={"material": "iron_ore_fines", "batchTonnes": 0.0},
                    unit="tonnes",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "emission": self._feature(
                    current={"scope_1_tco2": 0.0, "scope_2_tco2": 0.0, "scope_3_tco2": 0.0, "total_tco2": 0.0},
                    unit="tCO2",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "lifecycle": self._feature(
                    current={"state": "raw", "allowed": self.SUPPLIER_FLOW},
                    unit="state",
                    source="transition-engine",
                    updated_at=timestamp,
                ),
            },
            "metadata": {
                "entityType": "supplier",
                "correlationId": correlation_id,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            },
        }

    def _build_plant_thing(
        self,
        plant: Dict[str, Any],
        correlation_id: str,
        batch_tonnes: float,
    ) -> Dict[str, Any]:
        timestamp = now_ist()
        return {
            "thingId": plant["id"],
            "definition": self.PLANT_DEFINITION,
            "policyId": self.POLICY_ID,
            "revision": 0,
            "attributes": {
                "name": plant["label"],
                "operator": plant["operator"],
                "state": plant["state"],
                "district": plant["district"],
                "processRoute": "Integrated BF-BOF + HSM",
                "portId": plant["port_id"],
                "coordinateQuality": plant["coordinate_quality"],
            },
            "features": {
                "location": self._feature(
                    current={"lat": plant["lat"], "lon": plant["lon"]},
                    unit="geo",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "materialFlow": self._feature(
                    current={"inputTonnes": 0.0, "outputTonnes": 0.0, "batchTonnes": batch_tonnes},
                    unit="tonnes",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "emission": self._feature(
                    current={"scope_1_tco2": 0.0, "scope_2_tco2": 0.0, "scope_3_tco2": 0.0, "total_tco2": 0.0},
                    unit="tCO2",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "lifecycle": self._feature(
                    current={"state": "idle", "allowed": self.PLANT_FLOW},
                    unit="state",
                    source="transition-engine",
                    updated_at=timestamp,
                ),
            },
            "metadata": {
                "entityType": "plant",
                "correlationId": correlation_id,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            },
        }

    def _build_transport_thing(
        self,
        plant: Dict[str, Any],
        port: Dict[str, Any],
        thing_id: str,
        correlation_id: str,
        load_tonnes: float,
        index: int,
        total_units: int,
    ) -> Dict[str, Any]:
        timestamp = now_ist()
        location = self._interpolate_location(
            plant,
            port,
            0.0,
            self._transport_lateral_offset(index, total_units),
        )
        mode = plant["outbound_mode"]
        return {
            "thingId": thing_id,
            "definition": self.TRANSPORT_DEFINITION,
            "policyId": self.POLICY_ID,
            "revision": 0,
            "attributes": {
                "name": f"{self._short_label(plant['label'])} Dispatch {index + 1}",
                "operator": plant["dispatch_operator"],
                "state": plant["state"],
                "vehicleKind": "rail_rake" if mode == "rail" else "heavy_truck",
                "mode": mode,
            },
            "features": {
                "location": self._feature(
                    current=location,
                    unit="geo",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "materialFlow": self._feature(
                    current={"material": self.data["project"]["product"], "batchTonnes": round(load_tonnes, 3)},
                    unit="tonnes",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "emission": self._feature(
                    current={"scope_1_tco2": 0.0, "scope_2_tco2": 0.0, "scope_3_tco2": 0.0, "total_tco2": 0.0},
                    unit="tCO2",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "lifecycle": self._feature(
                    current={"state": "created", "allowed": self.TRANSPORT_FLOW},
                    unit="state",
                    source="transition-engine",
                    updated_at=timestamp,
                ),
            },
            "metadata": {
                "entityType": "transport",
                "correlationId": correlation_id,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            },
        }

    def _build_port_thing(self, port: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
        timestamp = now_ist()
        return {
            "thingId": port["id"],
            "definition": self.PORT_DEFINITION,
            "policyId": self.POLICY_ID,
            "revision": 0,
            "attributes": {
                "name": port["label"],
                "operator": port["operator"],
                "state": port["state"],
                "terminalReference": port["terminal_reference"],
                "coordinateQuality": port["coordinate_quality"],
            },
            "features": {
                "location": self._feature(
                    current={"lat": port["lat"], "lon": port["lon"]},
                    unit="geo",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "materialFlow": self._feature(
                    current={"material": self.data["project"]["product"], "batchTonnes": 0.0},
                    unit="tonnes",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "emission": self._feature(
                    current={"scope_1_tco2": 0.0, "scope_2_tco2": 0.0, "scope_3_tco2": 0.0, "total_tco2": 0.0},
                    unit="tCO2",
                    source="bootstrap",
                    updated_at=timestamp,
                ),
                "lifecycle": self._feature(
                    current={"state": "queued", "allowed": self.PORT_FLOW},
                    unit="state",
                    source="transition-engine",
                    updated_at=timestamp,
                ),
            },
            "metadata": {
                "entityType": "port",
                "correlationId": correlation_id,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            },
        }

    def _seed_world_state(
        self,
        correlation_id: str,
        metrics: Dict[str, Any],
        batch_tonnes: float,
    ) -> List[Dict[str, Any]]:
        plant_id = metrics["plant"]["id"]
        selected_supplier_id = metrics["supplier"]["id"]
        selected_scenario_id = metrics["scenario"]["scenarioId"]

        suppliers = []
        for scenario in self._scenarios_for_plant(plant_id):
            supplier = self._supplier_profile(scenario["supplierId"])
            suppliers.append(
                self._build_supplier_thing(
                    supplier,
                    scenario,
                    correlation_id,
                    selected=scenario["supplierId"] == selected_supplier_id,
                )
            )
        plant = self._build_plant_thing(metrics["plant"], correlation_id, batch_tonnes)
        transport_units = [
            self._build_transport_thing(
                metrics["plant"],
                metrics["port"],
                thing_id,
                correlation_id,
                batch_tonnes / len(metrics["dispatch"]["unitIds"]),
                index,
                len(metrics["dispatch"]["unitIds"]),
            )
            for index, thing_id in enumerate(metrics["dispatch"]["unitIds"])
        ]
        port = self._build_port_thing(metrics["port"], correlation_id)
        seeded = suppliers + [plant] + transport_units + [port]
        for thing in seeded:
            thing["attributes"]["scenarioId"] = selected_scenario_id
            self.store.upsert_twin(
                thing,
                entity_type=thing["metadata"]["entityType"],
                updated_at=thing["metadata"]["updatedAt"],
                correlation_id=correlation_id,
            )
        return seeded

    def _normalize_thing(
        self,
        payload: Dict[str, Any],
        entity_type: str,
        correlation_id: Optional[str],
    ) -> Dict[str, Any]:
        timestamp = now_ist()
        normalized = deepcopy(payload)
        if not normalized.get("policyId"):
            normalized["policyId"] = self.POLICY_ID
        if normalized.get("revision") is None:
            normalized["revision"] = 0
        if normalized.get("attributes") is None:
            normalized["attributes"] = {}
        if normalized.get("features") is None:
            normalized["features"] = {}
        if normalized.get("metadata") is None:
            normalized["metadata"] = {
                "entityType": entity_type,
                "correlationId": correlation_id,
                "createdAt": timestamp,
            }
        normalized["metadata"]["entityType"] = entity_type
        normalized["metadata"]["correlationId"] = correlation_id
        normalized["metadata"]["createdAt"] = normalized["metadata"].get("createdAt", timestamp)
        normalized["metadata"]["updatedAt"] = timestamp
        for feature_name, feature in normalized["features"].items():
            properties = feature.get("properties", {})
            feature["properties"] = {
                "desired": deepcopy(properties.get("desired", properties.get("current", {}))),
                "reported": deepcopy(properties.get("reported", properties.get("current", {}))),
                "current": deepcopy(
                    properties.get(
                        "current",
                        properties.get("reported", properties.get("desired", {})),
                    )
                ),
            }
            feature["metadata"] = deep_merge(
                {
                    "lastUpdated": timestamp,
                    "source": "api",
                    "unit": feature.get("metadata", {}).get("unit", ""),
                },
                feature.get("metadata", {}),
            )
            if feature_name == "lifecycle":
                feature["metadata"]["source"] = "transition-engine"
        return normalized

    def _resolve_world_state_things(
        self,
        correlation_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        if correlation_id:
            correlated = self.store.list_twins_for_correlation(correlation_id)
            if correlated:
                return [json.loads(row["thing_json"]) for row in correlated]
        return self.list_twins()

    def _feature(
        self,
        current: Dict[str, Any],
        unit: str,
        source: str,
        updated_at: str,
        desired: Optional[Dict[str, Any]] = None,
        reported: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "properties": {
                "desired": deepcopy(current if desired is None else desired),
                "reported": deepcopy(current if reported is None else reported),
                "current": deepcopy(current),
            },
            "metadata": {
                "lastUpdated": updated_at,
                "source": source,
                "unit": unit,
            },
        }

    def _set_lifecycle(self, thing: Dict[str, Any], new_state: str, timestamp: str) -> None:
        feature = thing["features"]["lifecycle"]
        current = feature["properties"]["current"]
        feature["properties"]["current"] = {
            "state": new_state,
            "allowed": current.get("allowed", []),
            "previous": current.get("state"),
            "timestamp": timestamp,
        }
        feature["properties"]["reported"] = deepcopy(feature["properties"]["current"])
        feature["metadata"]["lastUpdated"] = timestamp

    def _distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        multiplier: float,
    ) -> float:
        return self._haversine_km(lat1, lon1, lat2, lon2) * multiplier

    def _interpolate_location(
        self,
        plant: Dict[str, Any],
        port: Dict[str, Any],
        fraction: float,
        lateral_offset: float = 0.0,
    ) -> Dict[str, float]:
        base_lat = plant["lat"] + (port["lat"] - plant["lat"]) * fraction
        base_lon = plant["lon"] + (port["lon"] - plant["lon"]) * fraction
        delta_lat = port["lat"] - plant["lat"]
        delta_lon = port["lon"] - plant["lon"]
        magnitude = math.hypot(delta_lat, delta_lon) or 1.0
        normal_lat = -delta_lon / magnitude
        normal_lon = delta_lat / magnitude
        return {
            "lat": round(base_lat + normal_lat * lateral_offset, 6),
            "lon": round(base_lon + normal_lon * lateral_offset, 6),
        }

    def _dispatch_unit_ids(self, plant_id: str, count: int) -> List[str]:
        slug = plant_id.split(":")[-1].replace("-steel-plant", "")
        return [f"transport:{slug}-dispatch-{index:02d}" for index in range(1, count + 1)]

    def _transport_lateral_offset(self, index: int, total_units: int) -> float:
        center = (total_units - 1) / 2
        return round((index - center) * 0.16, 3)

    def _node_from_thing(
        self,
        thing: Dict[str, Any],
        selected: bool,
        muted: bool,
    ) -> Dict[str, Any]:
        location = thing["features"]["location"]["properties"]["current"]
        emission = thing["features"]["emission"]["properties"]["current"]
        lifecycle = thing["features"]["lifecycle"]["properties"]["current"]
        return {
            "id": thing["thingId"],
            "label": thing["attributes"]["name"],
            "type": thing["metadata"]["entityType"],
            "lat": location.get("lat"),
            "lon": location.get("lon"),
            "state": lifecycle.get("state"),
            "selected": selected,
            "muted": muted,
            "overview": False,
            "totalTco2": emission.get("total_tco2", 0.0),
        }

    def _truck_from_thing(self, thing: Dict[str, Any]) -> Dict[str, Any]:
        location = thing["features"]["location"]["properties"]["current"]
        emission = thing["features"]["emission"]["properties"]["current"]
        lifecycle = thing["features"]["lifecycle"]["properties"]["current"]
        material = thing["features"]["materialFlow"]["properties"]["current"]
        return {
            "id": thing["thingId"],
            "label": thing["attributes"]["name"],
            "lat": location.get("lat"),
            "lon": location.get("lon"),
            "state": lifecycle.get("state"),
            "loadTonnes": material.get("batchTonnes", 0.0),
            "totalTco2": emission.get("total_tco2", 0.0),
            "muted": False,
        }

    def _spatial_node_ref(self, plant: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": plant["id"],
            "label": plant["label"],
            "shortLabel": self._short_label(plant["label"]),
            "lat": plant["lat"],
            "lon": plant["lon"],
            "type": "plant",
        }

    def _spatial_port_ref(self, port: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": port["id"],
            "label": port["label"],
            "shortLabel": self._short_label(port["label"]),
            "lat": port["lat"],
            "lon": port["lon"],
            "type": "port",
        }

    def _spatial_supplier_ref(self, supplier: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": supplier["id"],
            "label": supplier["label"],
            "shortLabel": self._short_label(supplier["label"]),
            "lat": supplier["lat"],
            "lon": supplier["lon"],
            "type": "supplier",
        }

    def _short_label(self, label: str) -> str:
        replacements = {
            "Bhilai Steel Plant": "Bhilai",
            "Bokaro Steel Plant": "Bokaro",
            "Rourkela Steel Plant": "Rourkela",
            "Durgapur Steel Plant": "Durgapur",
            "Visakhapatnam Port": "Vizag Port",
            "Haldia Dock Complex": "Haldia",
            "Paradip Port": "Paradip",
            "Dalli Rajhara Iron Ore Complex": "Dalli Rajhara",
            "Meghahatuburu Iron Ore Mine": "Meghahatuburu",
        }
        return replacements.get(label, label)

    def _scenarios_for_plant(self, plant_id: Optional[str]) -> List[Dict[str, Any]]:
        if plant_id is None:
            scenarios: List[Dict[str, Any]] = []
            for items in self.scenarios_by_plant.values():
                scenarios.extend(items)
            scenarios.sort(key=lambda item: (item["plantId"], item["label"]))
            return scenarios
        if plant_id not in self.scenarios_by_plant:
            return []
        return list(self.scenarios_by_plant[plant_id])

    def _resolve_scenario(
        self,
        plant_id: Optional[str],
        scenario_id: Optional[str],
        supplier_thing_id: Optional[str],
    ) -> Dict[str, Any]:
        if scenario_id:
            scenario = self.scenarios_by_id.get(scenario_id)
            if scenario is None:
                raise IndiaSteelTwinError(f"Unknown scenario '{scenario_id}'")
            if plant_id and scenario["plantId"] != plant_id:
                raise IndiaSteelTwinError(
                    f"Scenario '{scenario_id}' does not belong to plant '{plant_id}'"
                )
            return scenario

        for scenario in self._scenarios_for_plant(plant_id):
            if supplier_thing_id and scenario["supplierId"] == supplier_thing_id:
                return scenario

        if plant_id and self._scenarios_for_plant(plant_id):
            return self._scenarios_for_plant(plant_id)[0]
        if supplier_thing_id:
            for scenario in self.data["plantSupplierScenarios"]:
                if scenario["supplierId"] == supplier_thing_id:
                    return scenario
        raise IndiaSteelTwinError("Unable to resolve a plant-scoped scenario")

    def _maybe_plant(self, plant_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not plant_id:
            return None
        return self._plant_profile(plant_id)

    def _plant_profile(self, plant_id: str) -> Dict[str, Any]:
        if plant_id not in self.plants_by_id:
            raise IndiaSteelTwinError(f"Unknown plant '{plant_id}'")
        return self.plants_by_id[plant_id]

    def _supplier_profile(self, supplier_thing_id: str) -> Dict[str, Any]:
        if supplier_thing_id not in self.suppliers_by_id:
            raise IndiaSteelTwinError(f"Unknown supplier '{supplier_thing_id}'")
        return self.suppliers_by_id[supplier_thing_id]

    def _port_profile(self, port_id: str) -> Dict[str, Any]:
        if port_id not in self.ports_by_id:
            raise IndiaSteelTwinError(f"Unknown port '{port_id}'")
        return self.ports_by_id[port_id]

    def _plant_port_id(self, plant_id: Optional[str]) -> Optional[str]:
        if plant_id is None:
            return None
        return self._plant_profile(plant_id)["port_id"]

    def _entity_type_for_definition(self, definition: str) -> str:
        mapping = {
            self.SUPPLIER_DEFINITION: "supplier",
            "org.eclipse.ditto:SupplierTwin:2.0.0": "supplier",
            self.PLANT_DEFINITION: "plant",
            "org.eclipse.ditto:PlantTwin:2.0.0": "plant",
            self.TRANSPORT_DEFINITION: "transport",
            "org.eclipse.ditto:TransportTwin:2.0.0": "transport",
            self.PORT_DEFINITION: "port",
            "org.eclipse.ditto:PortTwin:2.0.0": "port",
        }
        if definition not in mapping:
            raise IndiaSteelTwinError(f"Unknown definition '{definition}'")
        return mapping[definition]

    def _architecture(self) -> Dict[str, Any]:
        return {
            "layers": [
                "Digital Twin Layer",
                "State Transition Engine",
                "Emission Engine",
                "Ledger Abstraction",
                "API Layer",
            ],
            "explanation": {
                "Digital Twin Layer": "Persistent plant-scoped world-state store for suppliers, plant, transport units, and export port.",
                "State Transition Engine": "Applies lifecycle changes, validates progression, and emits stage events across the selected SAIL network.",
                "Emission Engine": "Calculates Scope 1, 2, and 3 values for supplier, plant, transport, and port checkpoints.",
                "Ledger Abstraction": "Writes Fabric-ready evidence records through a backend interface while Phase 1 uses a local audit chain.",
                "API Layer": "Exposes plant registry, scenarios, execution, replay, ledger, and authority evidence endpoints.",
            },
        }

    def _stage_visibility(self, active_stage: Optional[str]) -> Dict[str, bool]:
        if active_stage in {
            "supplier.selected",
            "supplier.dispatched",
            "plant.received_material",
            "plant.production_completed",
        }:
            return {
                "showSupplierPath": True,
                "showDispatchPaths": False,
                "showDeliveryPaths": False,
                "showTransportUnits": False,
            }
        if active_stage == "transport.assigned":
            return {
                "showSupplierPath": True,
                "showDispatchPaths": True,
                "showDeliveryPaths": False,
                "showTransportUnits": True,
            }
        if active_stage in {
            "transport.departed",
            "transport.arrived_port",
            "transport.unloaded",
            "port.received",
            "port.customs_cleared",
            "port.delivered",
        }:
            return {
                "showSupplierPath": True,
                "showDispatchPaths": True,
                "showDeliveryPaths": True,
                "showTransportUnits": True,
            }
        return {
            "showSupplierPath": False,
            "showDispatchPaths": False,
            "showDeliveryPaths": False,
            "showTransportUnits": False,
        }

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_km * c


india_steel_twin_service = IndiaSteelTwinPlatform()

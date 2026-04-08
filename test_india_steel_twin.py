import unittest
import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.india_steel_digital_twin import india_steel_twin_service


ROURKELA_PLANT = "plant:rourkela-steel-plant"
ROURKELA_SCENARIO = "rourkela_kalta"
ROURKELA_SUPPLIER = "supplier:kalta-iron-ore-mine"
BHILAI_PLANT = "plant:bhilai-steel-plant"
BHILAI_SUPPLIER = "supplier:rowghat-iron-ore-mine"


class IndiaSteelTwinServiceTests(unittest.TestCase):
    def setUp(self):
        india_steel_twin_service.store.clear_runtime()

    def test_each_plant_has_three_supplier_scenarios(self):
        plants = india_steel_twin_service.list_plants()
        self.assertEqual(len(plants), 4)
        for plant in plants:
            scenarios = india_steel_twin_service.list_scenarios(plant["plantId"])
            self.assertGreaterEqual(len(scenarios), 2)
            self.assertEqual(len(scenarios), 3)

    def test_compare_scenarios_prefers_lowest_rourkela_supplier(self):
        comparison = india_steel_twin_service.compare_scenarios(ROURKELA_PLANT, 1000.0)
        ranked = comparison["rankedScenarios"]
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["scenarioId"], ROURKELA_SCENARIO)
        self.assertLess(ranked[0]["totalTco2"], ranked[-1]["totalTco2"])

    def test_tampered_ledger_is_detected(self):
        run = india_steel_twin_service.execute_scenario(
            ROURKELA_PLANT,
            ROURKELA_SCENARIO,
            ROURKELA_SUPPLIER,
            1000.0,
        )
        self.assertTrue(run["ledger"]["isValid"])

        with india_steel_twin_service.store._connection() as connection:  # noqa: SLF001
            connection.execute(
                "UPDATE ledger_blocks SET payload_json = ? WHERE correlation_id = ? AND block_index = 1",
                ('{"tampered": true}', run["correlationId"]),
            )

        ledger = india_steel_twin_service.get_ledger(run["correlationId"])
        self.assertFalse(ledger["isValid"])


class IndiaSteelTwinApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        india_steel_twin_service.store.clear_runtime()

    def test_context_plants_and_scenario_endpoints(self):
        context = self.client.get("/india-steel-twin/context")
        self.assertEqual(context.status_code, 200)
        context_payload = context.json()["data"]
        self.assertEqual(len(context_payload["plant_selection"]["plants"]), 4)

        plant_context = self.client.get(f"/india-steel-twin/context?plantId={ROURKELA_PLANT}")
        self.assertEqual(plant_context.status_code, 200)
        self.assertEqual(
            plant_context.json()["data"]["plant_selection"]["selectedPlantId"],
            ROURKELA_PLANT,
        )

        plants = self.client.get("/india-steel-twin/plants")
        self.assertEqual(plants.status_code, 200)
        self.assertEqual(len(plants.json()["data"]), 4)

        scenarios = self.client.get(f"/india-steel-twin/scenarios?plantId={ROURKELA_PLANT}")
        self.assertEqual(scenarios.status_code, 200)
        self.assertEqual(len(scenarios.json()["data"]), 3)

        overlay_initial = self.client.get("/india-steel-twin/spatial-overlay")
        self.assertEqual(overlay_initial.status_code, 200)
        initial_payload = overlay_initial.json()["data"]
        self.assertEqual(len(initial_payload["nodes"]), 1)
        self.assertEqual(initial_payload["nodes"][0]["id"], "port:jnpt-mumbai")

        overlay = self.client.get(f"/india-steel-twin/spatial-overlay?plantId={ROURKELA_PLANT}")
        self.assertEqual(overlay.status_code, 200)
        overlay_payload = overlay.json()["data"]
        self.assertEqual(overlay_payload["plantId"], ROURKELA_PLANT)
        self.assertEqual(overlay_payload["activeStage"], "Plant selected")
        self.assertEqual(len(overlay_payload["edges"]), 0)
        self.assertEqual(len(overlay_payload["nodes"]), 2)

        alignment = self.client.get("/india-steel-twin/framework-alignment")
        self.assertEqual(alignment.status_code, 200)
        frameworks = alignment.json()["data"]["frameworks"]
        self.assertTrue(any(item["name"] == "Hyperledger Fabric" for item in frameworks))

    def test_create_get_list_and_patch_twin(self):
        create_response = self.client.post(
            "/india-steel-twin/twins",
            json={
                "thingId": "transport:test-truck",
                "definition": "org.eclipse.ditto:TransportTwin:2.0.0",
                "attributes": {
                    "name": "Test Truck",
                    "operator": "Demo Fleet",
                    "state": "Odisha",
                },
                "features": {
                    "location": {
                        "properties": {"current": {"lat": 20.98, "lon": 85.99}},
                        "metadata": {"unit": "geo"},
                    },
                    "materialFlow": {
                        "properties": {"current": {"material": "hot_rolled_coil", "batchTonnes": 0.0}},
                        "metadata": {"unit": "tonnes"},
                    },
                    "emission": {
                        "properties": {"current": {"scope_1_tco2": 0.0, "scope_2_tco2": 0.0, "scope_3_tco2": 0.0, "total_tco2": 0.0}},
                        "metadata": {"unit": "tCO2"},
                    },
                    "lifecycle": {
                        "properties": {"current": {"state": "created", "allowed": ["created", "assigned", "in_transit", "at_port", "unloaded"]}},
                        "metadata": {"unit": "state"},
                    },
                },
            },
        )
        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()["data"]
        self.assertEqual(created["thingId"], "transport:test-truck")

        list_response = self.client.get("/india-steel-twin/twins")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["data"]), 1)

        get_response = self.client.get("/india-steel-twin/twins/transport:test-truck")
        self.assertEqual(get_response.status_code, 200)
        twin = get_response.json()["data"]

        desired_patch = self.client.patch(
            "/india-steel-twin/twins/transport:test-truck/desired",
            json={
                "feature": "location",
                "properties": {"lat": 20.5, "lon": 86.1},
                "metadata": {"note": "planned dispatch"},
                "expectedRevision": twin["revision"],
            },
        )
        self.assertEqual(desired_patch.status_code, 200)
        desired_twin = desired_patch.json()["data"]
        self.assertEqual(
            desired_twin["features"]["location"]["properties"]["current"]["lat"],
            20.5,
        )

        reported_patch = self.client.patch(
            "/india-steel-twin/twins/transport:test-truck/reported",
            json={
                "feature": "emission",
                "properties": {"scope_1_tco2": 5.2, "total_tco2": 5.2},
                "metadata": {"source": "telematics"},
                "expectedRevision": desired_twin["revision"],
            },
        )
        self.assertEqual(reported_patch.status_code, 200)
        reported_twin = reported_patch.json()["data"]
        self.assertEqual(
            reported_twin["features"]["emission"]["properties"]["current"]["total_tco2"],
            5.2,
        )

        invalid_patch = self.client.patch(
            "/india-steel-twin/twins/transport:test-truck/reported",
            json={
                "feature": "lifecycle",
                "properties": {"state": "in_transit"},
            },
        )
        self.assertEqual(invalid_patch.status_code, 400)

    def test_revision_conflict_returns_409(self):
        create_response = self.client.post(
            "/india-steel-twin/twins",
            json={
                "thingId": "supplier:test-supplier",
                "definition": "org.eclipse.ditto:SupplierTwin:2.0.0",
                "features": {
                    "location": {
                        "properties": {"current": {"lat": 20.1, "lon": 86.2}},
                        "metadata": {"unit": "geo"},
                    },
                    "materialFlow": {
                        "properties": {"current": {"material": "iron_ore_fines", "batchTonnes": 0.0}},
                        "metadata": {"unit": "tonnes"},
                    },
                    "emission": {
                        "properties": {"current": {"scope_1_tco2": 0.0, "scope_2_tco2": 0.0, "scope_3_tco2": 0.0, "total_tco2": 0.0}},
                        "metadata": {"unit": "tCO2"},
                    },
                    "lifecycle": {
                        "properties": {"current": {"state": "raw", "allowed": ["raw", "allocated", "dispatched", "received_by_plant"]}},
                        "metadata": {"unit": "state"},
                    },
                },
            },
        )
        revision = create_response.json()["data"]["revision"]

        first_patch = self.client.patch(
            "/india-steel-twin/twins/supplier:test-supplier/desired",
            json={
                "feature": "materialFlow",
                "properties": {"batchTonnes": 10},
                "expectedRevision": revision,
            },
        )
        self.assertEqual(first_patch.status_code, 200)

        stale_patch = self.client.patch(
            "/india-steel-twin/twins/supplier:test-supplier/desired",
            json={
                "feature": "materialFlow",
                "properties": {"batchTonnes": 20},
                "expectedRevision": revision,
            },
        )
        self.assertEqual(stale_patch.status_code, 409)

    def test_execute_advance_and_evidence_endpoints(self):
        execute = self.client.post(
            "/india-steel-twin/scenarios/execute",
            json={
                "plantId": ROURKELA_PLANT,
                "scenarioId": ROURKELA_SCENARIO,
                "supplierThingId": ROURKELA_SUPPLIER,
                "batchTonnes": 1000.0,
            },
        )
        self.assertEqual(execute.status_code, 200)
        execute_payload = execute.json()["data"]
        self.assertTrue(execute_payload["completed"])
        self.assertEqual(execute_payload["plantId"], ROURKELA_PLANT)
        self.assertEqual(execute_payload["ledger"]["chainLength"], 5)
        self.assertTrue(execute_payload["ledger"]["isValid"])
        self.assertEqual(
            execute_payload["systemState"]["currentStage"],
            "port.delivered",
        )
        self.assertGreaterEqual(len(execute_payload["events"]), 11)

        system_state = self.client.get(
            f"/india-steel-twin/system/state?correlationId={execute_payload['correlationId']}"
        )
        self.assertEqual(system_state.status_code, 200)
        self.assertAlmostEqual(
            system_state.json()["data"]["aggregatedEmissions"]["total_tco2"],
            execute_payload["systemState"]["aggregatedEmissions"]["total_tco2"],
            places=4,
        )

        evidence = self.client.get(
            f"/india-steel-twin/evidence/{execute_payload['correlationId']}"
        )
        self.assertEqual(evidence.status_code, 200)
        evidence_payload = evidence.json()["data"]["evidenceBundle"]
        self.assertEqual(evidence_payload["recordType"], "EvidenceBundle")
        self.assertTrue(evidence_payload["verification"]["isValid"])
        self.assertEqual(len(evidence_payload["ledgerReferences"]), 5)

        new_correlation = f"step-{uuid.uuid4().hex[:8]}"
        advance_one = self.client.post(
            "/india-steel-twin/transitions/advance",
            json={
                "correlationId": new_correlation,
                "plantId": BHILAI_PLANT,
                "sourceThingId": BHILAI_SUPPLIER,
                "batchTonnes": 1000.0,
            },
        )
        self.assertEqual(advance_one.status_code, 200)
        self.assertEqual(advance_one.json()["data"]["currentStage"], "supplier.selected")

        advance_two = self.client.post(
            "/india-steel-twin/transitions/advance",
            json={
                "correlationId": new_correlation,
                "plantId": BHILAI_PLANT,
                "sourceThingId": BHILAI_SUPPLIER,
                "batchTonnes": 1000.0,
            },
        )
        self.assertEqual(advance_two.status_code, 200)
        self.assertEqual(advance_two.json()["data"]["currentStage"], "supplier.dispatched")

    def test_events_stream_returns_sse_payload(self):
        execute = self.client.post(
            "/india-steel-twin/scenarios/execute",
            json={
                "plantId": ROURKELA_PLANT,
                "scenarioId": ROURKELA_SCENARIO,
                "supplierThingId": ROURKELA_SUPPLIER,
                "batchTonnes": 1000.0,
            },
        )
        correlation_id = execute.json()["data"]["correlationId"]

        response = self.client.get(f"/india-steel-twin/events/stream?correlationId={correlation_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("event: supplier.selected", response.text)
        self.assertIn("event: heartbeat", response.text)


if __name__ == "__main__":
    unittest.main()

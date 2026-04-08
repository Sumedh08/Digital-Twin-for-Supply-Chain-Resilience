from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.india_steel_digital_twin import (
    IndiaSteelTwinError,
    InvalidTransitionError,
    RevisionConflictError,
    india_steel_twin_service,
)


router = APIRouter(prefix="/india-steel-twin", tags=["india-steel-twin"])


class TwinCreateRequest(BaseModel):
    thingId: str
    definition: str
    policyId: str | None = None
    attributes: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)


class TwinPatchRequest(BaseModel):
    feature: str
    properties: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    expectedRevision: int | None = None


class TransitionCommand(BaseModel):
    correlationId: str
    action: str = "next"
    plantId: str | None = None
    sourceThingId: str | None = None
    targetThingId: str | None = None
    batchTonnes: float = Field(default=1000.0, gt=0)
    truckIds: list[str] | None = None


class ScenarioExecuteRequest(BaseModel):
    plantId: str | None = None
    scenarioId: str | None = None
    supplierThingId: str | None = None
    batchTonnes: float = Field(default=1000.0, gt=0)


class IndiaSteelTwinComparisonRequest(BaseModel):
    plantId: str | None = None
    batchTonnes: float = Field(default=1000.0, gt=0)


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, RevisionConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, InvalidTransitionError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, IndiaSteelTwinError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise exc


@router.get("/context")
async def get_context(plantId: str | None = Query(default=None)):
    return {"success": True, "data": india_steel_twin_service.get_context(plantId)}


@router.get("/plants")
async def get_plants():
    return {"success": True, "data": india_steel_twin_service.list_plants()}


@router.get("/framework-alignment")
async def get_framework_alignment():
    return {"success": True, "data": india_steel_twin_service.framework_alignment()}


@router.get("/scenarios")
async def get_scenarios(plantId: str | None = Query(default=None)):
    return {"success": True, "data": india_steel_twin_service.list_scenarios(plantId)}


@router.post("/compare")
async def compare_scenarios(request: IndiaSteelTwinComparisonRequest):
    return {
        "success": True,
        "data": india_steel_twin_service.compare_scenarios(request.plantId, request.batchTonnes),
    }


@router.post("/simulate")
async def simulate_scenario(request: ScenarioExecuteRequest):
    try:
        return {
            "success": True,
            "data": india_steel_twin_service.execute_scenario(
                request.plantId,
                request.scenarioId,
                request.supplierThingId or "",
                request.batchTonnes,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.post("/scenarios/execute")
async def execute_scenario(request: ScenarioExecuteRequest):
    try:
        return {
            "success": True,
            "data": india_steel_twin_service.execute_scenario(
                request.plantId,
                request.scenarioId,
                request.supplierThingId or "",
                request.batchTonnes,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.post("/transitions/advance")
async def advance_transition(request: TransitionCommand):
    try:
        return {
            "success": True,
            "data": india_steel_twin_service.advance_transition(
                correlation_id=request.correlationId,
                action=request.action,
                plant_id=request.plantId,
                source_thing_id=request.sourceThingId,
                target_thing_id=request.targetThingId,
                batch_tonnes=request.batchTonnes,
                truck_ids=request.truckIds,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.post("/twins")
async def create_twin(request: TwinCreateRequest):
    try:
        return {"success": True, "data": india_steel_twin_service.create_twin(request.model_dump())}
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.get("/twins")
async def list_twins():
    return {"success": True, "data": india_steel_twin_service.list_twins()}


@router.get("/twins/{thing_id}")
async def get_twin(thing_id: str):
    try:
        return {"success": True, "data": india_steel_twin_service.get_twin(thing_id)}
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.patch("/twins/{thing_id}/desired")
async def patch_twin_desired(thing_id: str, request: TwinPatchRequest):
    try:
        return {
            "success": True,
            "data": india_steel_twin_service.patch_twin(
                thing_id,
                layer="desired",
                feature_name=request.feature,
                properties=request.properties,
                metadata=request.metadata,
                expected_revision=request.expectedRevision,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.patch("/twins/{thing_id}/reported")
async def patch_twin_reported(thing_id: str, request: TwinPatchRequest):
    try:
        return {
            "success": True,
            "data": india_steel_twin_service.patch_twin(
                thing_id,
                layer="reported",
                feature_name=request.feature,
                properties=request.properties,
                metadata=request.metadata,
                expected_revision=request.expectedRevision,
            ),
        }
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.get("/system/state")
async def get_system_state(correlationId: str | None = Query(default=None)):
    return {
        "success": True,
        "data": india_steel_twin_service.get_system_state(correlationId),
    }


@router.get("/events")
async def get_events(
    correlationId: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    return {
        "success": True,
        "data": india_steel_twin_service.get_events(correlationId, limit),
    }


@router.get("/events/stream")
async def stream_events(correlationId: str | None = Query(default=None)):
    payload = india_steel_twin_service.stream_events(correlationId)
    return StreamingResponse(iter([payload]), media_type="text/event-stream")


@router.get("/ledger")
async def get_ledger(correlationId: str | None = Query(default=None)):
    return {"success": True, "data": india_steel_twin_service.get_ledger(correlationId)}


@router.get("/spatial-overlay")
async def get_spatial_overlay(
    correlationId: str | None = Query(default=None),
    plantId: str | None = Query(default=None),
    supplierIds: str | None = Query(default=None),
):
    parsed_supplier_ids = None
    if supplierIds:
        parsed_supplier_ids = [sid.strip() for sid in supplierIds.split(",") if sid.strip()]
    return {
        "success": True,
        "data": india_steel_twin_service.get_spatial_overlay(correlationId, plantId, parsed_supplier_ids),
    }


@router.get("/evidence/{correlation_id}")
async def get_evidence_bundle(correlation_id: str):
    try:
        return {
            "success": True,
            "data": india_steel_twin_service.get_evidence_bundle(correlation_id),
        }
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc)


@router.get("/system/network-status")
async def get_network_status():
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}: {{.Status}}", "--filter", "name=fabric_test"],
            capture_output=True,
            text=True,
            check=False
        )
        containers = [line.strip() for line in result.stdout.split("\n") if line.strip()]
        return {
            "success": True,
            "data": {
                "containers": containers,
                "count": len(containers),
                "target": "hyperledger_fabric"
            }
        }
    except Exception:
        return {
            "success": True,
            "data": {
                "containers": [],
                "count": 0,
                "target": "local_fallback"
            }
        }

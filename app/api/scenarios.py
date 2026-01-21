"""Scenarios API endpoints for practice conversations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.logging_config import get_logger
from app.services.scenarios import ScenariosService

router = APIRouter()
logger = get_logger("api.scenarios")


class ScenariosListResponse(BaseModel):
    scenarios: list[dict]


@router.get("", response_model=ScenariosListResponse)
async def list_scenarios(difficulty: str | None = None, methodology: str | None = None):
    """List available practice scenarios."""
    service = ScenariosService()

    if difficulty:
        scenarios = service.get_by_difficulty(difficulty)
    elif methodology:
        scenarios = service.get_by_methodology(methodology)
    else:
        scenarios = service.list_all()

    logger.debug("Listed scenarios", extra={"count": len(scenarios)})
    return ScenariosListResponse(scenarios=scenarios)


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get a specific scenario by ID."""
    service = ScenariosService()
    scenario = service.get_by_id(scenario_id)

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return scenario.to_dict()

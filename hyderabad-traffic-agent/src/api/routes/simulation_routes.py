from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from src.domains.traffic.simulation_engine import SumoSimulationEngine

router = APIRouter()
engine = SumoSimulationEngine()

class RunSimulationRequest(BaseModel):
    scenario_id: Optional[str] = "biodiversity_junction"
    intervention_type: Optional[str] = "atsc" # "atsc" | "reroute" | "drainage"
    duration_frames: Optional[int] = 40

@router.get("/scenarios")
def list_scenarios():
    """Lists all available Hyderabad intersection simulation scenarios."""
    return engine.list_scenarios()

@router.post("/run")
def run_simulation(req: RunSimulationRequest):
    """
    Executes a microscopic traffic simulation run for an intersection.
    Returns vehicle trajectory step frames and Baseline vs. Intervention metrics.
    """
    try:
        results = engine.run_simulation(
            scenario_id=req.scenario_id or "biodiversity_junction",
            intervention_type=req.intervention_type or "atsc",
            duration_frames=min(100, max(15, req.duration_frames or 40))
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/live")
def get_live_status(scenario_id: str = "biodiversity_junction"):
    """Quick live status snapshot of the junction simulation."""
    res = engine.run_simulation(scenario_id=scenario_id, duration_frames=5)
    return {
        "scenario": res["scenario"],
        "comparison": res["comparison"],
        "status": "ready"
    }

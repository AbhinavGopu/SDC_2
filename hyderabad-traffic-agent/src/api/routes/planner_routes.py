from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def planner_health():
    return {"status": "planner route online"}

@router.get("/dashboard")
def planner_dashboard():
    return {"message": "Planner dashboard API is ready."}

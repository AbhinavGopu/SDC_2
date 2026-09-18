
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.agent_routes import router as agent_router
from .routes.auth_routes import router as auth_router
from .routes.citizen_routes import router as citizen_router
from .routes.locality_routes import router as locality_router
from .routes.planner_routes import router as planner_router
from .routes.simulation_routes import router as simulation_router
from src.auth.seed import seed_data
from src.db.seed import seed_hyderabad_data

app = FastAPI(
    title="Hyderabad Traffic-Focused Agentic City Planner API",
    description="Backend API for citizen complaints and planner dashboard analytics.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    seed_data()
    seed_hyderabad_data()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(citizen_router, prefix="/citizen", tags=["citizen"])
app.include_router(planner_router, prefix="/planner", tags=["planner"])
app.include_router(locality_router, prefix="/locality", tags=["locality"])
app.include_router(agent_router, prefix="/agent", tags=["agent"])
app.include_router(simulation_router, prefix="/simulation", tags=["simulation"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Hyderabad Traffic-Focused Agentic City Planner API"}

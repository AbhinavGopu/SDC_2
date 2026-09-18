from typing import Dict, Any, List
from src.rag.retriever import retrieve_context, format_context_for_prompt
from src.domains.traffic.simulation_engine import SumoSimulationEngine
from src.domains.traffic.infra_advisor.cost_estimator import CostEstimator

class AgentTools:
    """
    Tool registry for the Hyderabad Multi-Agent AI Planner.
    Provides verified tools for RAG document retrieval, SUMO simulation, and cost checks.
    """

    def __init__(self):
        self.sim_engine = SumoSimulationEngine()
        self.cost_estimator = CostEstimator()

    def search_rag_knowledge(self, query: str, db, limit: int = 3) -> Dict[str, Any]:
        """Retrieves urban planning guidelines and past citizen complaints from vector DB."""
        ctx = retrieve_context(query, db, limit=limit)
        return {
            "formatted_text": format_context_for_prompt(ctx),
            "documents_count": len(ctx["documents"]),
            "complaints_count": len(ctx["complaints"])
        }

    def run_sumo_simulation(self, scenario_id: str, intervention: str = "atsc") -> Dict[str, Any]:
        """Runs microscopic traffic simulation to verify delay reduction and speed gains."""
        return self.sim_engine.run_simulation(scenario_id=scenario_id, intervention_type=intervention, duration_frames=20)

    def estimate_civil_cost(self, intervention_type: str, scale_units: float = 1.0) -> Dict[str, Any]:
        """Computes cost in Lakhs using GHMC Schedule of Rates."""
        rates = {
            "signal_atsc": 45.0,
            "drainage_upgrade": 25.0,
            "road_widening_km": 280.0,
            "flyover_grade": 1500.0,
            "dust_sprinklers": 12.0
        }
        base = rates.get(intervention_type, 30.0)
        total_lakhs = base * scale_units
        return {
            "intervention_type": intervention_type,
            "total_cost_lakhs": total_lakhs,
            "is_crore_scale": total_lakhs >= 100.0
        }

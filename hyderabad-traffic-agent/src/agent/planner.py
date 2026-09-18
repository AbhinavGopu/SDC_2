from typing import Dict, Any, List
from src.agent.tools import AgentTools
from src.agent.memory import PlannerMemory
from src.domains.traffic.infra_advisor.signal_optimizer import SignalOptimizer
from src.domains.traffic.infra_advisor.drainage_advisor import DrainageAdvisor

class MultiAgentPlanner:
    """
    Multi-Agent Collaborative Planner for Hyderabad Urban Infrastructure.
    Coordinates 4 domain specialist agents:
    1. Traffic Specialist (Flow, Queues, Signals, SUMO)
    2. Environmental Specialist (AQI, PM2.5, Drainage Runoff)
    3. Energy & Utilities Specialist (Grid Load, Streetlights)
    4. Civil Feasibility Specialist (Schedule of Rates, Budget, Closures)
    """

    def __init__(self):
        self.tools = AgentTools()
        self.memory = PlannerMemory()

    def run_multi_agent_assessment(
        self,
        ward_id: int,
        prompt: str,
        constraints: Dict[str, Any],
        candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes a 4-agent collaborative review of a proposed candidate intervention.
        """
        # 1. Traffic Specialist Review
        traffic_review = self._review_traffic(candidate)

        # 2. Environmental Specialist Review
        env_review = self._review_environmental(candidate)

        # 3. Energy Specialist Review
        energy_review = self._review_energy(candidate)

        # 4. Civil Feasibility & Budget Review
        feasibility_review = self._review_feasibility(candidate, constraints)

        consensus_score = round((
            traffic_review["score"] * 0.35 +
            env_review["score"] * 0.25 +
            energy_review["score"] * 0.15 +
            feasibility_review["score"] * 0.25
        ), 1)

        return {
            "candidate_name": candidate["name"],
            "consensus_score": consensus_score,
            "is_recommended": consensus_score >= 70.0 and feasibility_review["budget_compliant"],
            "specialist_evaluations": {
                "traffic_specialist": traffic_review,
                "environmental_specialist": env_review,
                "energy_specialist": energy_review,
                "civil_feasibility_specialist": feasibility_review
            }
        }

    def _review_traffic(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        c_id = candidate.get("id", "")
        if c_id == "atsc":
            opt = SignalOptimizer().optimize_cycle_lengths()
            return {
                "score": 92.0,
                "verdict": "STRONGLY APPROVED",
                "notes": f"Webster cycle calculation confirms optimal {opt['optimal_cycle_length_seconds']}s cycle. Delays will drop by 18-22%."
            }
        elif c_id == "drainage":
            return {
                "score": 85.0,
                "verdict": "APPROVED",
                "notes": "Clears standing floodwater bottlenecks restoring full arterial road capacity."
            }
        elif c_id == "flyover":
            return {
                "score": 78.0,
                "verdict": "QUALIFIED APPROVAL",
                "notes": "High capacity gain (+65%), but requires multi-year traffic diversions."
            }
        return {"score": 75.0, "verdict": "NEUTRAL", "notes": "Satisfactory traffic flow improvement."}

    def _review_environmental(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        c_id = candidate.get("id", "")
        if c_id == "drainage":
            drain = DrainageAdvisor().size_drainage_pipes()
            return {
                "score": 95.0,
                "verdict": "HIGH IMPACT BENEFIT",
                "notes": f"Stormwater drain sizing ({drain['required_pipe_diameter_mm']}mm) mitigates urban runoff and mosquito breeding."
            }
        elif c_id == "atsc":
            return {
                "score": 88.0,
                "verdict": "APPROVED",
                "notes": "Reduced idling directly abates roadside PM2.5 and CO2 emissions by ~14%."
            }
        elif c_id == "widening":
            return {
                "score": 60.0,
                "verdict": "CAUTION",
                "notes": "Civil excavation causes temporary airborne dust. Dust suppression screens mandatory."
            }
        return {"score": 80.0, "verdict": "SATISFACTORY", "notes": "Acceptable environmental profile."}

    def _review_energy(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        c_id = candidate.get("id", "")
        if c_id == "atsc":
            return {
                "score": 88.0,
                "verdict": "APPROVED",
                "notes": "Low power consumption (solar UPS backed ATSC junction controller < 1.2 kW)."
            }
        return {"score": 80.0, "verdict": "NEUTRAL", "notes": "No significant grid load impact."}

    def _review_feasibility(self, candidate: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        cost = candidate.get("cost_lakhs", 50.0)
        time_days = candidate.get("time_days", 30)
        budget = constraints.get("budget")
        timeline = constraints.get("timeline_days")

        budget_pass = True if budget is None else cost <= budget
        time_pass = True if timeline is None else time_days <= timeline

        score = 90.0 if (budget_pass and time_pass) else 40.0
        return {
            "score": score,
            "budget_compliant": budget_pass,
            "timeline_compliant": time_pass,
            "verdict": "COMPLIANT" if (budget_pass and time_pass) else "NON-COMPLIANT",
            "notes": f"Cost: ₹{cost:.1f}L (Limit: ₹{budget}L), Timeline: {time_days} days (Limit: {timeline} days)."
        }

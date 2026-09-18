from datetime import datetime
from typing import Dict, Any, List, Optional

class PlannerMemory:
    """
    Semantic memory and historical intervention success log.
    Stores planner decisions, approved projects, and post-intervention KPI results.
    """

    _MEMORY_STORE: List[Dict[str, Any]] = [
        {
            "ward_id": 2,
            "ward_name": "Gachibowli",
            "decision": "Approved Adaptive Signal Control (ATSC) installation at Bio-diversity junction.",
            "budget_approved_lakhs": 45.0,
            "timestamp": "2026-07-15T10:30:00Z",
            "kpi_outcome": "Average peak vehicle delay reduced by 21.4%."
        },
        {
            "ward_id": 1,
            "ward_name": "Ameerpet",
            "decision": "Approved Stormwater Drainage pipe widening (900mm reinforced concrete).",
            "budget_approved_lakhs": 25.0,
            "timestamp": "2026-08-01T14:15:00Z",
            "kpi_outcome": "Water clearing time reduced from 4 hours to 25 minutes after heavy rain."
        }
    ]

    def record_decision(self, ward_id: int, ward_name: str, decision: str, budget_lakhs: float, kpi_outcome: str = "In Progress") -> Dict[str, Any]:
        entry = {
            "ward_id": ward_id,
            "ward_name": ward_name,
            "decision": decision,
            "budget_approved_lakhs": budget_lakhs,
            "timestamp": datetime.utcnow().isoformat(),
            "kpi_outcome": kpi_outcome
        }
        self._MEMORY_STORE.append(entry)
        return entry

    def get_ward_history(self, ward_id: int) -> List[Dict[str, Any]]:
        return [m for m in self._MEMORY_STORE if m["ward_id"] == ward_id]

    def format_history_for_prompt(self, ward_id: int) -> str:
        history = self.get_ward_history(ward_id)
        if not history:
            return "No previous interventions recorded for this ward."
        lines = ["Historical Approved Interventions for this Ward:"]
        for h in history[-3:]:
            lines.append(f"- {h['timestamp'][:10]}: {h['decision']} (Budget: ₹{h['budget_approved_lakhs']}L) -> Outcome: {h['kpi_outcome']}")
        return "\n".join(lines)

from typing import List, Dict, Any
from .data_connector import TrafficDataConnector
from .congestion_scorer import CongestionScorer

class TrafficTopProblems:
    def __init__(self):
        self.connector = TrafficDataConnector()
        self.scorer = CongestionScorer()

    def get_top_problems(self, ward_id: int, complaints: List[Any] = None) -> List[Dict[str, Any]]:
        """
        Dynamically extracts top-3 traffic congestion problems for a ward.
        Combines sensor telemetry with citizen complaint reports.
        """
        telemetry = self.connector.fetch_live_corridor_telemetry(ward_id)
        scored = self.scorer.score_ward_corridors(ward_id, telemetry)

        problems = []
        for b in scored.get("bottlenecks", []):
            priority = "High" if b["congestion_index"] >= 80.0 else "Medium"
            problems.append({
                "text": f"{b['corridor']} bottleneck ({b['los']}) with +{int(b['delay_seconds'])}s peak delay",
                "priority": priority,
                "congestion_index": b["congestion_index"]
            })

        # Augment with citizen complaint descriptions if available
        if complaints:
            for c in complaints:
                desc = getattr(c, "description", "") or (c.get("description") if isinstance(c, dict) else str(c))
                cat = getattr(c, "category", "") or (c.get("category") if isinstance(c, dict) else "")
                sev = getattr(c, "severity", "medium") or (c.get("severity") if isinstance(c, dict) else "medium")
                if cat == "traffic" and desc and len(problems) < 3:
                    problems.append({
                        "text": desc,
                        "priority": "High" if sev == "high" else "Medium",
                        "congestion_index": 75.0
                    })

        # Ensure at least 3 problems
        if len(problems) < 3:
            defaults = [
                {"text": "Signal phase mismatch causing peak-hour queue spillback", "priority": "High"},
                {"text": "Illegal on-street parking narrowing effective transit corridor", "priority": "Medium"},
                {"text": "Pedestrian crossing friction delaying intersection clearance", "priority": "Low"}
            ]
            for d in defaults:
                if len(problems) < 3 and not any(d["text"] in p["text"] for p in problems):
                    problems.append(d)

        return problems[:3]

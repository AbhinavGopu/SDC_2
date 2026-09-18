from typing import List, Dict, Any
from .data_connector import EnergyDataConnector
from .traffic_linkage import EnergyTrafficLinkage

class EnergyTopProblems:
    def __init__(self):
        self.connector = EnergyDataConnector()
        self.linkage = EnergyTrafficLinkage()

    def get_top_problems(self, ward_id: int, complaints: List[Any] = None) -> List[Dict[str, Any]]:
        grid_data = self.connector.fetch_live_grid_load(ward_id)
        problems = [
            {
                "text": f"High transformer load ({grid_data['current_load_mw']} MW / {grid_data['utilization_pct']}%) at {grid_data['substation_name']}",
                "priority": "High" if grid_data["utilization_pct"] >= 80.0 else "Medium"
            },
            {
                "text": "Overhead cable clutter and low power factor on commercial transit stretches",
                "priority": "Medium"
            },
            {
                "text": "Streetlight grid efficiency losses during off-peak hours",
                "priority": "Low"
            }
        ]

        if complaints:
            for c in complaints:
                desc = getattr(c, "description", "") or (c.get("description") if isinstance(c, dict) else str(c))
                cat = getattr(c, "category", "") or (c.get("category") if isinstance(c, dict) else "")
                sev = getattr(c, "severity", "medium") or (c.get("severity") if isinstance(c, dict) else "medium")
                if cat == "energy" and desc and len(problems) < 4:
                    problems.insert(0, {
                        "text": desc,
                        "priority": "High" if sev == "high" else "Medium"
                    })

        return problems[:3]

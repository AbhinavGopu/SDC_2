from typing import List, Dict, Any
from .data_connector import PollutionDataConnector
from .traffic_linkage import PollutionTrafficLinkage

class PollutionTopProblems:
    def __init__(self):
        self.connector = PollutionDataConnector()
        self.linkage = PollutionTrafficLinkage()

    def get_top_problems(self, ward_id: int, complaints: List[Any] = None) -> List[Dict[str, Any]]:
        aqi_data = self.connector.fetch_live_aqi(ward_id)
        problems = [
            {
                "text": f"Elevated PM2.5 ({aqi_data['pm25']} µg/m³) near major transit corridor ({aqi_data['station']})",
                "priority": "High" if aqi_data["pm25"] > 70.0 else "Medium"
            },
            {
                "text": "Suspended road dust and commercial construction particulate matter",
                "priority": "Medium"
            },
            {
                "text": "Peak hour diesel emissions buildup under flyover grades",
                "priority": "Medium" if aqi_data["aqi"] > 140 else "Low"
            }
        ]

        if complaints:
            for c in complaints:
                desc = getattr(c, "description", "") or (c.get("description") if isinstance(c, dict) else str(c))
                cat = getattr(c, "category", "") or (c.get("category") if isinstance(c, dict) else "")
                sev = getattr(c, "severity", "medium") or (c.get("severity") if isinstance(c, dict) else "medium")
                if cat == "pollution" and desc and len(problems) < 4:
                    problems.insert(0, {
                        "text": desc,
                        "priority": "High" if sev == "high" else "Medium"
                    })

        return problems[:3]

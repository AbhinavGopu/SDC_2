from typing import Dict, Any, List

class CongestionScorer:
    """
    Computes road segment congestion index, Level of Service (LOS),
    and aggregates ward-level traffic congestion scores.
    """

    @staticmethod
    def calculate_congestion_index(actual_travel_time: float, free_flow_time: float) -> float:
        """
        CI = ((T_actual - T_freeflow) / T_freeflow) * 100
        Returns percentage congestion index clamped between 0 and 100.
        """
        if free_flow_time <= 0:
            return 0.0
        ratio = (actual_travel_time - free_flow_time) / free_flow_time
        return max(0.0, min(100.0, ratio * 100.0))

    @staticmethod
    def determine_level_of_service(congestion_index: float) -> str:
        """Determines Highway Capacity Manual Level of Service (A through F)."""
        if congestion_index < 20.0:
            return "LOS A (Free Flow)"
        elif congestion_index < 40.0:
            return "LOS B (Stable Flow)"
        elif congestion_index < 60.0:
            return "LOS C (Moderate Delay)"
        elif congestion_index < 75.0:
            return "LOS D (Heavy Traffic)"
        elif congestion_index < 85.0:
            return "LOS E (Severe Congestion)"
        else:
            return "LOS F (Forced Breakdown / Gridlock)"

    def score_ward_corridors(self, ward_id: int, segment_telemetry: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates segment congestion indexes to identify top bottleneck
        and overall ward congestion score.
        """
        if not segment_telemetry:
            return {
                "ward_id": ward_id,
                "overall_congestion_index": 50.0,
                "level_of_service": "LOS C (Moderate Delay)",
                "bottlenecks": []
            }

        scores = []
        bottlenecks = []
        for seg in segment_telemetry:
            actual = seg.get("actual_time_sec", 60.0)
            free = seg.get("free_flow_sec", 30.0)
            ci = self.calculate_congestion_index(actual, free)
            scores.append(ci)
            if ci >= 70.0:
                bottlenecks.append({
                    "corridor": seg.get("name", "Unknown Corridor"),
                    "congestion_index": round(ci, 1),
                    "los": self.determine_level_of_service(ci),
                    "delay_seconds": round(actual - free, 1)
                })

        avg_ci = sum(scores) / len(scores) if scores else 50.0
        bottlenecks.sort(key=lambda b: b["congestion_index"], reverse=True)

        return {
            "ward_id": ward_id,
            "overall_congestion_index": round(avg_ci, 1),
            "level_of_service": self.determine_level_of_service(avg_ci),
            "bottlenecks": bottlenecks[:3]
        }

from typing import Dict, Any

class PollutionTrafficLinkage:
    """
    Models the causal interaction between traffic congestion and roadside air pollution.
    Idle vehicles in Hyderabad bottlenecks produce up to 3x localized particulate matter.
    """

    @staticmethod
    def model_congestion_to_aqi(congestion_index: float, baseline_pm25: float) -> Dict[str, Any]:
        """
        Estimates the portion of PM2.5 attributable to vehicular traffic congestion.
        """
        # Approximately 40-55% of roadside PM2.5 in Hyderabad is vehicular
        vehicular_contribution_pct = 45.0
        # High congestion (CI > 70%) increases local idling emission multiplier by 1.35x
        idling_factor = 1.0 + max(0.0, (congestion_index - 50.0) / 100.0) * 0.7
        attributable_pm25 = round(baseline_pm25 * (vehicular_contribution_pct / 100.0) * (idling_factor - 1.0), 1)

        return {
            "congestion_index": congestion_index,
            "baseline_pm25": baseline_pm25,
            "congestion_induced_pm25_excess": max(0.0, attributable_pm25),
            "potential_pm25_reduction_on_traffic_fix": round(max(0.0, attributable_pm25) * 0.75, 1)
        }

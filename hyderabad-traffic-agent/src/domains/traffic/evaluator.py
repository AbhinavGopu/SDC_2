from typing import Dict, Any

class TrafficEvaluator:
    """
    Evaluates traffic intervention KPIs: Travel Time Savings,
    Delay Reduction, Fuel Waste Savings, and Benefit-Cost Ratio (BCR).
    """

    @staticmethod
    def evaluate_intervention_impact(
        daily_vehicle_volume: int,
        delay_reduction_pct: float,
        intervention_cost_lakhs: float,
        project_lifetime_years: int = 5
    ) -> Dict[str, Any]:
        """
        Computes traffic, economic, and environmental impact KPIs.
        """
        # Baseline average delay per vehicle: ~12 minutes (0.20 hrs)
        baseline_delay_hrs = 0.20
        hours_saved_per_veh = baseline_delay_hrs * (delay_reduction_pct / 100.0)
        daily_hours_saved = daily_vehicle_volume * hours_saved_per_veh

        # Value of time (INR 250/hour for urban commuter in Hyderabad)
        val_of_time_per_hr = 250.0
        annual_time_value_inr = daily_hours_saved * 300 * val_of_time_per_hr
        annual_time_value_lakhs = annual_time_value_inr / 100000.0

        # Fuel savings: Idling car wastes ~0.6 L/hour
        daily_fuel_saved_liters = daily_hours_saved * 0.6
        annual_fuel_saved_liters = daily_fuel_saved_liters * 300
        # Fuel cost: ~INR 110/L in Hyderabad
        annual_fuel_cost_saved_lakhs = (annual_fuel_saved_liters * 110.0) / 100000.0

        # CO2 emissions reduction: ~2.31 kg CO2 per liter petrol/diesel
        annual_co2_saved_tons = (annual_fuel_saved_liters * 2.31) / 1000.0

        # Benefit-to-Cost Ratio (BCR)
        total_benefits_lakhs = (annual_time_value_lakhs + annual_fuel_cost_saved_lakhs) * project_lifetime_years
        cost_lakhs = max(intervention_cost_lakhs, 1.0)
        bcr = round(total_benefits_lakhs / cost_lakhs, 2)

        return {
            "delay_reduction_pct": delay_reduction_pct,
            "daily_commuter_hours_saved": round(daily_hours_saved, 1),
            "annual_economic_benefit_lakhs": round(annual_time_value_lakhs + annual_fuel_cost_saved_lakhs, 2),
            "annual_fuel_saved_liters": round(annual_fuel_saved_liters, 0),
            "annual_co2_reduction_tons": round(annual_co2_saved_tons, 1),
            "benefit_cost_ratio": bcr,
            "feasibility_assessment": "Economically Highly Viable (BCR > 3.0)" if bcr >= 3.0 else "Viable"
        }

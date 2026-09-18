from typing import Dict, Any

class EnergyTrafficLinkage:
    """
    Models fuel energy waste due to vehicle congestion and potential
    grid optimization opportunities (smart street lighting and EV charging load).
    """

    @staticmethod
    def calculate_congestion_energy_waste(daily_vehicle_count: int, congestion_index: float) -> Dict[str, Any]:
        """
        Idling car consumes ~0.6 L/hr. 1 Liter of gasoline contains ~8.9 kWh of thermal energy.
        """
        # Average delay hours per vehicle
        delay_hrs_per_veh = max(0.0, (congestion_index / 100.0) * 0.3)
        daily_fuel_waste_liters = daily_vehicle_count * delay_hrs_per_veh * 0.6
        daily_energy_waste_mwh = (daily_fuel_waste_liters * 8.9) / 1000.0

        return {
            "daily_fuel_waste_liters": round(daily_fuel_waste_liters, 1),
            "daily_energy_waste_mwh": round(daily_energy_waste_mwh, 2),
            "daily_cost_waste_inr": round(daily_fuel_waste_liters * 110.0, 0),
            "co2_emissions_kg": round(daily_fuel_waste_liters * 2.31, 1)
        }

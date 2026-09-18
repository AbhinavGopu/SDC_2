class WideningFlyoverAdvisor:
    def check_feasibility(self, growth_forecast: float = 1.05, right_of_way_width: float = 24.0) -> dict:
        """
        Stage 2: Road widening & flyovers feasibility checks
        """
        widening_feasible = right_of_way_width < 30.0
        flyover_feasible = growth_forecast > 1.10
        return {
            "widening_feasible": widening_feasible,
            "flyover_feasible": flyover_feasible
        }

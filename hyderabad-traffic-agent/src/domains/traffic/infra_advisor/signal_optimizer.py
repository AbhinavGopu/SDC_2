class SignalOptimizer:
    def optimize_cycle_lengths(self, junction_volumes: dict = None, geometry: dict = None) -> dict:
        """
        Stage 2: Generate candidate (Signal retiming)
        Webster's formula baseline: C = (1.5L + 5) / (1 - Y)
        """
        volumes = junction_volumes or {"north": 800, "south": 800, "east": 600, "west": 600}
        total_lost_time = 10.0
        critical_flow_sum = 0.65
        
        optimal_cycle = (1.5 * total_lost_time + 5.0) / (1.0 - critical_flow_sum)
        
        return {
            "optimal_cycle_length_seconds": round(optimal_cycle, 1),
            "phase_splits": {
                "north-south": round(optimal_cycle * 0.55, 1),
                "east-west": round(optimal_cycle * 0.45, 1)
            },
            "algorithm": "Websters Baseline"
        }

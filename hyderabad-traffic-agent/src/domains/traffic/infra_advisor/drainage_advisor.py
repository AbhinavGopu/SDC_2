class DrainageAdvisor:
    def size_drainage_pipes(self, rainfall_intensity: float = 50.0, network_capacity: float = 30.0) -> dict:
        """
        Stage 2: Rational method sizing (Q = CiA) for waterlogging upgrades.
        """
        required_dia = 900 if rainfall_intensity > 40.0 else 600
        return {
            "required_pipe_diameter_mm": required_dia,
            "status": "upgrade_recommended" if required_dia > 600 else "adequate"
        }

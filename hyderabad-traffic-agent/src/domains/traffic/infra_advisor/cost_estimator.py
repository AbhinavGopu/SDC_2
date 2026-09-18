class CostEstimator:
    def __init__(self):
        # Base cost estimation rates in Lakhs INR
        self.rates = {
            "atsc": 45.0,
            "reroute": 10.0,
            "drainage": 25.0,
            "widening": 300.0,
            "flyover": 1500.0,
            "aqi_sprinklers": 12.0,
            "dust_barriers": 5.0,
            "transformer_capacitor": 28.0,
            "smart_lighting": 15.0
        }

    def estimate_cost(self, intervention_id: str, quantity: float = 1.0) -> float:
        """
        Stage 3: Estimates cost in Lakhs INR based on intervention type and quantity.
        """
        base_rate = self.rates.get(intervention_id, 10.0)
        return float(base_rate * quantity)

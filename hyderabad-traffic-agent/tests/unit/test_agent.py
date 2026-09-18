import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from src.db.models import Base, Ward, LocalityMetrics
from src.agent.constraint_parser import parse_constraints
from src.agent.core_agent import generate_recommendation

class AgentConstraintTest(unittest.TestCase):
    def test_parse_constraints(self):
        prompt = "Fix biodiversity bottleneck, budget limit ₹50 lakh, timeline within 5 days, no road closures"
        c = parse_constraints(prompt)
        self.assertEqual(c["budget"], 50.0)
        self.assertEqual(c["timeline_days"], 5)
        self.assertTrue(c["no_road_closures"])
        self.assertFalse(c["no_widening"])

    def test_parse_constraints_crore(self):
        prompt = "Major highway work, budget Rs 2 Crore, timeline 3 months, no widening"
        c = parse_constraints(prompt)
        self.assertEqual(c["budget"], 200.0)  # 2 Crores = 200 Lakhs
        self.assertEqual(c["timeline_days"], 90)
        self.assertTrue(c["no_widening"])

    def test_generate_recommendation(self):
        # Create a clean in-memory database for testing
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Seed a single ward
            ward = Ward(id=2, name="Gachibowli", ghmc_code="HYD-W2", description="Tech corridor", locality="Gachibowli")
            session.add(ward)
            
            metric = LocalityMetrics(
                ward_id=2,
                timestamp=datetime.now(timezone.utc),
                congestion_index=85.0,
                pm25=70.0,
                pm10=130.0,
                noise_db=70.0,
                energy_demand_mw=60.0,
                source="mock"
            )
            session.add(metric)
            session.commit()

            # Test traffic signal optimization (ATSC) which is cheaper than road widening
            prompt = "optimize traffic signals at biodiversity junction, budget 50 lakhs, no road closures"
            rec = generate_recommendation(2, prompt, session)
            self.assertIn("Adaptive Traffic Signal Control", rec)
            self.assertIn("Hyderabad Traffic Police", rec)
            self.assertIn("45.0 Lakhs", rec)

            # Test constraint conflict (budget too small)
            prompt = "fix waterlogging at biodiversity, budget under 5 lakhs"
            rec = generate_recommendation(2, prompt, session)
            self.assertIn("Constraint conflict", rec)
            self.assertIn("Alternative Recommendation", rec)

        finally:
            session.close()

if __name__ == "__main__":
    unittest.main()

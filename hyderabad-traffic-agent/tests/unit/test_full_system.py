import unittest
import json
from src.utils.geo_utils import is_point_in_hyderabad, point_in_polygon, match_coordinates_to_ward
from src.domains.traffic.simulation_engine import SumoSimulationEngine
from src.domains.traffic.congestion_scorer import CongestionScorer
from src.domains.traffic.top_problems import TrafficTopProblems
from src.domains.pollution.top_problems import PollutionTopProblems
from src.domains.energy.top_problems import EnergyTopProblems
from src.complaints.classifier import ComplaintClassifier
from src.complaints.ward_matcher import WardMatcher
from src.agent.planner import MultiAgentPlanner
from src.agent.tools import AgentTools

class FullSystemIntegrationTest(unittest.TestCase):

    def test_geo_point_in_polygon_and_bbox(self):
        # Hyderabad center (Charminar / Secretariat approx 17.38, 78.48)
        self.assertTrue(is_point_in_hyderabad(17.38, 78.48))
        # Delhi coordinates (should be False)
        self.assertFalse(is_point_in_hyderabad(28.61, 77.20))

        # Test point in square polygon
        poly = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        self.assertTrue(point_in_polygon(5, 5, poly))
        self.assertFalse(point_in_polygon(15, 15, poly))

        # Test Gachibowli coordinate (17.44, 78.35)
        ward = match_coordinates_to_ward(17.44, 78.35)
        if ward:
            self.assertEqual(ward.get("id"), 2)

    def test_sumo_simulation_engine(self):
        engine = SumoSimulationEngine()
        scenarios = engine.list_scenarios()
        self.assertGreaterEqual(len(scenarios), 3)

        # Run Biodiversity Junction simulation
        result = engine.run_simulation("biodiversity_junction", intervention_type="atsc", duration_frames=15)
        self.assertIn("comparison", result)
        self.assertIn("baseline_frames", result)
        self.assertIn("intervention_frames", result)

        comp = result["comparison"]
        # Delay reduction must be positive and significant
        self.assertGreater(comp["delay_reduction_pct"], 10.0)
        self.assertGreater(comp["speed_gain_pct"], 10.0)

        # Check vehicle trajectories in frame 0
        frame_0 = result["intervention_frames"][0]
        self.assertIn("signals", frame_0)
        self.assertIn("vehicles", frame_0)
        self.assertGreater(len(frame_0["vehicles"]), 0)

    def test_congestion_scorer(self):
        scorer = CongestionScorer()
        # Actual: 120s, Free flow: 40s -> CI = 200% clamped to 100%
        ci_high = scorer.calculate_congestion_index(120, 40)
        self.assertEqual(ci_high, 100.0)

        los = scorer.determine_level_of_service(85.0)
        self.assertIn("LOS F", los)

        # Free flow
        ci_low = scorer.calculate_congestion_index(30, 30)
        self.assertEqual(ci_low, 0.0)
        self.assertIn("LOS A", scorer.determine_level_of_service(0.0))

    def test_complaint_classifier(self):
        classifier = ComplaintClassifier()
        res_water = classifier.classify_complaint("Severe waterlogging and overflow on Ameerpet main road")
        self.assertEqual(res_water["category"], "traffic")
        self.assertEqual(res_water["severity"], "high")
        self.assertEqual(res_water["inferred_ward_id"], 1) # Ameerpet
        self.assertIn("Water Board", res_water["responsible_authority"])

        res_pollution = classifier.classify_complaint("Excessive construction dust and high smoke in Madhapur")
        self.assertEqual(res_pollution["category"], "pollution")
        self.assertEqual(res_pollution["inferred_ward_id"], 5) # Madhapur
        self.assertIn("TSPCB", res_pollution["responsible_authority"])

    def test_ward_matcher(self):
        matcher = WardMatcher()
        # Landmark test
        res_landmark = matcher.resolve_ward(location_text="Bio-diversity junction bottleneck")
        self.assertEqual(res_landmark["ward_id"], 2) # Gachibowli
        self.assertEqual(res_landmark["match_method"], "LANDMARK_TEXT_MATCH")

    def test_dynamic_domain_top_problems(self):
        traffic_prob = TrafficTopProblems().get_top_problems(ward_id=2)
        self.assertEqual(len(traffic_prob), 3)

        pollution_prob = PollutionTopProblems().get_top_problems(ward_id=2)
        self.assertEqual(len(pollution_prob), 3)

        energy_prob = EnergyTopProblems().get_top_problems(ward_id=2)
        self.assertEqual(len(energy_prob), 3)

    def test_multi_agent_planner_assessment(self):
        planner = MultiAgentPlanner()
        candidate = {
            "id": "atsc",
            "name": "Adaptive Traffic Signal Control (ATSC)",
            "cost_lakhs": 45.0,
            "time_days": 10
        }
        constraints = {"budget": 50.0, "timeline_days": 30}
        eval_result = planner.run_multi_agent_assessment(2, "Fix signal", constraints, candidate)

        self.assertTrue(eval_result["is_recommended"])
        self.assertGreater(eval_result["consensus_score"], 75.0)
        self.assertIn("traffic_specialist", eval_result["specialist_evaluations"])
        self.assertIn("environmental_specialist", eval_result["specialist_evaluations"])


if __name__ == "__main__":
    unittest.main()

import unittest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from src.db.models import Base, Ward, LocalityMetrics, Complaint, KnowledgeDocument
from src.rag.vector_db import VectorDBWrapper
from src.rag.ingestion import ingest_text_document, get_embedding
from src.rag.retriever import retrieve_context, format_context_for_prompt
from src.agent.core_agent import generate_recommendation


class RAGAndRulesTest(unittest.TestCase):
    def setUp(self):
        # Clean in-memory DB for every test
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Seed initial Ward
        self.ward = Ward(
            id=1,
            name="Gachibowli",
            ghmc_code="HYD-W2",
            description="Large tech corridor.",
            locality="Gachibowli"
        )
        self.session.add(self.ward)

        # Seed initial metrics
        self.metrics = LocalityMetrics(
            ward_id=1,
            timestamp=datetime.now(timezone.utc),
            congestion_index=82.0,
            pm25=75.0,
            energy_demand_mw=60.0
        )
        self.session.add(self.metrics)

        # Seed complaints with mock embeddings
        # Description: "Severe waterlogging at Gachibowli junction"
        emb_water = get_embedding("Severe waterlogging at Gachibowli junction")
        self.comp_water = Complaint(
            id=101,
            citizen_email="citizen@hyd.local",
            locality="Gachibowli",
            description="Severe waterlogging at Gachibowli junction",
            category="traffic",
            severity="high",
            ward_id=1,
            status="open",
            created_at=datetime.now(timezone.utc),
            embedding=json.dumps(emb_water)
        )
        
        # Description: "Junction signal timing is mismatched"
        emb_signal = get_embedding("Junction signal timing is mismatched")
        self.comp_signal = Complaint(
            id=102,
            citizen_email="citizen2@hyd.local",
            locality="Gachibowli",
            description="Junction signal timing is mismatched causing queues",
            category="traffic",
            severity="medium",
            ward_id=1,
            status="open",
            created_at=datetime.now(timezone.utc),
            embedding=json.dumps(emb_signal)
        )
        self.session.add_all([self.comp_water, self.comp_signal])

        # Ingest a knowledge document
        ingest_text_document(
            title="HMWSSB Drainage Guide",
            content="HMWSSB Drainage Guidelines: Waterlogging fixes require drainage network upgrades (pipelines >= 900mm diameter). Standard implementation costs 25 Lakhs INR, takes 14 days, and requires temporary road closures.",
            category="traffic",
            db=self.session
        )
        
        ingest_text_document(
            title="ATSC Signal Timing split guidelines",
            content="ATSC guidelines: Deployment at major junctions improves signal timing splits. Implementation costs 45 Lakhs, takes 10 days, and requires zero road closures.",
            category="traffic",
            db=self.session
        )

        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_vector_db_similarity_search(self):
        # Query: "drainage waterlogging pipelines"
        query_emb = get_embedding("drainage waterlogging pipelines")
        docs = VectorDBWrapper.similarity_search_documents(self.session, query_emb, limit=1)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].title, "HMWSSB Drainage Guide")

        # Query: "signal queue"
        query_emb_sig = get_embedding("signal queue")
        complaints = VectorDBWrapper.similarity_search_complaints(self.session, query_emb_sig, limit=1)
        self.assertEqual(len(complaints), 1)
        self.assertIn("signal timing", complaints[0].description)

    def test_rag_context_retriever(self):
        retrieved = retrieve_context("need waterlogging drainage upgrade", self.session, limit=1)
        self.assertIn("HMWSSB Drainage Guide", [d.title for d in retrieved["documents"]])
        self.assertTrue(any("Severe waterlogging" in c.description for c in retrieved["complaints"]))

        formatted = format_context_for_prompt(retrieved)
        self.assertIn("HMWSSB Drainage Guide", formatted)
        self.assertIn("Severe waterlogging", formatted)

    def test_generate_recommendation_waterlogging(self):
        # Test that waterlogging complaint results in drainage proposal, with pipe size calculated, and routed to HMWSSB
        prompt = "Fix waterlogging at Gachibowli, budget 30 lakhs, timeline 20 days"
        rec = generate_recommendation(1, prompt, self.session)
        
        self.assertIn("Stormwater drainage upgrade", rec)
        self.assertIn("HMWSSB (Water Board)", rec)
        self.assertIn("Required pipe size: 900mm", rec)  # drainage advisor pipe size calculation check

    def test_generate_recommendation_signal_timing(self):
        # Test signal retiming selection, with Webster optimal cycle calculated, and routed to Hyderabad Traffic Police
        prompt = "Optimize signal timing splits, budget 50 lakhs, no road closures"
        rec = generate_recommendation(1, prompt, self.session)
        
        self.assertIn("Adaptive Traffic Signal Control", rec)
        self.assertIn("Hyderabad Traffic Police", rec)
        self.assertIn("Webster Optimal Cycle", rec)  # Webster cycle length calculation check

    def test_generate_recommendation_constraint_conflict(self):
        # Test constraint conflict check
        prompt = "Fix waterlogging at Gachibowli, budget 5 lakhs"
        rec = generate_recommendation(1, prompt, self.session)
        self.assertIn("Constraint conflict", rec)
        self.assertIn("Alternative Recommendation", rec)

    def test_constraint_parsing_robustness(self):
        from src.agent.constraint_parser import parse_constraints
        
        # Test connects and plurals
        c1 = parse_constraints("budget is 40 lakhs")
        self.assertEqual(c1["budget"], 40.0)

        c2 = parse_constraints("make it so that the time taken is not over 6 months")
        self.assertEqual(c2["timeline_days"], 180)

    def test_location_proper_noun_disambiguation(self):
        # The exact query the user ran on the frontend:
        prompt = "budget is 40 lakhs what can I do with this to solve Persistent waterlogging on the Ameerpet flyover"
        
        # Run recommendation
        rec = generate_recommendation(1, prompt, self.session)
        
        # Verify it proposed drainage, NOT the flyover!
        self.assertIn("Stormwater drainage upgrade", rec)
        self.assertIn("HMWSSB (Water Board)", rec)
        self.assertIn("Intervention Proposed**: Stormwater drainage upgrade", rec)
        self.assertNotIn("Intervention Proposed**: Grade-separated flyover", rec)
        self.assertIn("Grade-separated flyover construction", rec) # Recorded in the failed audit log


if __name__ == "__main__":
    unittest.main()


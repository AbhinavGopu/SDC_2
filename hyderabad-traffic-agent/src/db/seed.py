import json
import hashlib
from datetime import datetime, timedelta
from src.db.db import engine, SessionLocal
from src.db.models import Base, Ward, LocalityMetrics, Complaint, KnowledgeDocument
from src.rag.ingestion import get_embedding as generate_mock_embedding



def seed_hyderabad_data():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        is_sqlite_db = str(session.bind.url).startswith("sqlite")

        wards = [
            {"id": 1, "name": "Ameerpet", "ghmc_code": "HYD-W1", "description": "Core IT and residential ward.", "locality": "Ameerpet"},
            {"id": 2, "name": "Gachibowli", "ghmc_code": "HYD-W2", "description": "Large tech corridor with frequent peak-hour congestion.", "locality": "Gachibowli"},
            {"id": 3, "name": "Kukatpally", "ghmc_code": "HYD-W3", "description": "Busy suburban ward with mixed traffic.", "locality": "Kukatpally"},
            {"id": 4, "name": "Secunderabad", "ghmc_code": "HYD-W4", "description": "Key transit hub and civic center.", "locality": "Secunderabad"},
            {"id": 5, "name": "Madhapur", "ghmc_code": "HYD-W5", "description": "Major IT/ITES hub, high office-goer traffic.", "locality": "Madhapur"},
            {"id": 6, "name": "Banjara Hills", "ghmc_code": "HYD-W6", "description": "Upscale commercial and residential area with steep terrain.", "locality": "Banjara Hills"},
            {"id": 7, "name": "Jubilee Hills", "ghmc_code": "HYD-W7", "description": "Premium residential and commercial zone with high vehicle density.", "locality": "Jubilee Hills"},
            {"id": 8, "name": "Begumpet", "ghmc_code": "HYD-W8", "description": "Commercial and residential hub, old airport area.", "locality": "Begumpet"},
            {"id": 9, "name": "Uppal", "ghmc_code": "HYD-W9", "description": "Key eastern gateway hub with metro terminal.", "locality": "Uppal"},
            {"id": 10, "name": "Dilsukhnagar", "ghmc_code": "HYD-W10", "description": "Densely populated educational and commercial hub.", "locality": "Dilsukhnagar"},
        ]
        existing_names = {ward.name for ward in session.query(Ward).all()}
        for ward_data in wards:
            if ward_data["name"] not in existing_names:
                session.add(Ward(**ward_data))

        now = datetime.utcnow()
        metric_rows = [
            {"ward_id": 1, "timestamp": now - timedelta(hours=1), "congestion_index": 72.4, "pm25": 68.0, "pm10": 120.5, "noise_db": 68.0, "energy_demand_mw": 56.2, "source": "mock"},
            {"ward_id": 2, "timestamp": now - timedelta(hours=1), "congestion_index": 81.7, "pm25": 72.1, "pm10": 132.0, "noise_db": 72.2, "energy_demand_mw": 63.4, "source": "mock"},
            {"ward_id": 3, "timestamp": now - timedelta(hours=1), "congestion_index": 66.3, "pm25": 60.8, "pm10": 110.2, "noise_db": 64.0, "energy_demand_mw": 49.8, "source": "mock"},
            {"ward_id": 4, "timestamp": now - timedelta(hours=1), "congestion_index": 69.0, "pm25": 69.4, "pm10": 125.6, "noise_db": 70.1, "energy_demand_mw": 58.9, "source": "mock"},
            {"ward_id": 5, "timestamp": now - timedelta(hours=1), "congestion_index": 83.5, "pm25": 75.4, "pm10": 138.2, "noise_db": 73.5, "energy_demand_mw": 68.7, "source": "mock"},
            {"ward_id": 6, "timestamp": now - timedelta(hours=1), "congestion_index": 75.1, "pm25": 58.3, "pm10": 108.4, "noise_db": 69.2, "energy_demand_mw": 52.1, "source": "mock"},
            {"ward_id": 7, "timestamp": now - timedelta(hours=1), "congestion_index": 78.2, "pm25": 59.1, "pm10": 112.5, "noise_db": 71.0, "energy_demand_mw": 55.4, "source": "mock"},
            {"ward_id": 8, "timestamp": now - timedelta(hours=1), "congestion_index": 70.8, "pm25": 66.7, "pm10": 122.1, "noise_db": 67.8, "energy_demand_mw": 50.5, "source": "mock"},
            {"ward_id": 9, "timestamp": now - timedelta(hours=1), "congestion_index": 68.5, "pm25": 65.2, "pm10": 118.9, "noise_db": 66.5, "energy_demand_mw": 48.2, "source": "mock"},
            {"ward_id": 10, "timestamp": now - timedelta(hours=1), "congestion_index": 79.4, "pm25": 73.8, "pm10": 135.0, "noise_db": 72.8, "energy_demand_mw": 57.6, "source": "mock"},
        ]
        existing_metrics = {(m.ward_id, m.timestamp) for m in session.query(LocalityMetrics).all()}
        for metric in metric_rows:
            if (metric["ward_id"], metric["timestamp"]) not in existing_metrics:
                session.add(LocalityMetrics(**metric))

        complaint_rows = [
            {"citizen_email": "citizen1@hyderabad.local", "citizen_name": "Ameerpet Resident", "locality": "Ameerpet", "description": "Persistent waterlogging on the Ameerpet flyover causes traffic jam.", "category": "traffic", "severity": "high", "ward_id": 1, "status": "open", "created_at": now - timedelta(hours=4)},
            {"citizen_email": "citizen2@hyderabad.local", "citizen_name": "Gachibowli commuter", "locality": "Gachibowli", "description": "Heavy dust and PM2.5 near Gachibowli road during evening rush hour.", "category": "pollution", "severity": "medium", "ward_id": 2, "status": "open", "created_at": now - timedelta(hours=6)},
            {"citizen_email": "citizen3@hyderabad.local", "citizen_name": "Kukatpally Local", "locality": "Kukatpally", "description": "Waterlogging near Kukatpally Metro station causing service road delays.", "category": "traffic", "severity": "high", "ward_id": 3, "status": "open", "created_at": now - timedelta(hours=5)},
            {"citizen_email": "citizen4@hyderabad.local", "citizen_name": "Secunderabad Citizen", "locality": "Secunderabad", "description": "Pedestrian congestion near railway station exit blocking autos.", "category": "traffic", "severity": "medium", "ward_id": 4, "status": "open", "created_at": now - timedelta(hours=3)},
            {"citizen_email": "citizen5@hyderabad.local", "citizen_name": "Madhapur IT Employee", "locality": "Madhapur", "description": "Severe traffic block near Cyber Towers during peak hours.", "category": "traffic", "severity": "high", "ward_id": 5, "status": "open", "created_at": now - timedelta(hours=2)},
            {"citizen_email": "citizen6@hyderabad.local", "citizen_name": "Banjara Hills Resident", "locality": "Banjara Hills", "description": "Road surface damage on Road No. 12 causing slow traffic and safety issues.", "category": "traffic", "severity": "medium", "ward_id": 6, "status": "open", "created_at": now - timedelta(hours=7)},
            {"citizen_email": "citizen7@hyderabad.local", "citizen_name": "Jubilee Hills Local", "locality": "Jubilee Hills", "description": "High energy demand causing transformer heating and noise.", "category": "energy", "severity": "medium", "ward_id": 7, "status": "open", "created_at": now - timedelta(hours=8)},
            {"citizen_email": "citizen8@hyderabad.local", "citizen_name": "Begumpet Business Owner", "locality": "Begumpet", "description": "Traffic backlog near Begumpet bridge due to narrow lanes.", "category": "traffic", "severity": "medium", "ward_id": 8, "status": "open", "created_at": now - timedelta(hours=4)},
            {"citizen_email": "citizen9@hyderabad.local", "citizen_name": "Uppal Commuter", "locality": "Uppal", "description": "Streetlight outages along Metro corridor leading to unsafe driving.", "category": "energy", "severity": "medium", "ward_id": 9, "status": "open", "created_at": now - timedelta(hours=3)},
            {"citizen_email": "citizen10@hyderabad.local", "citizen_name": "Dilsukhnagar Local", "locality": "Dilsukhnagar", "description": "Encroachments on footpaths forcing pedestrians onto the main road, causing slow movement.", "category": "traffic", "severity": "high", "ward_id": 10, "status": "open", "created_at": now - timedelta(hours=1)},
        ]
        
        existing_complaints = {c.description for c in session.query(Complaint).all()}
        for complaint_data in complaint_rows:
            if complaint_data["description"] not in existing_complaints:
                emb = generate_mock_embedding(complaint_data["description"])
                complaint_data["embedding"] = json.dumps(emb) if is_sqlite_db else emb
                session.add(Complaint(**complaint_data))

        # Seed Knowledge Documents
        knowledge_docs = [
            {
                "title": "GHMC Road Widening Guidelines",
                "content": "GHMC Road Widening Guidelines: Road widening in IT hubs (Gachibowli, Madhapur) requires a minimum right-of-way (ROW) clearance of 30 meters. Construction is estimated at 300 Lakhs INR (3 Crores) per km with a timeline of 120 days. Approvals must be routed to GHMC Engineering (Roads) Wing.",
                "category": "traffic"
            },
            {
                "title": "Hyderabad Traffic Control & ATSC Deployment Manual",
                "content": "Adaptive Traffic Signal Control (ATSC) deployment guidelines: Deployment at major junctions (e.g. Biodiversity Junction, Cyber Towers) improves signal timing splitting using camera-based feed. Implementation costs 45 Lakhs INR, takes 10 days, and requires zero road closures. Routed to Hyderabad Traffic Police.",
                "category": "traffic"
            },
            {
                "title": "IRC:93 Traffic Signal Timing and Webster Split Optimization",
                "content": "IRC:93 Guidelines for Traffic Signal Design: Optimal cycle length is computed via Webster's formula C_o = (1.5L + 5) / (1 - Y), where L is total lost time per cycle and Y is sum of critical flow ratios. For 4-phase Hyderabad junctions like Biodiversity, optimum cycle lengths range between 75s and 95s to minimize queue delay and spillback.",
                "category": "traffic"
            },
            {
                "title": "Hyderabad Traffic Police Corridor Rerouting Protocols",
                "content": "Hyderabad Traffic Police Dynamic Rerouting Protocol: When bottlenecks exceed Level of Service E, traffic is diverted across secondary parallel collector roads. Rerouting requires signage and traffic warden deployment, costing 8 Lakhs INR and taking 3 days.",
                "category": "traffic"
            },
            {
                "title": "Telangana Water Board Stormwater Drainage Standards",
                "content": "HMWSSB Drainage Standards: Waterlogging fixes require drainage network upgrades (pipelines >= 900mm diameter). Standard implementation costs 25 Lakhs INR, takes 14 days, and requires temporary road closures. Jointly routed to HMWSSB and GHMC Engineering.",
                "category": "traffic"
            },
            {
                "title": "TSPCB Air Pollution Mitigation Plan",
                "content": "TSPCB Air Pollution Mitigation Plan: PM2.5 reduction measures include water mist sprinklers and construction site dust barriers. Sprinkler installation costs 12 Lakhs INR, takes 5 days. Barrier enforcement costs 5 Lakhs, takes 2 days. Both route to TSPCB.",
                "category": "pollution"
            },
            {
                "title": "TSSPDCL Smart Grid and Streetlight Specifications",
                "content": "TSSPDCL Smart Grid Guidelines: Voltage drop mitigation requires capacitor bank installation at local distribution transformers (costs 28 Lakhs, takes 7 days). Streetlight conversions to Smart LEDs cost 15 Lakhs, take 4 days. Routed to TSSPDCL and GHMC Electrical.",
                "category": "energy"
            }
        ]

        existing_docs = {d.title for d in session.query(KnowledgeDocument).all()}
        for doc in knowledge_docs:
            if doc["title"] not in existing_docs:
                emb = generate_mock_embedding(doc["content"])
                doc["embedding"] = json.dumps(emb) if is_sqlite_db else emb
                doc["created_at"] = now
                session.add(KnowledgeDocument(**doc))

        session.commit()
    finally:
        session.close()


if __name__ == '__main__':
    seed_hyderabad_data()


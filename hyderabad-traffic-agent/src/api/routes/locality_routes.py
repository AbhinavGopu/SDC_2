from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from src.db.db import SessionLocal
from src.db.models import Ward, LocalityMetrics, Complaint
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class WardSummary(BaseModel):
    id: int
    name: str
    ghmc_code: str | None
    description: str | None
    locality: str | None

class MetricSummary(BaseModel):
    ward_id: int
    ward_name: str
    congestion_index: float
    pm25: float | None
    pm10: float | None
    noise_db: float | None
    energy_demand_mw: float | None
    timestamp: datetime

class LocalitySummaryResponse(BaseModel):
    total_wards: int
    average_congestion: float
    highest_congestion_ward: str
    latest_metrics: list[MetricSummary]

@router.get("/health")
def locality_health():
    return {"status": "locality route online"}

@router.get("/wards")
def list_wards():
    db = SessionLocal()
    try:
        wards = db.query(Ward).all()
        return [WardSummary(**{"id": w.id, "name": w.name, "ghmc_code": w.ghmc_code, "description": w.description, "locality": w.locality}) for w in wards]
    finally:
        db.close()

@router.get("/ward/{ward_id}")
def ward_summary(ward_id: int):
    db = SessionLocal()
    try:
        ward = db.query(Ward).filter(Ward.id == ward_id).one_or_none()
        if ward is None:
            raise HTTPException(status_code=404, detail="Ward not found")

        latest_metric = db.query(LocalityMetrics).filter(LocalityMetrics.ward_id == ward_id).order_by(LocalityMetrics.timestamp.desc()).first()
        complaint_count = db.query(func.count(Complaint.id)).filter(Complaint.ward_id == ward_id).scalar()
        return {
            "ward": WardSummary(**{"id": ward.id, "name": ward.name, "ghmc_code": ward.ghmc_code, "description": ward.description, "locality": ward.locality}),
            "latest_metric": latest_metric and MetricSummary(
                ward_id=latest_metric.ward_id,
                ward_name=ward.name,
                congestion_index=latest_metric.congestion_index,
                pm25=latest_metric.pm25,
                pm10=latest_metric.pm10,
                noise_db=latest_metric.noise_db,
                energy_demand_mw=latest_metric.energy_demand_mw,
                timestamp=latest_metric.timestamp,
            ),
            "open_complaints": complaint_count,
        }
    finally:
        db.close()

@router.get("/summary", response_model=LocalitySummaryResponse)
def locality_summary(locality: str | None = Query(default=None, description="Hyderabad locality name to filter by")):
    db = SessionLocal()
    try:
        query = db.query(Ward.id)
        if locality:
            query = query.filter(func.lower(Ward.locality) == locality.lower())
        ward_ids = [row.id for row in query.all()]
        if not ward_ids:
            raise HTTPException(status_code=404, detail="No wards found for the provided locality")

        latest_metrics = db.query(LocalityMetrics).filter(LocalityMetrics.ward_id.in_(ward_ids)).order_by(LocalityMetrics.timestamp.desc()).all()
        if not latest_metrics:
            raise HTTPException(status_code=404, detail="No metrics found for the selected locality")

        ward_map = {ward.id: ward.name for ward in db.query(Ward).filter(Ward.id.in_(ward_ids)).all()}
        avg_congestion = float(db.query(func.avg(LocalityMetrics.congestion_index)).filter(LocalityMetrics.ward_id.in_(ward_ids)).scalar())
        top_metric = max(latest_metrics, key=lambda m: m.congestion_index)

        response_metrics = [
            MetricSummary(
                ward_id=m.ward_id,
                ward_name=ward_map.get(m.ward_id, "Unknown"),
                congestion_index=m.congestion_index,
                pm25=m.pm25,
                pm10=m.pm10,
                noise_db=m.noise_db,
                energy_demand_mw=m.energy_demand_mw,
                timestamp=m.timestamp,
            )
            for m in latest_metrics
        ]

        return LocalitySummaryResponse(
            total_wards=len(ward_ids),
            average_congestion=avg_congestion,
            highest_congestion_ward=ward_map.get(top_metric.ward_id, "Unknown"),
            latest_metrics=response_metrics,
        )
    finally:
        db.close()

PREDEFINED_PROBLEMS = {
    1: {
        "Traffic": [
            {"text": "Persistent waterlogging on the Ameerpet flyover", "priority": "High"},
            {"text": "Metro station pedestrian bottleneck during rush hour", "priority": "High"},
            {"text": "Two-wheeler congestion on interior business lanes", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High noise levels under metro pillars", "priority": "High"},
            {"text": "Construction dust from commercial retail projects", "priority": "Medium"},
            {"text": "Exhaust gas accumulation at major traffic junctions", "priority": "Medium"}
        ],
        "Energy": [
            {"text": "Transformer overload near commercial market area", "priority": "High"},
            {"text": "Hanging overhead internet/power cables hazard", "priority": "High"},
            {"text": "Unscheduled maintenance outages in residential zone", "priority": "Medium"}
        ]
    },
    2: {
        "Traffic": [
            {"text": "Signal mistiming at Bio-diversity junction", "priority": "High"},
            {"text": "Peak-hour bottleneck on ORR service road", "priority": "Medium"},
            {"text": "Illegal parking reducing lane width, Nanakramguda", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High PM10 levels from IT corridor construction", "priority": "High"},
            {"text": "Dust pollution near Gachibowli stadium", "priority": "Medium"},
            {"text": "Diesel emissions from transit busses", "priority": "Low"}
        ],
        "Energy": [
            {"text": "Voltage fluctuations during peak IT park load", "priority": "High"},
            {"text": "Frequent power cuts near financial district", "priority": "Medium"},
            {"text": "Streetlight outages along ORR service road", "priority": "Low"}
        ]
    },
    3: {
        "Traffic": [
            {"text": "JNTU junction traffic bottleneck", "priority": "High"},
            {"text": "Encroachments on main commercial road margins", "priority": "Medium"},
            {"text": "Waterlogging near Kukatpally Metro station", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "Industrial emissions from Kukatpally IDAL zone", "priority": "High"},
            {"text": "High PM2.5 levels from heavy vehicular exhaust", "priority": "Medium"},
            {"text": "Noise pollution near retail hubs and malls", "priority": "Medium"}
        ],
        "Energy": [
            {"text": "Overloaded residential substation transformers", "priority": "High"},
            {"text": "Frequent power outages in older residential phases", "priority": "Medium"},
            {"text": "Defective street lights in residential blocks", "priority": "Low"}
        ]
    },
    4: {
        "Traffic": [
            {"text": "Station road heavy vehicle bottleneck", "priority": "High"},
            {"text": "Pedestrian congestion near railway station exit", "priority": "High"},
            {"text": "Unregulated auto-rickshaw parking bays", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High PM10 levels from railway terminal area", "priority": "High"},
            {"text": "Soot and coal dust from freight movements", "priority": "Medium"},
            {"text": "Traffic exhaust build-up under flyovers", "priority": "Medium"}
        ],
        "Energy": [
            {"text": "Old distribution infrastructure feeder failure", "priority": "High"},
            {"text": "Frequent cable cuts during municipal civic works", "priority": "High"},
            {"text": "Inefficient street lighting in public parks", "priority": "Low"}
        ]
    },
    5: {
        "Traffic": [
            {"text": "Severe traffic block near Cyber Towers during peak hours", "priority": "High"},
            {"text": "Junction gridlock near Hitec City Metro station", "priority": "High"},
            {"text": "Encroachments on service roads", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High PM2.5 levels from vehicular exhaust", "priority": "High"},
            {"text": "Construction dust from commercial projects", "priority": "Medium"},
            {"text": "Noise pollution from IT office construction", "priority": "Low"}
        ],
        "Energy": [
            {"text": "Frequent power cuts near IT parks", "priority": "High"},
            {"text": "Transformer overloading in commercial area", "priority": "Medium"},
            {"text": "Streetlight malfunctions in inner lanes", "priority": "Low"}
        ]
    },
    6: {
        "Traffic": [
            {"text": "Road surface damage on Road No. 12 causing slow traffic", "priority": "High"},
            {"text": "Peak hour congestion near Taj Krishna junction", "priority": "Medium"},
            {"text": "Narrow lanes causing bottlenecks in residential sectors", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High noise pollution from late-night commercial activity", "priority": "High"},
            {"text": "Dust pollution from renovation projects", "priority": "Medium"},
            {"text": "High exhaust fumes near main transit corridors", "priority": "Low"}
        ],
        "Energy": [
            {"text": "Power fluctuations in high-density commercial strips", "priority": "High"},
            {"text": "Old power poles needing shifting for safety", "priority": "Medium"},
            {"text": "Hanging cables near road crossings", "priority": "Low"}
        ]
    },
    7: {
        "Traffic": [
            {"text": "Gridlock near Road No. 36 junction during rush hours", "priority": "High"},
            {"text": "Unregulated parking outside cafes and lounges", "priority": "Medium"},
            {"text": "Steep slope traffic bottlenecks during rain", "priority": "Low"}
        ],
        "Pollution": [
            {"text": "Excessive noise levels from commercial nightlife", "priority": "High"},
            {"text": "Particulate matter accumulation near metro corridor", "priority": "Medium"},
            {"text": "Littering in public open spaces", "priority": "Low"}
        ],
        "Energy": [
            {"text": "High energy demand causing transformer heating", "priority": "High"},
            {"text": "Voltage drops in residential clusters", "priority": "Medium"},
            {"text": "Cable cuts due to municipal digging projects", "priority": "Low"}
        ]
    },
    8: {
        "Traffic": [
            {"text": "Traffic backlog near Begumpet bridge due to narrow lanes", "priority": "High"},
            {"text": "Waterlogging near railway underpass during monsoon", "priority": "High"},
            {"text": "Airport road junction bottleneck", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "Poor air quality near public metro corridor", "priority": "High"},
            {"text": "Dust pollution from road repairs", "priority": "Medium"},
            {"text": "Industrial particulate transport from nearby zones", "priority": "Low"}
        ],
        "Energy": [
            {"text": "Old distribution cables failing in monsoon", "priority": "High"},
            {"text": "Transformer overloading near commercial properties", "priority": "Medium"},
            {"text": "Inadequate lighting in pedestrian subways", "priority": "Low"}
        ]
    },
    9: {
        "Traffic": [
            {"text": "Heavy vehicle parking on Uppal main road reducing lane space", "priority": "High"},
            {"text": "Uppal Ring Road junction congestion during evening peak", "priority": "High"},
            {"text": "Encroachments near metro station entrances", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High dust and PM10 levels from heavy highway trucks", "priority": "High"},
            {"text": "Industrial emissions from Uppal IDA zone", "priority": "Medium"},
            {"text": "Noise pollution along the highway corridor", "priority": "Medium"}
        ],
        "Energy": [
            {"text": "Streetlight outages along Metro corridor", "priority": "High"},
            {"text": "Frequent power outages in industrial sector", "priority": "Medium"},
            {"text": "Voltage fluctuations in older colonies", "priority": "Low"}
        ]
    },
    10: {
        "Traffic": [
            {"text": "Encroachments on footpaths forcing pedestrians onto the main road", "priority": "High"},
            {"text": "Dilsukhnagar Bus Depot junction bottleneck", "priority": "High"},
            {"text": "U-turn congestion on main shopping street", "priority": "Medium"}
        ],
        "Pollution": [
            {"text": "High PM2.5 and PM10 from dense vehicular congestion", "priority": "High"},
            {"text": "Soot and black smoke from older transit buses", "priority": "Medium"},
            {"text": "High decibel noise near retail shopping complexes", "priority": "Medium"}
        ],
        "Energy": [
            {"text": "Transformer overload near retail markets", "priority": "High"},
            {"text": "Hanging cable hazards in dense commercial areas", "priority": "High"},
            {"text": "Frequent maintenance cuts in residential lanes", "priority": "Low"}
        ]
    }
}

from src.domains.traffic.top_problems import TrafficTopProblems
from src.domains.pollution.top_problems import PollutionTopProblems
from src.domains.energy.top_problems import EnergyTopProblems

traffic_problems_extractor = TrafficTopProblems()
pollution_problems_extractor = PollutionTopProblems()
energy_problems_extractor = EnergyTopProblems()

@router.get("/ward/{ward_id}/problems")
def list_ward_problems(ward_id: int):
    db = SessionLocal()
    try:
        db_complaints = db.query(Complaint).filter(Complaint.ward_id == ward_id, Complaint.status == "open").order_by(Complaint.created_at.desc()).all()
        
        traffic_probs = traffic_problems_extractor.get_top_problems(ward_id, db_complaints)
        pollution_probs = pollution_problems_extractor.get_top_problems(ward_id, db_complaints)
        energy_probs = energy_problems_extractor.get_top_problems(ward_id, db_complaints)
        
        return {
            "Traffic": traffic_probs,
            "Pollution": pollution_probs,
            "Energy": energy_probs
        }
    finally:
        db.close()


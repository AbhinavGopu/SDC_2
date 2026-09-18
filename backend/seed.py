import os, json, uuid
from pathlib import Path
from sqlalchemy import text
from .db import Base, engine, Session, User, Ward, Document, Observation
from .security import hash_password

ROOT = Path(__file__).resolve().parents[1]

def initialize():
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("ALTER TABLE wards ADD COLUMN IF NOT EXISTS geom geometry(Geometry,4326)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS wards_geom_idx ON wards USING gist(geom)"))
            conn.execute(text("CREATE TABLE IF NOT EXISTS document_vectors (document_id text PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE, embedding vector(1536), model text NOT NULL)"))
    with Session() as db:
        for role in ["citizen", "planner"]:
            email = role + "@demo.local"
            if not db.query(User).filter_by(email=email).first():
                db.add(User(id=str(uuid.uuid4()), email=email, password=hash_password(os.getenv("DEMO_PASSWORD", "CityDemo-2026!")), role=role, ward_id=1 if role == "planner" else None))
        for feature in json.loads((ROOT / "data/demo_wards.geojson").read_text())["features"]:
            p = feature["properties"]
            if not db.get(Ward, p["id"]):
                db.add(Ward(id=p["id"], name=p["name"], geometry=feature["geometry"], provenance=p["provenance"]))
        for d in json.loads((ROOT / "data/knowledge.json").read_text()):
            if not db.get(Document, d["id"]):
                db.add(Document(**d))
        for o in json.loads((ROOT / "data/simulated_observations.json").read_text()):
            if not db.get(Observation, o["id"]):
                db.add(Observation(**o))
        db.commit()
        if engine.dialect.name == "postgresql":
            db.execute(text("UPDATE wards SET geom = ST_SetSRID(ST_GeomFromGeoJSON(CAST(geometry AS text)),4326) WHERE geom IS NULL"))
            db.commit()

    historical = ROOT / "data/historical/rainfall.csv"
    if historical.exists():
        from .ingest import ingest
        ingest(historical, "Open-Meteo / Copernicus ERA5 historical gridded reanalysis; https://open-meteo.com/; grid 17.5N 78.5E, not a ward measurement", "CC BY 4.0; Open-Meteo and Copernicus ERA5 attribution")

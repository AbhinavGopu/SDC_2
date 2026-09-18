import csv, io, json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from shapely.geometry import Point, shape
from .db import get_db, engine, User, Ward, Complaint, Observation, Plan, Job, Audit
from .security import current_user, planner, own_ward, hash_password, verify_password, token
from .seed import initialize
from .rules import classify, AUTHORITIES, recommend
from .rag import advise
from .priority import complaint_priority
from .focused_advice import focused_options

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def record(row):
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in ("password",)}
    if isinstance(row, Complaint):
        data["priority"] = complaint_priority(row.description, row.status)
    return data

def redis_client():
    import redis
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=1, socket_timeout=2)

def notify(ward_id):
    try: redis_client().publish("ward:" + str(ward_id), "refresh")
    except Exception: pass  # durable database records remain available via polling

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="Hyderabad City Lab", version="1.0.0", lifespan=lifespan,
              description="Local planning demonstration. Bundled ward boundaries, estimates and sensor values are simulated.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:3001"],
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])

@app.get("/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    result = {"database": engine.dialect.name, "redis": False, "sumo_worker": False}
    try:
        r = redis_client()
        result.update(redis=bool(r.ping()), sumo_worker=bool(r.get("worker:heartbeat")))
    except Exception: pass
    return result

class Login(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=10, max_length=128)

@app.post("/auth/register", status_code=201)
def register(body: Login, db=Depends(get_db)):
    if "@" not in body.email: raise HTTPException(422, "A valid email is required")
    user = User(id=uid(), email=body.email.strip().lower(), password=hash_password(body.password), role="citizen")
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    return {"token": token(user), "user": record(user)}

@app.post("/auth/login")
def login(body: Login, db=Depends(get_db)):
    user = db.query(User).filter_by(email=body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": token(user), "user": record(user)}

@app.get("/auth/me")
def me(user=Depends(current_user)): return record(user)

@app.get("/wards")
def wards(q: str = "", user=Depends(current_user), db=Depends(get_db)):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": w.geometry, "properties": {"id": w.id, "name": w.name, "provenance": w.provenance}}
        for w in db.query(Ward).order_by(Ward.id).all() if q.lower() in w.name.lower()]}

def match_ward(db, lat, lon):
    if not 17.2 <= lat <= 17.6 or not 78.25 <= lon <= 78.65:
        raise HTTPException(422, "Coordinates are outside the Hyderabad study area")
    if db.bind.dialect.name == "postgresql":
        ward_id = db.execute(text("SELECT id FROM wards WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)) ORDER BY id LIMIT 1"), {"lon": lon, "lat": lat}).scalar()
        ward = db.get(Ward, ward_id) if ward_id else None
    else:
        ward = next((w for w in db.query(Ward).order_by(Ward.id) if shape(w.geometry).covers(Point(lon, lat))), None)
    if not ward: raise HTTPException(422, "No loaded ward covers that point. Demo polygons cover only three small areas; choose a point on the map.")
    return ward

class Intake(BaseModel):
    description: str = Field(min_length=10, max_length=4000)
    latitude: float = Field(ge=17.2, le=17.6, allow_inf_nan=False)
    longitude: float = Field(ge=78.25, le=78.65, allow_inf_nan=False)

@app.post("/complaints", status_code=201)
def intake(body: Intake, user=Depends(current_user), db=Depends(get_db)):
    if user.role != "citizen": raise HTTPException(403, "Citizen access required")
    ward = match_ward(db, body.latitude, body.longitude)
    category, issue = classify(body.description)
    complaint = Complaint(id=uid(), owner_id=user.id, ward_id=ward.id, description=body.description,
                          category=category, authority=AUTHORITIES[issue],
                          severity="high" if any(w in body.description.lower() for w in ["severe", "danger", "accident", "flood"]) else "normal",
                          latitude=body.latitude, longitude=body.longitude, created_at=now(),
                          analysis={"mode": "offline rules", "location": "citizen-confirmed coordinates",
                                    "routing_provenance": ward.provenance, "suggested_fix": "Inspect the reported location and verify conditions before intervention."})
    db.add(complaint); db.commit(); notify(ward.id)
    return record(complaint)

def accessible_complaint(db, complaint_id, user, write=False):
    c = db.get(Complaint, complaint_id)
    if not c: raise HTTPException(404, "Complaint not found")
    if user.role == "citizen" and c.owner_id != user.id: raise HTTPException(404, "Complaint not found")
    if user.role == "planner" and c.ward_id != user.ward_id: raise HTTPException(403, "Complaint details are restricted to assigned ward")
    return c

@app.get("/complaints")
def complaints(user=Depends(current_user), db=Depends(get_db)):
    query = db.query(Complaint)
    query = query.filter_by(owner_id=user.id) if user.role == "citizen" else query.filter_by(ward_id=user.ward_id)
    if user.role == "planner":
        rows = [record(c) for c in query.all()]
        rows.sort(key=lambda c: (c["priority"]["rank"], c["created_at"], c["id"]))
        return rows[:100]
    return [record(c) for c in query.order_by(Complaint.created_at.desc()).limit(100).all()]

@app.get("/complaints/{complaint_id}")
def complaint(complaint_id: str, user=Depends(current_user), db=Depends(get_db)):
    return record(accessible_complaint(db, complaint_id, user))

class Status(BaseModel):
    status: Literal["acknowledged", "in_progress", "resolved"]

@app.patch("/complaints/{complaint_id}")
def update_status(complaint_id: str, body: Status, user=Depends(planner), db=Depends(get_db)):
    c = accessible_complaint(db, complaint_id, user, True)
    transitions = {"received": ["acknowledged"], "acknowledged": ["in_progress"], "in_progress": ["resolved"], "resolved": []}
    if body.status not in transitions[c.status]: raise HTTPException(409, "Invalid status transition")
    c.status = body.status
    db.add(Audit(id=uid(), actor_id=user.id, ward_id=c.ward_id, action=body.status, target_id=c.id, created_at=now()))
    db.commit(); notify(c.ward_id)
    return record(c)

@app.post("/complaints/{complaint_id}/media", status_code=201)
async def upload(complaint_id: str, file: UploadFile = File(...), user=Depends(current_user), db=Depends(get_db)):
    c = accessible_complaint(db, complaint_id, user)
    if user.role != "citizen": raise HTTPException(403, "Only the reporting citizen may attach evidence")
    if len(c.media or []) >= 3: raise HTTPException(422, "Maximum three attachments")
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024: raise HTTPException(413, "Maximum attachment size is 10 MB")
    if raw.startswith(b"\xff\xd8\xff"): ext, mime = ".jpg", "image/jpeg"
    elif raw.startswith(b"\x89PNG\r\n\x1a\n"): ext, mime = ".png", "image/png"
    elif len(raw) > 12 and raw[4:8] == b"ftyp": ext, mime = ".mp4", "video/mp4"
    else: raise HTTPException(415, "Attach JPEG, PNG, or MP4 evidence")
    if mime.startswith("image/"):
        from PIL import Image
        try:
            with Image.open(io.BytesIO(raw)) as im: im.verify()
        except Exception: raise HTTPException(415, "Invalid image")
    media_id = uid() + ext
    directory = Path(os.getenv("MEDIA_DIR", "./artifacts/media")); directory.mkdir(parents=True, exist_ok=True)
    (directory / media_id).write_bytes(raw)
    c.media = list(c.media or []) + [{"id": media_id, "mime": mime, "analysis": "queued; no visual interpretation yet"}]
    job = Job(id=uid(), owner_id=user.id, ward_id=c.ward_id, status="queued",
              request={"kind": "media", "complaint_id": c.id, "media_id": media_id, "mime": mime}, created_at=now())
    db.add(job); db.commit()
    return {"media_id": media_id, "job_id": job.id}

@app.get("/complaints/{complaint_id}/media/{media_id}")
def download(complaint_id: str, media_id: str, user=Depends(current_user), db=Depends(get_db)):
    c = accessible_complaint(db, complaint_id, user)
    attachment = next((m for m in c.media or [] if m["id"] == media_id), None)
    if not attachment: raise HTTPException(404)
    return FileResponse(Path(os.getenv("MEDIA_DIR", "./artifacts/media")) / media_id, media_type=attachment["mime"])

@app.get("/wards/{ward_id}/overview")
def overview(ward_id: int, user=Depends(planner), db=Depends(get_db)):
    ward = db.get(Ward, ward_id)
    if not ward: raise HTTPException(404, "Ward not found")
    observations = db.query(Observation).filter_by(ward_id=ward_id).order_by(Observation.observed_at.desc(), Observation.id).all()
    latest = {}
    for o in observations: latest.setdefault((o.domain, o.metric, o.provenance), o)
    problems = {}
    for domain in ["traffic", "pollution", "energy"]:
        rows = [o for o in latest.values() if o.domain == domain]
        problems[domain] = [{"title": o.metric.replace("_", " "), "value": o.value, "unit": o.unit,
                             "source": o.source, "provenance": o.provenance, "observed_at": o.observed_at,
                             "note": "Indicator for review; no causal diagnosis established."} for o in rows[:3]]
    count = db.query(Complaint).filter(Complaint.ward_id == ward_id, Complaint.status != "resolved").count()
    return {"ward": record(ward), "read_only": ward_id != user.ward_id, "open_complaints": count,
            "problems": problems, "history": [record(o) for o in observations], "live_telemetry": False}

class Constraints(BaseModel):
    budget_lakhs: float = Field(default=50, ge=0, le=100000, allow_inf_nan=False)
    timeline_days: int = Field(default=90, ge=0, le=3650)
    available_row_m: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    no_construction: bool = True
    no_road_closures: bool = True
    preserve_bus: bool = True

class Advice(BaseModel):
    ward_id: int
    prompt: str = Field(default="", max_length=2000)
    constraints: Constraints = Field(default_factory=Constraints)

@app.post("/plans", status_code=201)
def create_plan(body: Advice, user=Depends(planner), db=Depends(get_db)):
    own_ward(user, body.ward_id)
    pending = db.query(Complaint).filter(Complaint.ward_id == body.ward_id, Complaint.status != "resolved").all()
    pending.sort(key=lambda c: (complaint_priority(c.description, c.status)["rank"], c.created_at, c.id))
    target = pending[0] if pending else None
    brief = body.prompt.strip()
    if not target and not brief:
        raise HTTPException(409, "No unresolved complaints in this ward. Enter a planning brief to review another issue.")
    result = recommend(brief, body.constraints.model_dump(), focused_options(target) if target else None)
    result["target_complaint"] = record(target) if target else None
    result["review_action"] = (complaint_priority(target.description, target.status)["review"] if target else "Review the planning brief")
    context = json.dumps({"planner_brief": brief, "highest_priority_complaint": {"id": target.id, "description": target.description, "priority": result["target_complaint"]["priority"], "source": "Unverified citizen report"} if target else None})
    result["rag"] = advise(db, context, result["candidates"])
    result["prompt"] = brief or "Address highest-priority complaint " + target.id
    result["limitations"].append("Recommendations do not resolve a complaint automatically; verify the action and update its status separately.")
    result["data_provenance"] = "simulated planning assumptions; no official live telemetry"
    plan = Plan(id=uid(), owner_id=user.id, ward_id=body.ward_id, result=result, status="proposed", created_at=now())
    db.add(plan); db.commit()
    return record(plan)

@app.get("/plans")
def plans(user=Depends(planner), db=Depends(get_db)):
    return [record(p) for p in db.query(Plan).filter_by(ward_id=user.ward_id).order_by(Plan.created_at.desc()).limit(100)]

@app.post("/plans/{plan_id}/approve")
def approve(plan_id: str, user=Depends(planner), db=Depends(get_db)):
    p = db.get(Plan, plan_id)
    if not p: raise HTTPException(404)
    own_ward(user, p.ward_id)
    if p.status != "proposed": raise HTTPException(409, "Plan already reviewed")
    if not p.result["candidates"]: raise HTTPException(409, "No eligible candidates to approve")
    p.status = "approved_for_review"
    db.add(Audit(id=uid(), actor_id=user.id, ward_id=p.ward_id, action="approved_for_review", target_id=p.id, created_at=now()))
    db.commit()
    return record(p)

class Simulation(BaseModel):
    ward_id: int
    seconds: int = Field(default=300, ge=60, le=900)
    seed: int = Field(default=42, ge=0, le=100000)
    green_seconds: int = Field(default=25, ge=10, le=90)

@app.post("/simulations", status_code=202)
def simulate(body: Simulation, user=Depends(planner), db=Depends(get_db)):
    own_ward(user, body.ward_id)
    try:
        if not redis_client().get("worker:heartbeat"): raise ValueError()
    except Exception: raise HTTPException(503, "SUMO worker unavailable; no simulated result has been fabricated")
    pending = db.query(Job).filter(Job.status.in_(["queued", "running"])).count()
    if pending >= 20: raise HTTPException(429, "Simulation queue is full")
    job = Job(id=uid(), owner_id=user.id, ward_id=body.ward_id, request=dict(body.model_dump(), kind="simulation"), status="queued", created_at=now())
    db.add(job); db.commit()
    return record(job)

@app.get("/jobs/{job_id}")
def job(job_id: str, user=Depends(current_user), db=Depends(get_db)):
    j = db.get(Job, job_id)
    if not j or (j.owner_id != user.id and not (user.role == "planner" and user.ward_id == j.ward_id)):
        raise HTTPException(404)
    return record(j)

@app.get("/audit")
def audit(user=Depends(planner), db=Depends(get_db)):
    return [record(a) for a in db.query(Audit).filter_by(ward_id=user.ward_id).order_by(Audit.created_at.desc()).limit(100)]

@app.get("/wards/{ward_id}/export")
def export(ward_id: int, user=Depends(planner), db=Depends(get_db)):
    stream = io.StringIO()
    rows = db.query(Observation).filter_by(ward_id=ward_id).order_by(Observation.observed_at, Observation.id).all()
    writer = csv.DictWriter(stream, fieldnames=[c.name for c in Observation.__table__.columns])
    writer.writeheader()
    for row in rows: writer.writerow(record(row))
    return Response(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="ward-{ward_id}-observations.csv"'})

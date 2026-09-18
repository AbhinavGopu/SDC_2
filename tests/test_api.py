import io, uuid
from PIL import Image
from conftest import auth
from backend.rules import recommend
from backend.main import Constraints

def report(client, headers, lat=17.435, lon=78.445):
    return client.post("/complaints", headers=headers, json={"description":"Severe waterlogging near the junction", "latitude":lat, "longitude":lon})

def test_auth_rbac_and_ownership(client):
    assert client.get("/complaints").status_code in (401,403)
    citizen, planner = auth(client,"citizen"), auth(client,"planner")
    assert client.get("/wards/1/overview",headers=citizen).status_code == 403
    r = report(client,citizen); assert r.status_code == 201
    item = r.json()
    assert item["ward_id"] == 1 and item["category"] == "traffic"
    assert "simulated" in item["analysis"]["routing_provenance"]
    other = client.post("/auth/register",json={"email":"other@demo.local","password":"AnotherPassword1!"}).json()
    assert client.get("/complaints/"+item["id"],headers={"Authorization":"Bearer "+other["token"]}).status_code == 404
    assert client.patch("/complaints/"+item["id"],headers=citizen,json={"status":"resolved"}).status_code == 403
    assert client.patch("/complaints/"+item["id"],headers=planner,json={"status":"resolved"}).status_code == 409
    for status in ("acknowledged","in_progress","resolved"):
        assert client.patch("/complaints/"+item["id"],headers=planner,json={"status":status}).status_code == 200
    assert len(client.get("/audit",headers=planner).json()) == 3
    outside = report(client,citizen,17.44,78.35).json()
    assert client.patch("/complaints/"+outside["id"],headers=planner,json={"status":"acknowledged"}).status_code == 403

def test_citizen_report_list_is_limited_to_own_reports(client):
    first = auth(client, "citizen")
    second_user = client.post("/auth/register", json={"email": "second@demo.local", "password": "AnotherPassword1!"}).json()
    second = {"Authorization": "Bearer " + second_user["token"]}
    first_report = report(client, first).json()
    second_report = report(client, second).json()
    first_rows = client.get("/complaints", headers=first).json()
    second_rows = client.get("/complaints", headers=second).json()
    assert {row["id"] for row in first_rows} == {first_report["id"]}
    assert {row["id"] for row in second_rows} == {second_report["id"]}

def test_location_and_validation(client):
    c=auth(client,"citizen")
    assert report(client,c,28.6,77.2).status_code == 422
    assert report(client,c,17.21,78.26).status_code == 422
    assert report(client,c,17.42,78.43).status_code == 201
    assert client.post("/auth/login",json={"email":"planner@demo.local","password":"bad-password"}).status_code == 401

def test_constraints_are_hard_filters():
    result = recommend("Under 10 lakh, within 14 days, no construction",Constraints(budget_lakhs=50).model_dump())
    assert result["constraints"]["budget_lakhs"] == 10
    assert result["constraints"]["timeline_days"] == 14
    assert {c["id"] for c in result["candidates"]} == {"signal","parking"}
    assert all(c["cost_lakhs"]<=10 and c["days"]<=14 and not c["construction"] for c in result["candidates"])
    assert recommend("zero funding",Constraints(budget_lakhs=0).model_dump())["candidates"] == []
    assert recommend("under 1 crore",Constraints(budget_lakhs=150).model_dump())["constraints"]["budget_lakhs"] == 100

def test_offline_plan_provenance_and_approval(client):
    h=auth(client,"planner")
    body={"ward_id":1,"prompt":"Signal timing under 50 lakh within 30 days"}
    a=client.post("/plans",headers=h,json=body); assert a.status_code==201,a.text
    b=client.post("/plans",headers=h,json=body)
    assert a.json()["result"] == b.json()["result"]
    assert a.json()["result"]["rag"]["mode"]=="offline"
    assert a.json()["result"]["rag"]["citations"]
    assert client.post("/plans",headers=h,json=dict(body,ward_id=2)).status_code==403
    p=a.json()["id"]
    assert client.post("/plans/"+p+"/approve",headers=h).status_code==200
    assert client.post("/plans/"+p+"/approve",headers=h).status_code==409
    overview=client.get("/wards/2/overview",headers=h).json()
    assert overview["read_only"] and not overview["live_telemetry"]
    assert all(o["provenance"]=="simulated" for o in overview["history"])
    assert "provenance" in client.get("/wards/1/export",headers=h).text

def test_openai_failure_is_explicit(client,monkeypatch):
    import openai
    class Failing:
        def __init__(self,**kwargs): raise RuntimeError("unavailable")
    monkeypatch.setenv("OPENAI_API_KEY","not-a-real-key")
    monkeypatch.setattr(openai,"OpenAI",Failing)
    response=client.post("/plans",headers=auth(client,"planner"),json={"ward_id":1,"prompt":"Review signal timing"})
    rag=response.json()["result"]["rag"]
    assert rag["mode"]=="offline" and "RuntimeError" in rag["fallback_reason"]

def test_media_validation_and_access(client):
    c=auth(client,"citizen")
    item=report(client,c).json()
    path="/complaints/"+item["id"]+"/media"
    assert client.post(path,headers=c,files={"file":("bad.png",b"not an image","image/png")}).status_code==415
    stream=io.BytesIO();Image.new("RGB",(8,8)).save(stream,format="PNG")
    r=client.post(path,headers=c,files={"file":("test.png",stream.getvalue(),"image/png")})
    assert r.status_code==201,r.text
    assert client.get(path+"/"+r.json()["media_id"],headers=c).status_code==200
    assert client.get("/jobs/"+r.json()["job_id"],headers=c).json()["status"]=="queued"

def test_worker_outage_no_fabricated_simulation(client,monkeypatch):
    import backend.main
    class Down:
        def get(self,*args): return None
    monkeypatch.setattr(backend.main,"redis_client",lambda:Down())
    r=client.post("/simulations",headers=auth(client,"planner"),json={"ward_id":1})
    assert r.status_code==503
    assert "fabricated" in r.json()["detail"]

def test_historical_ingestion_atomic_and_idempotent(client,tmp_path):
    from backend.ingest import ingest
    from backend.db import Session,Observation
    f=tmp_path/"history.csv"
    f.write_text("ward_id,domain,metric,value,unit,observed_at\n1,traffic,travel_time,23,s,2024-01-01T00:00:00Z\n")
    assert ingest(f,"test historical source","test license")==1
    assert ingest(f,"test historical source","test license")==1
    with Session() as db: assert db.query(Observation).filter_by(source="test historical source").count()==1
    f.write_text("ward_id,domain,metric,value,unit,observed_at\n1,traffic,travel_time,23,s,2024-01-02T00:00:00Z\n999,traffic,travel_time,20,s,2024-01-03T00:00:00Z\n")
    import pytest
    with pytest.raises(ValueError): ingest(f,"test historical source","test license")
    with Session() as db: assert db.query(Observation).filter_by(source="test historical source").count()==1

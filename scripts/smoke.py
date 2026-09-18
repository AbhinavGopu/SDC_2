"""Run against the actual Compose API; creates clearly named local test records."""
import json, time, urllib.request
BASE="http://127.0.0.1:8000"
def call(path,token=None,data=None):
    headers={}
    if token:headers["Authorization"]="Bearer "+token
    if data is not None:headers["Content-Type"]="application/json"
    req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
def main():
    health=call("/health")
    assert health["database"]=="postgresql" and health["redis"] and health["sumo_worker"],health
    token=call("/auth/login",data={"email":"planner@demo.local","password":"CityDemo-2026!"})["token"]
    overview=call("/wards/1/overview",token)
    assert not overview["live_telemetry"]
    assert {"historical","simulated"} <= {o["provenance"] for o in overview["history"]}
    plan=call("/plans",token,{"ward_id":1,"prompt":"Integration smoke test: signal timing under 10 lakh within 14 days"})
    assert plan["result"]["candidates"]
    job=call("/simulations",token,{"ward_id":1,"seconds":60,"seed":42,"green_seconds":25})
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        job=call("/jobs/"+job["id"],token)
        if job["status"] in ("completed","failed"):break
        time.sleep(1)
    assert job["status"]=="completed",job
    assert job["result"]["engine"]=="SUMO/TraCI"
    assert job["result"]["provenance"]=="simulated"
    assert job["result"]["baseline"]["frames"]
    print(json.dumps({"health":health,"job_id":job["id"],"engine":job["result"]["engine"],"baseline_arrivals":job["result"]["baseline"]["arrived_vehicles"],"trial_arrivals":job["result"]["intervention"]["arrived_vehicles"],"rag_mode":plan["result"]["rag"]["mode"]},indent=2))
if __name__=="__main__":main()

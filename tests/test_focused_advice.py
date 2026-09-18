from conftest import auth


def test_advice_targets_priority_and_moves_on_after_resolution(client):
    citizen, planner = auth(client, "citizen"), auth(client, "planner")
    def submit(description):
        return client.post("/complaints", headers=citizen, json={"description":description,"latitude":17.435,"longitude":78.445}).json()
    event = submit("Festival procession tomorrow needs traffic management")
    accident = submit("Accident causing congestion at the junction")
    response = client.post("/plans", headers=planner, json={"ward_id":1,"prompt":""})
    assert response.status_code == 201, response.text
    result = response.json()["result"]
    assert result["target_complaint"]["id"] == accident["id"]
    assert "immediately" in result["review_action"]
    assert any("incident" in c["name"] for c in result["candidates"])
    assert len({c["id"] for c in result["candidates"]}) == len(result["candidates"])
    assert client.get("/complaints/"+accident["id"],headers=citizen).json()["status"] == "received"
    limited = client.post("/plans",headers=planner,json={"ward_id":1,"constraints":{"budget_lakhs":0}}).json()["result"]
    assert not limited["candidates"] and limited["review_action"] == "Review immediately"
    for state in ["acknowledged","in_progress","resolved"]:
        client.patch("/complaints/"+accident["id"],headers=planner,json={"status":state})
    next_plan = client.post("/plans",headers=planner,json={"ward_id":1}).json()["result"]
    assert next_plan["target_complaint"]["id"] == event["id"]
    assert any("event" in c["name"] for c in next_plan["candidates"])


def test_empty_brief_without_complaints_is_explicit(client):
    r=client.post("/plans",headers=auth(client,"planner"),json={"ward_id":1})
    assert r.status_code == 409

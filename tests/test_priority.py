import pytest
from backend.priority import complaint_priority
from conftest import auth


@pytest.mark.parametrize("description,level", [
    ("An accident is causing congestion at the junction", "critical"),
    ("An ambulance is stuck in traffic", "critical"),
    ("People injured near the market", "critical"),
    ("Festival procession tomorrow evening", "high"),
    ("A procession is blocking the main road", "high"),
    ("Festival procession next month, request route planning", "medium"),
    ("A procession may take place, date not confirmed", "medium"),
    ("Pothole on a quiet side street", "normal"),
    ("No accident or injuries, just a broken streetlight", "normal"),
    ("Accident yesterday, the road has been cleared", "medium"),
    ("Accident yesterday but the road is still blocked", "high"),
])
def test_priority_rules(description, level):
    result = complaint_priority(description)
    assert result["level"] == level
    assert result["reason"] and result["review"] and not result["verified"]


def test_priority_sorting_existing_reports_and_resolution(client):
    citizen, planner = auth(client, "citizen"), auth(client, "planner")
    def submit(description):
        r = client.post("/complaints", headers=citizen, json={"description": description, "latitude":17.435,"longitude":78.445})
        assert r.status_code == 201
        return r.json()
    normal = submit("Broken streetlight in a quiet lane")
    critical = submit("Accident causing congestion on the main road")
    planned = submit("Festival procession next month needs route planning")
    imminent = submit("Festival procession tomorrow on the main road")
    rows = client.get("/complaints", headers=planner).json()
    assert [c["id"] for c in rows] == [critical["id"], imminent["id"], planned["id"], normal["id"]]
    for state in ["acknowledged", "in_progress", "resolved"]:
        assert client.patch("/complaints/"+critical["id"],headers=planner,json={"status":state}).status_code == 200
    rows = client.get("/complaints", headers=planner).json()
    assert rows[-1]["id"] == critical["id"]
    assert rows[-1]["priority"]["level"] == "closed"

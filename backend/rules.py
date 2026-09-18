import json, re
from pathlib import Path

AUTHORITIES = json.loads((Path(__file__).resolve().parents[1] / "config/authorities.json").read_text())
CANDIDATES = [
    dict(id="signal", name="Trial signal retiming", cost_lakhs=8, days=14, row_m=0, construction=False, road_closure=False, affects_bus=False, benefit_score=6),
    dict(id="parking", name="Parking enforcement and junction clearance", cost_lakhs=3, days=7, row_m=0, construction=False, road_closure=False, affects_bus=False, benefit_score=4),
    dict(id="transit", name="Study a temporary bus priority route", cost_lakhs=15, days=30, row_m=0, construction=False, road_closure=False, affects_bus=True, benefit_score=5),
    dict(id="water", name="Survey and clear drainage obstructions", cost_lakhs=12, days=21, row_m=1, construction=True, road_closure=True, affects_bus=False, benefit_score=3),
    dict(id="pothole", name="Survey a road widening option", cost_lakhs=180, days=180, row_m=6, construction=True, road_closure=True, affects_bus=True, benefit_score=7),
]
def classify(description):
    s = description.lower()
    for words, category, issue in [
        (["waterlogging", "flood", "drain"], "traffic", "water"),
        (["pothole", "broken road"], "traffic", "pothole"),
        (["parking", "encroach"], "traffic", "parking"),
        (["smoke", "dust", "air"], "pollution", "air"),
        (["garbage", "waste"], "pollution", "waste"),
        (["sewage", "water pollution"], "pollution", "water"),
        (["power", "electric", "streetlight"], "energy", "energy"),
    ]:
        if any(w in s for w in words):
            return category, issue
    return "traffic", "signal"

def constraints_from(prompt, supplied):
    c = dict(supplied)
    s = prompt.lower()
    budgets = re.findall(r"([\d.]+)\s*(lakh|lac|crore|rupees|inr)", s)
    for number, unit in budgets:
        value = float(number) * (100 if unit == "crore" else 1 if unit in ("lakh", "lac") else 0.00001)
        c["budget_lakhs"] = min(c["budget_lakhs"], value)
    times = re.findall(r"(?:within|under|in|deadline)\s*(\d+)\s*(day|week|month)", s)
    for number, unit in times:
        days = int(number) * {"day": 1, "week": 7, "month": 30}[unit]
        c["timeline_days"] = min(c["timeline_days"], days)
    if re.search(r"no (?:road )?widening|no construction|no digging", s):
        c["no_construction"] = True
    if re.search(r"no (?:road )?closures", s):
        c["no_road_closures"] = True
    if re.search(r"(?:preserve|protect|not affect|do not affect).*bus", s):
        c["preserve_bus"] = True
    return c

def recommend(prompt, supplied, candidates=None):
    c = constraints_from(prompt, supplied)
    accepted, rejected = [], []
    for candidate in (CANDIDATES if candidates is None else candidates):
        item = dict(candidate, authority=AUTHORITIES[candidate.get("authority_key", candidate["id"])], estimate_provenance="simulated planning assumption; not official schedule of rates")
        reasons = []
        if item["cost_lakhs"] > c["budget_lakhs"]: reasons.append("budget")
        if item["days"] > c["timeline_days"]: reasons.append("timeline")
        if item["row_m"] > c["available_row_m"]: reasons.append("right of way")
        if c["no_construction"] and item["construction"]: reasons.append("construction prohibited")
        if c["no_road_closures"] and item["road_closure"]: reasons.append("road closures prohibited")
        if c["preserve_bus"] and item["affects_bus"]: reasons.append("bus corridor protected")
        if reasons: rejected.append(dict(item, reasons=reasons))
        else: accepted.append(item)
    accepted.sort(key=lambda x: (-x["benefit_score"] / x["cost_lakhs"], x["id"]))
    return {"constraints": c, "candidates": accepted, "rejected": rejected,
            "limitations": ["Costs and benefit scores are illustrative assumptions.", "Free-text social or political constraints require planner review; only the displayed structured constraints are enforced.", "No engineering feasibility or real-world benefit is established."]}

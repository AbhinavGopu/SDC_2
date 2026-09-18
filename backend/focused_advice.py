import re
from .rules import classify, CANDIDATES


def focused_options(complaint):
    """Select relevant options before enforcing planner constraints."""
    text = complaint.description.lower()
    if re.search(r"\b(accident|crash|collision|injured|ambulance|trapped)\b", text):
        return [option("signal", "Coordinate incident assessment and emergency-access protection", 1, 1),
                option("signal", "Prepare a traffic-management and clearance plan with the responsible authority", 3, 2)]
    if re.search(r"\b(procession|festival|parade|rally|immersion|gathering)\b", text):
        return [option("signal", "Confirm event time, route and expected attendance with organizers", 1, 1),
                option("signal", "Prepare an event traffic-control and emergency-access plan", 4, 2)]
    category, issue = classify(complaint.description)
    if category == "traffic":
        if issue == "water":
            return [option("water", "Inspect reported waterlogging and identify drainage obstructions", 2, 1)]
        return [dict(c) for c in CANDIDATES if c["id"] == issue]
    return [option(issue, "Verify the reported issue and coordinate a corrective-action assessment", 2, 2)]


def option(authority_key, name, cost, days):
    return dict(id=re.sub(r"[^a-z]+", "-", name.lower()).strip("-"), authority_key=authority_key, name=name, cost_lakhs=cost, days=days, row_m=0,
                construction=False, road_closure=False, affects_bus=False, benefit_score=1)

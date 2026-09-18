"""Explainable intake triage; reported urgency is not independently verified."""
import re


def complaint_priority(description, status="received"):
    text = description.lower()

    def mentions(pattern):
        for match in re.finditer(r"\b(?:" + pattern + r")\b", text):
            prefix = text[max(0, match.start() - 45):match.start()]
            if not re.search(r"\b(?:no|not|without)\s+(?:\w+\s+){0,3}$", prefix):
                return True
        return False

    accident = mentions(r"accidents?|crash(?:es)?|collision|pile[- ]?up")
    danger = mentions(r"injur(?:y|ies|ed)|trapped|unconscious|bleeding|fire|stampede|live wires?|electrocution")
    emergency_access = mentions(r"ambulance|emergency vehicle") and mentions(r"blocked|stuck|cannot pass|unable to pass")
    event = mentions(r"procession|festival|parade|rally|march|immersion|large gathering")
    soon = mentions(r"today|tonight|tomorrow|now|ongoing|currently|in progress|this evening|this morning|within (?:an?|\d+) hours?")
    disruption = mentions(r"congestion|gridlock|blocked|blocking|standstill|traffic jam|road closure|flood(?:ing)?|severe waterlogging")
    past = mentions(r"yesterday|last week|last month|cleared|ended|already resolved") and not soon

    if status == "resolved":
        level, reason, review = "closed", "Complaint has been resolved.", "No pending review"
    elif emergency_access or (danger and not past) or (accident and not past):
        level, reason, review = "critical", (
            "Reported obstruction to emergency access." if emergency_access else
            "Reported immediate safety risk or injuries." if danger else
            "Reported accident or collision requires immediate assessment."
        ), "Review immediately"
    elif event and (soon or disruption):
        level, reason, review = "high", "Procession or event is imminent, ongoing, or disrupting traffic.", "Review promptly; coordinate traffic arrangements"
    elif disruption and (not past or mentions(r"still|remains|continues")):
        level, reason, review = "high", "Reported significant traffic disruption or blocked access.", "Review promptly"
    elif event:
        level, reason, review = "medium", "Planned procession or gathering needs advance coordination; timing is not imminent or is unspecified.", "Confirm event time and plan before the event"
    elif accident or danger:
        level, reason, review = "medium", "Past incident reported; confirm whether any hazard remains.", "Review remaining impact"
    else:
        level, reason, review = "normal", "No immediate hazard or major disruption identified in the description.", "Routine review"
    return {"level": level, "rank": {"critical": 0, "high": 1, "medium": 2, "normal": 3, "closed": 4}[level],
            "reason": reason, "review": review, "method": "deterministic triage v1", "verified": False}

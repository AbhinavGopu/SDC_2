import re
from typing import Dict, Any

class ComplaintClassifier:
    """
    Multimodal complaint classifier for citizen reports.
    Extracts domain category, severity, urgency, landmarks, and responsible department.
    """

    KEYWORD_MAPPINGS = {
        "traffic": [
            "traffic", "jam", "bottleneck", "signal", "light", "congestion",
            "pothole", "flyover", "car", "bus", "vehicle", "parking", "gridlock", "queue"
        ],
        "pollution": [
            "pollution", "air", "pm2.5", "pm10", "dust", "smoke", "smog",
            "smell", "odor", "garbage", "waste", "noise", "dumping", "aqi"
        ],
        "energy": [
            "electricity", "power", "blackout", "outage", "wire", "cable",
            "transformer", "streetlight", "voltage", "pole", "current", "load"
        ],
        "drainage": [
            "waterlogging", "water", "flood", "drain", "drainage", "pipe",
            "pipeline", "manhole", "sewer", "rainwater"
        ]
    }

    SEVERITY_KEYWORDS = {
        "high": ["severe", "danger", "hazard", "fatal", "accident", "overflow", "stuck", "emergency", "fire", "spark", "submerged", "gridlock"],
        "medium": ["delay", "slow", "frequent", "broken", "issue", "problem", "bottleneck"],
        "low": ["minor", "request", "suggestion", "dim", "paint"]
    }

    HYD_LANDMARKS = {
        "ameerpet": 1,
        "gachibowli": 2,
        "biodiversity": 2,
        "bio-diversity": 2,
        "kukatpally": 3,
        "jntu": 3,
        "secunderabad": 4,
        "madhapur": 5,
        "cyber towers": 5,
        "hitec": 5,
        "banjara": 6,
        "jubilee": 7,
        "begumpet": 8,
        "uppal": 9,
        "dilsukhnagar": 10
    }

    def classify_complaint(self, text: str, media_type: str = "text") -> Dict[str, Any]:
        """
        Classifies incoming citizen complaint text or audio/image description.
        """
        lower = text.lower()

        # 1. Determine Category
        category = "traffic" # default
        matched_counts = {cat: 0 for cat in self.KEYWORD_MAPPINGS}
        for cat, kws in self.KEYWORD_MAPPINGS.items():
            for kw in kws:
                if kw in lower:
                    matched_counts[cat] += 1

        top_cat = max(matched_counts, key=matched_counts.get)
        if matched_counts[top_cat] > 0:
            category = "traffic" if top_cat == "drainage" else top_cat

        # 2. Determine Severity
        severity = "medium"
        for kw in self.SEVERITY_KEYWORDS["high"]:
            if kw in lower:
                severity = "high"
                break
        if severity != "high":
            for kw in self.SEVERITY_KEYWORDS["low"]:
                if kw in lower:
                    severity = "low"
                    break

        # 3. Detect Landmark and Inferred Ward
        inferred_ward_id = None
        matched_landmark = None
        for lm, w_id in self.HYD_LANDMARKS.items():
            if lm in lower:
                inferred_ward_id = w_id
                matched_landmark = lm.title()
                break

        # 4. Department Routing
        authority = "GHMC"
        if category == "traffic":
            if any(k in lower for k in ["signal", "retiming", "police", "atsc"]):
                authority = "Hyderabad Traffic Police"
            elif any(k in lower for k in ["drain", "waterlogging", "water"]):
                authority = "HMWSSB (Water Board)"
            else:
                authority = "GHMC Traffic & Engineering Cell"
        elif category == "pollution":
            authority = "TSPCB (Pollution Control Board)"
        elif category == "energy":
            authority = "TSSPDCL"

        return {
            "category": category,
            "severity": severity,
            "urgency": "immediate" if severity == "high" else "standard",
            "inferred_ward_id": inferred_ward_id,
            "detected_landmark": matched_landmark,
            "responsible_authority": authority,
            "media_type": media_type
        }

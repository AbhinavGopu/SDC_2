import re

def parse_constraints(prompt: str) -> dict:
    """
    Parses budget (standardized to lakhs), timeline (in days), and other
    exclusion flags from a natural language constraint string.
    """
    constraints = {
        "budget": None,            # budget limit in Lakhs INR (e.g. 50.0 means 50 Lakhs)
        "timeline_days": None,     # timeline limit in days
        "no_road_closures": False,
        "no_weekday_closures": False,
        "no_widening": False,
    }
    
    lower_prompt = prompt.lower()
    
    # 1. Parse Budget (e.g., "₹50 lakh", "budget is 40 lakhs", "under Rs 2 cr")
    budget_match = re.search(
        r'(?:budget|limit|cost|under|rs\.?|₹)\b.*?\b(\d+(?:\.\d+)?)\s*(lakh|l|crore|cr|crores|lakhs)?', 
        lower_prompt
    )
    if budget_match:
        val = float(budget_match.group(1))
        unit = budget_match.group(2)
        if unit in ['crore', 'cr', 'crores']:
            constraints["budget"] = val * 100.0  # 1 Crore = 100 Lakhs
        else:
            constraints["budget"] = val          # Default to Lakhs
            
    # 2. Parse Timeline (e.g., "within 5 days", "time taken is not over 6 months")
    timeline_match = re.search(
        r'(?:within|in|timeline|under|duration|time|period|limit)\b.*?\b(\d+)\s*(day|days|week|weeks|month|months|year|years)', 
        lower_prompt
    )
    if timeline_match:
        val = int(timeline_match.group(1))
        unit = timeline_match.group(2)
        if 'day' in unit:
            constraints["timeline_days"] = val
        elif 'week' in unit:
            constraints["timeline_days"] = val * 7
        elif 'month' in unit:
            constraints["timeline_days"] = val * 30
        elif 'year' in unit:
            constraints["timeline_days"] = val * 365
            
    # 3. Parse Exclusion conditions
    if any(phrase in lower_prompt for phrase in ["no road closure", "no closure", "without road closure", "without closing"]):
        constraints["no_road_closures"] = True
    if any(phrase in lower_prompt for phrase in ["no weekday closure", "off-peak", "weekend", "night", "nights"]):
        constraints["no_weekday_closures"] = True
    if any(phrase in lower_prompt for phrase in ["no widening", "no road widening", "without widening", "avoid widening"]):
        constraints["no_widening"] = True
        
    return constraints

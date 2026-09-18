import os
from src.agent.constraint_parser import parse_constraints
from src.db.models import Ward, LocalityMetrics

# RAG & Rule Engine imports
from src.rag.retriever import retrieve_context, format_context_for_prompt
from src.domains.traffic.infra_advisor.problem_diagnoser import ProblemDiagnoser
from src.domains.traffic.infra_advisor.cost_estimator import CostEstimator
from src.domains.traffic.infra_advisor.ranker import Ranker
from src.domains.traffic.infra_advisor.signal_optimizer import SignalOptimizer
from src.domains.traffic.infra_advisor.drainage_advisor import DrainageAdvisor


CANDIDATES = [
    {
        "id": "atsc",
        "name": "Adaptive Traffic Signal Control (ATSC) deployment",
        "domain": "traffic",
        "cost_lakhs": 45.0,
        "time_days": 10,
        "impact": "reduces average vehicle delay by 18-22% and queue length by 15%",
        "authority": "Hyderabad Traffic Police",
        "requires_widening": False,
        "requires_closures": False,
        "details": "Execution Plan: Off-peak nighttime installations. Calibration done during live traffic without weekday closures."
    },
    {
        "id": "reroute",
        "name": "Off-peak traffic diversion and dynamic lane clearing",
        "domain": "traffic",
        "cost_lakhs": 10.0,
        "time_days": 3,
        "impact": "reduces peak congestion index by 12-15%",
        "authority": "GHMC & Hyderabad Traffic Police (joint)",
        "requires_widening": False,
        "requires_closures": False,
        "details": "Execution Plan: Immediate implementation over a weekend. Enforces towing zones and temporary flow modifications."
    },
    {
        "id": "drainage",
        "name": "Stormwater drainage upgrade and water pump integration",
        "domain": "traffic",
        "cost_lakhs": 25.0,
        "time_days": 14,
        "impact": "eliminates waterlogging-induced traffic jams by 95% at the bottleneck site",
        "authority": "HMWSSB (Water Board) & GHMC Engineering",
        "requires_widening": False,
        "requires_closures": True,
        "details": "Execution Plan: 14 days of phased lane closures. Best executed during dry spells."
    },
    {
        "id": "widening",
        "name": "Minor road widening and corridor expansion",
        "domain": "traffic",
        "cost_lakhs": 300.0,
        "time_days": 120,
        "impact": "increases road segment throughput by 25% and reduces bottlenecks",
        "authority": "GHMC Engineering (Roads) wing",
        "requires_widening": True,
        "requires_closures": True,
        "details": "Execution Plan: Phased corridor construction over 4 months with detours. Requires utility poles shifting."
    },
    {
        "id": "flyover",
        "name": "Grade-separated flyover construction at major junction",
        "domain": "traffic",
        "cost_lakhs": 1500.0,
        "time_days": 360,
        "impact": "increases junction transit capacity by 60% and eliminates grade congestion",
        "authority": "GHMC Engineering & HMDA",
        "requires_widening": True,
        "requires_closures": True,
        "details": "Execution Plan: Major civil construction over 1 year. Requires persistent traffic diversions."
    },
    {
        "id": "aqi_sprinklers",
        "name": "Anti-smog water mist gun installation & construction dust shields",
        "domain": "pollution",
        "cost_lakhs": 12.0,
        "time_days": 5,
        "impact": "reduces local PM2.5/PM10 concentrations by 25% during dry hours",
        "authority": "TSPCB (Telangana State Pollution Control Board)",
        "requires_widening": False,
        "requires_closures": False,
        "details": "Execution Plan: Installed on critical commercial poles. Sprinkling scheduled during peak congestion hours."
    },
    {
        "id": "dust_barriers",
        "name": "Enforcement of dust screens and construction barrier violations",
        "domain": "pollution",
        "cost_lakhs": 5.0,
        "time_days": 2,
        "impact": "curbs construction dust fallout and improves local AQI by 15%",
        "authority": "GHMC Town Planning & TSPCB",
        "requires_widening": False,
        "requires_closures": False,
        "details": "Execution Plan: Inspection and screen setup. Can be done immediately without traffic impact."
    },
    {
        "id": "transformer_capacitor",
        "name": "Auxiliary capacitor bank deployment at local distribution transformers",
        "domain": "energy",
        "cost_lakhs": 28.0,
        "time_days": 7,
        "impact": "stabilizes local grid load, mitigates transformer heating, and reduces voltage drops by 99.8%",
        "authority": "TSSPDCL",
        "requires_widening": False,
        "requires_closures": False,
        "details": "Execution Plan: Standard installation on utility structures. Completed during scheduled 2-hour night maintenance."
    },
    {
        "id": "smart_lighting",
        "name": "Smart LED streetlight grid conversion",
        "domain": "energy",
        "cost_lakhs": 15.0,
        "time_days": 4,
        "impact": "reduces ward lighting energy consumption by 15% and improves safety",
        "authority": "GHMC Electrical wing & TSSPDCL",
        "requires_widening": False,
        "requires_closures": False,
        "details": "Execution Plan: Block-by-block night installation. No power outages to households required."
    }
]

def generate_recommendation(ward_id: int, prompt: str, db) -> str:
    # Stage 0: Fetch Ward and metrics
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    if not ward:
        return "Ward not found in database."

    latest_metric = db.query(LocalityMetrics).filter(LocalityMetrics.ward_id == ward_id).order_by(LocalityMetrics.timestamp.desc()).first()
    congestion = latest_metric.congestion_index if latest_metric else 70.0
    pm25 = latest_metric.pm25 if latest_metric else 65.0
    energy = latest_metric.energy_demand_mw if latest_metric else 50.0

    # Retrieve RAG context (Complaints & Docs)
    retrieved = retrieve_context(prompt, db, limit=2, ward_id=ward_id)
    rag_context = format_context_for_prompt(retrieved)

    # Stage 1: Diagnose problem type
    diagnoser = ProblemDiagnoser()
    diagnosis = diagnoser.diagnose_problem(congestion, retrieved.get("complaints", []))

    # Stage 1: Parse constraints
    constraints = parse_constraints(prompt)
    
    # Determine the target domain based on keywords in prompt
    lower_prompt = prompt.lower()
    domain = "traffic"
    if any(keyword in lower_prompt for keyword in ["pollution", "aqi", "dust", "smoke", "smog", "air"]):
        domain = "pollution"
    elif any(keyword in lower_prompt for keyword in ["energy", "power", "electricity", "voltage", "grid", "transformer", "streetlight"]):
        domain = "energy"
    elif any(keyword in lower_prompt for keyword in ["waterlogging", "water", "drain", "drainage", "sewage", "flood", "flooding"]) or diagnosis == "waterlogging_induced":
        domain = "traffic"  # Drainage upgrades are treated under traffic due to waterlogging impact

    # Filter candidates by domain first
    domain_candidates = [c for c in CANDIDATES if c["domain"] == domain]
    # Prioritize candidates based on specific keywords or diagnosis
    if any(keyword in lower_prompt for keyword in ["waterlogging", "water", "drain", "drainage"]) or diagnosis == "waterlogging_induced":
        domain_candidates = [c for c in CANDIDATES if c["id"] == "drainage"] + [c for c in domain_candidates if c["id"] != "drainage"]
    elif any(keyword in lower_prompt for keyword in ["signal", "timing", "atsc", "calibration"]) or diagnosis == "signal_mistiming":
        domain_candidates = [c for c in domain_candidates if c["id"] == "atsc"] + [c for c in domain_candidates if c["id"] != "atsc"]
    elif any(keyword in lower_prompt for keyword in ["diversion", "divert", "clear", "reroute", "rerouting"]):
        domain_candidates = [c for c in domain_candidates if c["id"] == "reroute"] + [c for c in domain_candidates if c["id"] != "reroute"]
    elif any(keyword in lower_prompt for keyword in ["widening", "widen", "expand", "widened"]) or (diagnosis == "capacity_limited" and not any(kw in lower_prompt for kw in ["flyover", "bridge"])):
        domain_candidates = [c for c in domain_candidates if c["id"] == "widening"] + [c for c in domain_candidates if c["id"] != "widening"]
    elif any(keyword in lower_prompt for keyword in ["flyover", "bridge"]):
        domain_candidates = [c for c in domain_candidates if c["id"] == "flyover"] + [c for c in domain_candidates if c["id"] != "flyover"]

    # Stage 2 & 3: Filter candidates by constraints
    surviving_candidates = []
    failed_candidates = []

    for c in domain_candidates:
        failed_reasons = []
        
        # Check budget limit (if budget constraints specified)
        if constraints["budget"] is not None:
            if c["cost_lakhs"] > constraints["budget"]:
                failed_reasons.append(f"cost (₹{c['cost_lakhs']:.1f}L) exceeds budget limit (₹{constraints['budget']:.1f}L)")
                
        # Check timeline limit
        if constraints["timeline_days"] is not None:
            if c["time_days"] > constraints["timeline_days"]:
                failed_reasons.append(f"time ({c['time_days']} days) exceeds timeline limit ({constraints['timeline_days']} days)")
                
        # Check widening exclusions
        if constraints["no_widening"] and c["requires_widening"]:
            failed_reasons.append("requires road widening which is excluded")
            
        # Check road closures exclusions
        if constraints["no_road_closures"] and c["requires_closures"]:
            failed_reasons.append("requires road closures which are excluded")

        if failed_reasons:
            failed_candidates.append((c, failed_reasons))
        else:
            surviving_candidates.append(c)

    # Stage 4: Rank candidates cost-effectiveness and keywords
    ranker = Ranker()
    surviving_candidates = ranker.rank_candidates(surviving_candidates, prompt, diagnosis)

    # Check if we should call LLM APIs (if keys are valid and not "mock-key")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    
    use_llm = False
    # Only call LLM if keys look actual/valid (not "mock-key" and not empty)
    if anthropic_key and anthropic_key != "mock-key":
        use_llm = "anthropic"
    elif openai_key and openai_key != "mock-key":
        use_llm = "openai"

    if use_llm:
        try:
            return call_llm_agent(use_llm, ward, congestion, pm25, energy, constraints, prompt, surviving_candidates, failed_candidates, rag_context, diagnosis)
        except Exception as e:
            # If LLM call fails, fall back to the rule-based response
            pass

    # Stage 4: Format programmatically (Rule-based agent)
    if surviving_candidates:
        best = surviving_candidates[0]
        cost_str = f"₹{best['cost_lakhs']:.1f} Lakhs" if best['cost_lakhs'] < 100 else f"₹{best['cost_lakhs']/100.0:.2f} Crores"
        
        # Check if weekday closures are excluded but general closures are allowed
        exec_plan = best["details"]
        if constraints["no_weekday_closures"] and best["requires_closures"]:
            exec_plan = "Execution Plan: Executed strictly during weekend nights and off-peak hours (11 PM - 5 AM) to prevent weekday closures."

        # Add physical calculations to details if applicable
        optimal_calc_str = ""
        if best["id"] == "atsc":
            optimizer = SignalOptimizer()
            opt_data = optimizer.optimize_cycle_lengths()
            optimal_calc_str = f"- **Webster Optimal Cycle calculation**: Base Cycle Length = {opt_data['optimal_cycle_length_seconds']}s (splits: north-south={opt_data['phase_splits']['north-south']}s, east-west={opt_data['phase_splits']['east-west']}s) using Webster's critical flow split calculation."
            exec_plan += f" (Webster Optimal Cycle: {opt_data['optimal_cycle_length_seconds']}s, phase split N-S: {opt_data['phase_splits']['north-south']}s)."
        elif best["id"] == "drainage":
            drainage_adv = DrainageAdvisor()
            pipe_data = drainage_adv.size_drainage_pipes()
            optimal_calc_str = f"- **Drainage Pipe Diameter Sizing**: Calculated required diameter of {pipe_data['required_pipe_diameter_mm']}mm (Status: {pipe_data['status']}) using the Rational Method (Q = CiA) to bypass waterlogging bottlenecks."
            exec_plan += f" (Required pipe size: {pipe_data['required_pipe_diameter_mm']}mm; status: {pipe_data['status']})."

        # Construct the detailed Agentic reasoning output
        response = f"🧠 **AI PLANNER AGENT REASONING LOG**\n\n"
        response += f"### 1. Diagnosis & RAG Context Retrieval\n"
        response += f"- **Diagnosed Problem**: `{diagnosis.upper()}` (detected from congestion index of {congestion}% and user complaints).\n"
        
        # List cited documents from RAG
        cited_docs = retrieved.get("documents", [])
        if cited_docs:
            response += f"- **Cited Guidelines & Context**:\n"
            for doc in cited_docs:
                response += f"  - *{doc.title}* ({doc.category}): \"{doc.content[:120]}...\"\n"
        else:
            response += f"- **Cited Guidelines**: No local matching guidelines were found. Falling back to default standards.\n"
            
        cited_complaints = retrieved.get("complaints", [])
        if cited_complaints:
            response += f"- **Referenced Ward Complaints**:\n"
            for c in cited_complaints:
                response += f"  - \"{c.description}\" (Severity: {c.severity.upper()})\n"

        b_str = f"₹{constraints['budget']} Lakhs" if constraints.get("budget") is not None else "None"
        t_str = f"{constraints['timeline_days']} days" if constraints.get("timeline_days") is not None else "None"
        response += f"- **User Stated Constraints**: Budget: {b_str}, Timeline: {t_str}, Avoid road closures: {constraints['no_road_closures']}, Avoid widening: {constraints['no_widening']}.\n"
        response += f"- **Audit Log**:\n"
        
        # Audit pass
        response += f"  - [PASS] `{best['name']}`: Estimated cost ₹{best['cost_lakhs']}L fits budget; timeline {best['time_days']} days fits constraints.\n"
        # Audit failures
        for fc, reasons in failed_candidates:
            response += f"  - [FAIL] `{fc['name']}`: Excluded because {', '.join(reasons)}.\n"

        if optimal_calc_str:
            response += f"\n### 3. Engineering Calculations\n"
            response += f"{optimal_calc_str}\n"

        # Multi-Agent Specialist Assessment
        from src.agent.planner import MultiAgentPlanner
        agent_eval = MultiAgentPlanner().run_multi_agent_assessment(ward.id, prompt, constraints, best)
        response += f"\n### 4. Multi-Agent Specialist Consensus (Score: {agent_eval['consensus_score']}/100)\n"
        for role, rev in agent_eval['specialist_evaluations'].items():
            formatted_role = role.replace('_', ' ').title()
            response += f"- **{formatted_role}**: [{rev['verdict']}] {rev['notes']}\n"

        response += f"\n### 5. Implementation Routing Proposal\n"
        response += f"🔧 **Intervention Proposed**: {best['name']} for {ward.name}.\n"
        response += f"💰 **Budget Estimate**: {cost_str} (Approved; satisfies your constraints).\n"
        response += f"📅 **Timeline**: {best['time_days']} days. {exec_plan}\n"
        response += f"📈 **Expected Outcome**: {best['impact']}.\n"
        response += f"🏢 **Responsible Authority**: Routed to **{best['authority']}**."
        
        return response
    else:
        # Constraint conflict case
        response = f"⚠️ Constraint conflict: All standard candidates for this domain in {ward.name} violate your constraints.\n\n"
        response += "Violations:\n"
        for fc, reasons in failed_candidates:
            response += f"- {fc['name']}: {', '.join(reasons)}.\n"
            
        # Propose the cheapest/fastest regardless of constraints as an alternative
        cheapest = min(domain_candidates, key=lambda x: x["cost_lakhs"])
        cheapest_cost = f"₹{cheapest['cost_lakhs']:.1f} Lakhs" if cheapest['cost_lakhs'] < 100 else f"₹{cheapest['cost_lakhs']/100.0:.2f} Crores"
        
        response += f"\n💡 Alternative Recommendation (Phased): Deploy a minimized version of '{cheapest['name']}' costing {cheapest_cost} with a {cheapest['time_days']}-day rollout, routed to {cheapest['authority']}."
        return response

def call_llm_agent(provider: str, ward, congestion, pm25, energy, constraints, user_prompt, surviving_candidates, failed_candidates, rag_context: str = "", diagnosis: str = "") -> str:
    system_prompt = (
        "You are the expert Hyderabad Traffic & Infrastructure AI Planner. You generate highly intelligent, "
        "constraint-aware recommendations for city planners. You MUST reason step-by-step using a 'Chain of Thought' "
        "format. First, diagnose the problem, citing specific documents by title from the RAG context (e.g. "
        "According to 'HMWSSB Drainage Guide'...). Second, show a constraint audit listing which candidate options passed "
        "or failed and why. Third, output the final proposed recommendation, budget estimate, timeline, "
        "execution plan, expected outcome, and the responsible Hyderabad authority.\n\n"
        "Your final response must follow this structured format:\n"
        "🧠 **AI PLANNER AGENT REASONING LOG**\n\n"
        "### 1. Diagnosis & RAG Context Retrieval\n"
        "[Explain diagnosis and cite guidelines by name from RAG Context]\n\n"
        "### 2. Constraint Validation Audit\n"
        "[Audit logs showing PASS/FAIL on candidates and reasons]\n\n"
        "### 3. Engineering Calculations\n"
        "[Webster signal calculation details or pipe sizing splits if relevant]\n\n"
        "### 4. Implementation Routing Proposal\n"
        "🔧 **Intervention Proposed**: [Name]\n"
        "💰 **Budget Estimate**: [Cost details]\n"
        "📅 **Timeline**: [Time details]\n"
        "📈 **Expected Outcome**: [Expected impact]\n"
        "🏢 **Responsible Authority**: [Hyderabad Authority]\n"
    )
    
    user_content = (
        f"Ward Profile: {ward.name} ({ward.description})\n"
        f"Current Ward metrics: Congestion Index: {congestion}%, PM2.5: {pm25} µg/m³, Grid Demand: {energy} MW\n"
        f"Diagnosed Problem Type: {diagnosis}\n"
        f"Planner request: '{user_prompt}'\n"
        f"Parsed Constraints: {constraints}\n\n"
        f"RAG Context (Local guidelines & matching complaints):\n{rag_context}\n\n"
        f"Available Surviving Candidates: {surviving_candidates}\n"
        f"Filtered Out Candidates: {failed_candidates}\n\n"
        "Generate a recommendation following the required layout."
    )

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )
        return message.content[0].text
    else:
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=500,
            temperature=0.2
        )
        return response.choices[0].message.content


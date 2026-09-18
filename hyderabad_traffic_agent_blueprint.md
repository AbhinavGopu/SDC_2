# Hyderabad Traffic-Focused Agentic City Planner — Project Blueprint v2

Scope narrowed per requirements: **Hyderabad only**, **traffic congestion as the primary domain** (pollution and energy remain as supporting domains since they interact with traffic — e.g. congestion drives up local AQI and fuel/energy waste), with a **dual-login citizen/planner system** and a **constraint-aware agentic advisor**.

---

## 1. Features Recap (what the system does)

**Citizen login**
- Submits a complaint as text, image, or video (e.g. a photo of a blocked junction, a video of a pothole causing jams).
- The LLM analyzes the submission (multimodal), classifies the issue, extracts/asks for location.
- The system alerts the city planner assigned to that ward and generates a first-pass suggested fix.
- Citizen gets an acknowledgement + tracking ID.

**City planner login**
- Either assigned a ward/zone at login (tied to employee credentials) or can search for any locality via a search bar.
- On opening a locality: brief overview card — traffic state, infrastructure summary, pollution snapshot (air/water/land).
- Three domain tabs: **Traffic** (primary), Pollution, Energy.
- Each tab surfaces the **top 3 problems** for that locality, derived from datasets + citizen complaints.
- Planner can prompt the agent in natural language, supplying constraints (budget, spatial limits, timeline, political/social constraints) — the agent factors these in and proposes interventions.
- Agent tags **which real Hyderabad authority** owns the fix (see §5).

---

## 2. Architecture (see diagrams above for visuals)

**Layer 1 — Entry points**: Citizen app and City Planner app, both hitting a single API gateway with role-based access control (RBAC). Planner accounts carry a `ward_id` claim (assigned by admin at onboarding, matching GHMC's 150 ward divisions); citizens don't need ward info — it's inferred from their complaint's location.

**Layer 2 — API & Auth gateway**: Validates JWT, resolves role (`citizen` / `planner`), and for planners resolves their assigned ward geometry (PostGIS polygon) so all their queries are automatically scoped — unless they explicitly search another locality (read-only access outside their own ward, configurable).

**Layer 3 — Agentic core (RAG + LLM)**: This is the reasoning layer. It:
1. Retrieves relevant context from the Hyderabad data layer (live traffic, historical congestion patterns, pollution readings, energy load) plus recent citizen complaints for the locality.
2. Ranks and surfaces the top 3 problems per domain.
3. When a planner sends a free-text prompt with constraints ("fix this with under ₹50 lakh and no road widening"), the agent treats those as hard constraints in its reasoning (not just context) — it filters candidate interventions that violate a stated constraint before proposing them.
4. Outputs a recommendation **and** the authority responsible for executing it.

**Layer 4 — Hyderabad data layer**: All ingestion is scoped to Hyderabad's bounding box (roughly 17.20°N–17.60°N, 78.25°E–78.65°E) — see §4 for exact sources. This is deliberately not multi-city to keep the RAG index small, fast, and high-precision for the assignment's stated scope.

**Layer 5 — Outputs**: Planner dashboard (alerts + suggestions) and authority routing (a structured record: locality, issue, suggested fix, responsible department, constraint trade-offs considered).

---

## 3. Workflow (step-by-step)

### A. Citizen complaint flow
1. Citizen logs in → submits text and/or photo/video + (optionally) a pinned map location.
2. If video: backend extracts key frames (e.g. 1 fps) + transcribes any audio (Whisper) → both fed to the multimodal LLM alongside the text.
3. LLM classifies: domain (traffic / pollution / energy / other), severity, and confidence; if location wasn't pinned, LLM attempts to infer it from image/video content or asks the citizen to confirm a detected landmark.
4. PostGIS matches the coordinate to a GHMC ward polygon → identifies the assigned planner.
5. Agent drafts a first-pass suggested fix (using the same RAG context planners see) and pushes a real-time alert (WebSocket + email/SMS) to that planner, with the complaint attached.
6. Citizen receives a tracking ID and can check status later.

### B. City planner flow
1. Planner logs in → lands on their assigned ward (or searches another locality via the search bar, which geocodes against Hyderabad-only OSM/GHMC data).
2. Overview card renders: current traffic state (congestion index, recent incident count), infrastructure notes (road condition, ongoing works pulled from GHMC project data if available), pollution snapshot (latest air/water/land readings).
3. Planner opens the **Traffic** tab (default, since traffic is primary) → sees top 3 traffic problems (e.g. "signal cycle mismatch at X junction", "peak-hour bottleneck on Y road", "illegal parking reducing effective lane width on Z street"), each backed by cited data + related citizen complaints.
4. Planner can accept a suggestion, ask the agent to revise under new constraints, or switch to Pollution/Energy tabs (which are traffic-linked where relevant, e.g. "reducing congestion at X would also cut roadside PM2.5 by ~Y%").
5. Once a planner approves an action, it's logged and tracked against the KPI it was meant to move (e.g. congestion index) — this becomes future training signal for the agent's memory.

---

## 4. Hyderabad-Specific Datasets (with justification)

### Traffic (primary domain)
| Source | What it gives | Why this one |
|---|---|---|
| **Hyderabad Traffic Police (HTP) open data / Telangana Police open data portal** | Junction-level incident data, black-spot reports | Ground-truth local enforcement data, directly maps to the "responsible authority" for congestion fixes |
| **GHMC / HMDA GIS road network & ward boundaries** | Ward polygons (for complaint routing), road hierarchy | Needed for the PostGIS ward-matching step; official administrative boundaries |
| **OpenStreetMap, clipped to Hyderabad bbox (via OSMnx)** | Free, detailed road graph for routing/simulation | No usable free alternative gives street-level graph detail at this resolution |
| **Google Maps / HERE Traffic API (Hyderabad queries only)** | Real-time congestion/speed data | Needed for "current traffic state" — static datasets alone can't give live congestion |
| **TSRTC (Telangana State Road Transport Corporation) route/stop data** | Bus network overlay | Congestion fixes often interact with public transit routing; keeps recommendations realistic |

### Pollution (supporting domain, traffic-linked)
| Source | What it gives | Why this one |
|---|---|---|
| **TSPCB (Telangana State Pollution Control Board) real-time AQI stations** | Official air quality readings across Hyderabad (e.g. Bollaram, Sanathnagar, Zoo Park stations) | State authority data — directly usable to route pollution issues to TSPCB |
| **CPCB CAAQMS Hyderabad stations (via CPCB API)** | Cross-check / additional air stations | National-standard measurement, fills TSPCB gaps |
| **HMWSSB (water board) water quality reports** | Water pollution snapshot for "land/water/air" overview | Only credible source for the water-quality part of the overview card |
| **GHMC Solid Waste Management (SWM) data** | Land pollution / waste dumping reports | Matches "land pollution" requirement in the overview card |

### Energy (supporting domain, traffic-linked)
| Source | What it gives | Why this one |
|---|---|---|
| **TSSPDCL (Southern Power Distribution Company of Telangana) open data / consumption data** | Local grid load by area | The actual utility for Hyderabad — recommendations must route here to be actionable |
| **data.telangana.gov.in energy datasets** | Historical consumption trends | State open-data portal, free and locality-tagged |

### Cross-cutting
- **GHMC's own grievance/open-data portal** (if accessible) — useful as a sanity check for how citizen complaints are currently categorized locally.
- All ingestion pipelines should **hard-filter to the Hyderabad bounding box** at the query/API level, not just at display time — this keeps the vector index precise and prevents the agent from "hallucinating" in data from other cities when a source is nationwide (e.g. CPCB, data.gov.in).

---

## 5. Authority Routing Table (used by the agent to tag suggestions)

| Issue type | Responsible authority |
|---|---|
| Traffic signal timing, junction congestion, black spots | Hyderabad Traffic Police |
| Road condition, potholes, widening, footpaths | GHMC Engineering (Roads) wing |
| Illegal parking / encroachment reducing road width | GHMC + Traffic Police (joint) |
| Air quality / vehicular emissions | TSPCB |
| Water pollution / drainage | HMWSSB |
| Land pollution / waste dumping | GHMC Solid Waste Management wing |
| Power load / demand response / streetlights | TSSPDCL, GHMC Electrical wing |
| Public transit routing changes | TSRTC |

This table is stored as structured config (`config/authority_routing.yaml`), not hardcoded in the agent prompt, so it can be updated as departments change without retraining or reprompting logic.

---

## 6. Tech Stack (with justification)

| Layer | Choice | Why |
|---|---|---|
| LLM / agent reasoning | **Claude (Anthropic API), multimodal, tool use** | Needs to read text + images natively, reason over constraints, and call tools (dataset lookups, authority routing) — this is exactly agentic tool-use territory, not a simple classifier |
| Video handling | **FFmpeg (frame extraction) + Whisper (transcription)** → frames + transcript sent to Claude | Claude doesn't take raw video; this is the standard practical bridge, keeps token cost low by sampling frames instead of sending full video |
| RAG / retrieval | **LlamaIndex or LangChain + pgvector** | Using pgvector (a Postgres extension) instead of a separate vector DB (Chroma/Pinecone) avoids running two databases — since PostGIS is already required for ward geometry, one Postgres instance serves both spatial and vector needs |
| Geospatial matching | **PostgreSQL + PostGIS** | Ward-to-complaint matching is fundamentally a "which polygon contains this point" query — PostGIS is the standard, well-optimized tool for this |
| Time-series sensor data | **TimescaleDB extension on the same Postgres instance** | Traffic/AQI/energy readings are time-series; Timescale avoids a third database while giving efficient time-range queries |
| Backend API | **FastAPI (Python)** | Same language as the ML/agent stack (no context-switching), async-native for handling concurrent complaint uploads and LLM calls |
| Object storage | **S3-compatible storage (e.g. MinIO if self-hosted, or AWS S3)** | Images/videos shouldn't live in Postgres; object storage is the standard pattern, keeps DB lean |
| Async task queue | **Celery + Redis** | Video processing (frame extraction, transcription) and LLM calls shouldn't block the request/response cycle — complaints get a fast "received" response while processing happens in the background |
| Real-time alerts | **WebSockets (for in-app) + Twilio/SMS or email for offline planners** | Planners need near-instant awareness of new complaints in their ward; WebSocket push avoids polling |
| Frontend | **React + Next.js, Mapbox/Leaflet with GHMC ward GeoJSON overlay** | Map-centric UI is core to both the locality search and the overview card; Mapbox/Leaflet are the practical open options for polygon overlays |
| Auth | **JWT + RBAC**, planner accounts provisioned with a `ward_id` claim | Simple, stateless, and naturally encodes the "planner owns a ward" business rule directly in the token |
| Deployment | **Docker + Kubernetes**, scheduled ingestion via **Airflow** | Data ingestion (traffic/AQI/energy pulls) needs to run on a schedule independent of user traffic; Airflow is standard for this kind of DAG-based pipeline |
| Monitoring | **Prometheus + Grafana** | Standard, free, and needed to track both system health and — repurposed — KPI dashboards (congestion index trends etc.) |

---

## 7. Folder Structure

```
hyderabad-traffic-agent/
├── README.md
├── pyproject.toml
├── .env.example
│
├── config/
│   ├── settings.yaml                  # Hyderabad bbox, ward count, thresholds
│   ├── authority_routing.yaml         # issue type → authority mapping (table in §5)
│   └── agent_prompts/
│       ├── planner_prompt.md          # includes instruction to respect stated constraints
│       ├── citizen_intake_prompt.md
│       ├── traffic_prompt.md
│       ├── pollution_prompt.md
│       └── energy_prompt.md
│
├── data/
│   ├── geo/
│   │   ├── ghmc_wards.geojson          # 150 ward boundaries
│   │   └── hyderabad_road_network.osm  # OSMnx extract, Hyderabad bbox only
│   ├── raw/                            # snapshots for offline dev
│   ├── processed/
│   └── vector_store/                   # pgvector tables (or Chroma if self-hosted separately)
│
├── src/
│   ├── auth/
│   │   ├── citizen_auth.py
│   │   ├── planner_auth.py            # issues ward_id-scoped JWT
│   │   └── rbac.py
│   │
│   ├── complaints/
│   │   ├── intake_api.py              # accepts text/image/video
│   │   ├── media_pipeline.py          # FFmpeg frame extraction + Whisper transcription
│   │   ├── classifier.py              # LLM multimodal classification call
│   │   ├── ward_matcher.py            # PostGIS point-in-polygon
│   │   └── alert_dispatcher.py        # WebSocket + SMS/email push to planner
│   │
│   ├── agent/
│   │   ├── core_agent.py              # plan-execute-reflect loop
│   │   ├── constraint_parser.py       # extracts budget/spatial/other constraints from planner prompt
│   │   ├── planner.py
│   │   ├── memory.py
│   │   └── tools.py                   # dataset lookups, authority_routing lookup, complaint search
│   │
│   ├── rag/
│   │   ├── ingestion.py               # Hyderabad-only scoped ingestion
│   │   ├── retriever.py
│   │   └── vector_db.py               # pgvector wrapper
│   │
│   ├── domains/
│   │   ├── traffic/                   # primary domain — most detailed module
│   │   │   ├── data_connector.py      # HTP, GHMC, OSM, live traffic API
│   │   │   ├── congestion_scorer.py   # computes congestion index per road segment
│   │   │   ├── top_problems.py        # ranks top-3 issues per locality
│   │   │   └── evaluator.py           # KPI tracking (travel time, congestion index)
│   │   ├── pollution/
│   │   │   ├── data_connector.py      # TSPCB, CPCB, HMWSSB, GHMC SWM
│   │   │   ├── top_problems.py
│   │   │   └── traffic_linkage.py     # models congestion → AQI relationship
│   │   └── energy/
│   │       ├── data_connector.py      # TSSPDCL
│   │       ├── top_problems.py
│   │       └── traffic_linkage.py     # fuel waste / idling load from congestion
│   │
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── citizen_routes.py
│   │   │   ├── planner_routes.py
│   │   │   ├── locality_routes.py     # search + overview card endpoint
│   │   │   └── agent_routes.py        # constraint-aware suggestion endpoint
│   │   └── schemas/
│   │
│   ├── orchestration/
│   │   ├── scheduler.py               # Airflow DAG triggers for data refresh
│   │   └── event_bus.py
│   │
│   └── utils/
│       ├── logging.py
│       └── geo_utils.py
│
├── dashboard/
│   ├── citizen-app/                   # complaint submission UI
│   │   └── src/
│   └── planner-app/                   # ward map, domain tabs, agent chat
│       └── src/
│           ├── components/
│           │   ├── LocalitySearch.tsx
│           │   ├── OverviewCard.tsx
│           │   ├── DomainTabs.tsx      # Traffic / Pollution / Energy
│           │   ├── TopProblemsPanel.tsx
│           │   └── AgentConstraintChat.tsx
│           └── pages/
│
├── notebooks/                         # traffic model prototyping (SUMO scenario tests etc.)
├── tests/
│   ├── unit/
│   └── integration/
│
├── deployment/
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   └── k8s/
│
└── docs/
    ├── architecture.md
    └── api_reference.md
```

---

## 8. Traffic Rerouting & Infrastructure Recommendation Engine

This is the model that turns "here's a congestion problem" into "here's a specific, costed, feasible fix" — rerouting, signal retiming, road widening, a flyover, or a drainage/sewage upgrade where waterlogging is the root cause. It sits inside `domains/traffic/` as `infra_advisor/` and runs in four stages (see diagram above).

### Stage 1 — Diagnose problem type
Before proposing anything, the engine classifies *why* a location is congested, because the fix depends entirely on the cause:
- **Recurring peak-hour bottleneck** (demand > capacity at predictable times) → signal timing or widening candidate.
- **Capacity-limited junction/corridor** (physically too narrow for its traffic volume, congestion holds most of the day) → widening or flyover candidate.
- **Waterlogging-induced** (congestion spikes correlate with rainfall + drainage complaints) → sewage/stormwater drain candidate, routed to HMWSSB.
- **Signal mistiming** (queues form even at moderate volume, cycle length doesn't match demand) → signal retiming candidate.
- **One-off/incident-driven** (accident, event, construction) → rerouting-only, no infrastructure change needed.

This classification uses a mix of the congestion time-series (from `congestion_scorer.py`), rainfall data (IMD) cross-correlated with complaint timestamps, and junction geometry from OSM/GHMC GIS — it's a rules + statistics step, not an LLM call, because it needs to be reliable and auditable.

### Stage 2 — Generate candidates (one model per intervention type)

| Intervention | Model / method | Why this method |
|---|---|---|
| **Rerouting** | Congestion-weighted shortest-path search on the Hyderabad road graph (NetworkX/OSMnx), edge weights = live travel time from the traffic API | Standard, fast, and explainable — a planner can see exactly why a route was suggested. Full dynamic traffic assignment is overkill for point suggestions. |
| **Reroute impact check** | SUMO microsimulation, feeding the proposed diversion back into a local traffic model | A rerouting suggestion that just moves the jam one block over is worse than useless — SUMO lets the engine simulate the diverted load *before* recommending it, catching that failure mode. |
| **Signal retiming** | Webster's formula for baseline cycle length/phase split from measured approach volumes, refined with an RL agent (SUMO-RL / TraCI) where enough historical data exists | Webster's method is a well-established, explainable starting point (no black box for a first recommendation); RL fine-tuning is layered in only where there's enough data to trust it, avoiding a pure black-box suggestion for junctions with sparse data. |
| **Road widening** | Traffic growth forecast (Prophet, on historical volume) projected against current capacity, filtered by available right-of-way width from HMDA/GHMC GIS layers | Widening only makes sense if (a) demand is genuinely growing and (b) there's physically room to widen — both are checkable against real GIS data rather than left to the LLM to guess. |
| **Flyover** | Triggered when junction volume already exceeds capacity, widening is geometrically infeasible (ROW check fails), and the location has recurring high delay (not just peak-hour) | Flyovers are the most expensive, disruptive option — the engine only surfaces it when the cheaper options are ruled out by hard feasibility checks, not by cost alone. |
| **Drainage/sewage upgrade** | Simplified rational method (Q = CiA) sizing against rainfall intensity data (IMD) and existing GHMC drain network capacity | Gives a defensible, engineering-based capacity number rather than a vague "upgrade the drain" suggestion — routes to HMWSSB with an actual sizing target. |

### Stage 3 — Constraint filter
Every candidate from Stage 2 is checked against the constraints already extracted by `constraint_parser.py` (§8 note in the earlier design):
- **Budget**: each candidate has a cost estimate from `cost_estimator.py`, built on GHMC/PWD standard schedule-of-rates benchmarks (₹/km for widening, ₹/lane-km for flyovers, ₹/km for drain upgrades). Anything over the planner's stated ceiling is dropped or flagged as "needs phased funding."
- **Spatial**: ROW width checks (widening/flyover), whether utility lines or heritage/no-construction zones block the site (drop from HMDA land-use layer).
- **Other stated constraints**: e.g. "no road closures during exam season," "must not affect the bus corridor" — passed to the LLM as explicit filtering instructions, since these are open-ended and not GIS-checkable.

### Stage 4 — Rank and recommend
Surviving candidates are ranked by **estimated congestion reduction per rupee spent** (a simple effectiveness score combining the SUMO-simulated or Webster-predicted delay reduction against the cost estimate). The LLM agent takes this ranked list plus the diagnosis and writes the final recommendation in plain language, citing the data behind it, and tags it with the responsible authority from `authority_routing.yaml` (Hyderabad Traffic Police for retiming, GHMC Engineering for widening/flyovers, HMWSSB for drainage).

### New folder additions
```
src/domains/traffic/infra_advisor/
├── problem_diagnoser.py       # Stage 1: classifies root cause
├── rerouting_engine.py        # congestion-weighted shortest path (NetworkX)
├── sumo_impact_checker.py     # simulates diverted load before recommending a reroute
├── signal_optimizer.py        # Webster baseline + optional RL refinement
├── widening_flyover_advisor.py # growth forecast + ROW feasibility check
├── drainage_advisor.py        # rational-method sizing for waterlogging fixes
├── cost_estimator.py          # PWD/GHMC schedule-of-rates based cost lookup
└── ranker.py                  # cost-effectiveness ranking of surviving candidates
```

### Additional datasets needed for this engine
| Dataset | Used for |
|---|---|
| Historical traffic volume time series (per road segment, ≥2 years if available) | Growth forecasting for widening/flyover decisions |
| HMDA/GHMC land-use & right-of-way GIS layers | Feasibility checks for widening and flyover siting |
| IMD (India Meteorological Department) Hyderabad rainfall data | Correlating congestion with waterlogging, sizing drain upgrades |
| GHMC stormwater drain network GIS + capacity data | Baseline for drainage upgrade sizing |
| GHMC/PWD schedule of rates (public works cost benchmarks) | Cost estimation for every candidate intervention |
| Junction geometry (lane count, turning movements) from OSM + GHMC | Signal timing (Webster's formula inputs) and widening feasibility |

---

## 9. Design Notes Worth Flagging

- **Why traffic is structurally "primary"**: the `domains/traffic/` module is the most detailed (dedicated congestion scorer + evaluator), and both pollution and energy modules include a `traffic_linkage.py` that models how a traffic fix affects them — this keeps the other two domains genuinely supporting rather than duplicating full pipelines.
- **Why constraints are parsed, not just prompted**: `constraint_parser.py` extracts structured constraints (budget ceiling, spatial limits, timeline) from the planner's free-text prompt *before* the agent generates suggestions, so constraints act as hard filters rather than something the LLM might silently ignore in a long generation.
- **Human-in-the-loop**: nothing in this design auto-executes a real-world action (e.g. changing a real signal timing) — every agent output is a *recommendation with a named authority*, and a planner must explicitly act on it. This matters both for safety and because actual execution requires those departments' own systems.
- **Ward-scoped by default, searchable beyond**: planners default to their assigned ward (matches how officials actually work) but can search any Hyderabad locality — useful for cross-ward issues like a single congested corridor spanning two wards.

# Hyderabad City Lab

A local Windows/Docker Compose project with a FastAPI API, PostgreSQL 16 with PostGIS and pgvector, Redis, an actual containerized SUMO/TraCI worker, and separate citizen/planner Next.js applications.

**Run this project from this folder, not from `hyderabad-traffic-agent/`.** That older scaffold and all supplied reference files are preserved. Its generated `.next` files are unrelated to the new stack. No GitHub repository, commit, push, or deployment is needed.

## Start on Windows

Install/start Docker Desktop with Linux containers (WSL2), then in PowerShell:

```powershell
Copy-Item .env.example .env # only on first setup; do not overwrite a configured .env
docker compose up -d --build
docker compose ps
```

- Citizen: http://localhost:3000
- Planner: http://localhost:3001
- API documentation: http://localhost:8000/docs
- Dependency status: http://localhost:8000/health

Demo accounts: `citizen@demo.local` and `planner@demo.local`. Default password: `CityDemo-2026!`. The planner is assigned demonstration area 1 (Ameerpet). Citizen registration cannot create planner accounts. Demo passwords are read at first database initialization; changing the environment does not reset existing accounts.

`docker compose stop` stops services and retains data. `docker compose up -d` starts them again. Named volumes persist PostgreSQL, Redis and uploaded media. Do not use `down -v` unless you intend to erase these project volumes.

## Interface

Both portals open on a login-only page with blank credential fields. After login, workspace navigation appears across the top, including on mobile. Signing out returns to the login page and clears the visible workspace. The shared theme is light blue.

## Priority-focused planning advisor

The planning brief starts empty and shows a placeholder suggestion only. You can request advice without typing when the assigned ward has unresolved complaints. The server chooses the highest-priority unresolved complaint, oldest first for ties, and filters complaint-specific options through the planner controls. The selected report and review urgency appear in the result. Resolving the complaint separately makes the next unresolved issue eligible on the next request. Advice and approval do not automatically resolve complaints. If the queue is empty, enter a planning brief to review another issue.

## Complaint priority

Assigned ward reports are automatically ranked as Critical, High, Medium, Normal, or Closed. Reported accidents, injuries and blocked emergency access require immediate review; imminent/ongoing processions and major road disruptions receive High priority. Events with unspecified or later timing receive Medium priority for advance planning. Routine issues receive Normal priority; resolved reports appear last. Each card explains the rule and suggested review urgency. Within a priority, older reports appear first, before the 100-report display limit. Existing complaints are included without a database migration.

Priority is derived from report text and status using deterministic rules, not independently verified facts or an official response-time commitment. Timing words such as tomorrow are interpreted as reported urgency, not automatically scheduled calendar events. Planners should confirm timing and severity.

## Traffic-dot playback

Sign in to the planner portal and open **Simulation lab** in the top navigation. Click **Run comparison** to load actual SUMO frames. Blue dots are moving vehicles, amber dots are slow vehicles, and red dots are stopped vehicles. Use **Play traffic** or the time slider to compare baseline and trial queues. Positions are sampled every ten simulation seconds with up to 100 displayed vehicles per frame; playback is accelerated. The generated junction and demand are simulated, not official live Hyderabad telemetry.

## What is implemented

- Citizen login/registration, coordinate confirmation on an offline SVG study-area map, text complaints, JPEG/PNG/MP4 evidence (10 MB, up to three attachments), tracking IDs and status tracking.
- PBKDF2 password hashes and expiring JWTs. Citizens can read only their own complaints. Planners can update only their assigned area. Other locality indicators are read-only.
- PostGIS point-in-polygon routing in Compose; Shapely provides the test-only/local SQLite equivalent. Demo polygons are explicitly labeled rectangular study areas, not official administrative boundaries.
- Three indicator tabs, dated history, source/provenance labels, CSV export, citizen report review and an audit trail. Report lists poll every ten seconds.
- Hard budget/timeline/right-of-way/construction/closure/bus-corridor filters, eligible and rejected alternatives, illustrative authority routing, approval for human review.
- OpenAI Responses-based RAG with pgvector and `text-embedding-3-small` in PostgreSQL. With no key, or an API failure, deterministic lexical retrieval and rule-based explanations take over with an explicit mode/reason. The LLM cannot alter the structured eligible candidates.
- A durable PostgreSQL work queue, Redis worker heartbeat and ward notifications, and a single SUMO worker. Redis failure is visible in health; no SUMO result is invented on worker outage.
- Real SUMO network generation, TraCI stepping, matching synthetic demand/seed for baseline and trial, measured simulation speed/halting/arrival/emission outputs and trajectory frames. The trial is allowed to be worse.
- Optional OpenAI image analysis. MP4 processing in the worker samples up to three frames from the first ten seconds and transcribes up to thirty seconds of audio if present. Without a key, media is stored explicitly for human review; contents are not inferred.

## Data honesty

**No official live telemetry is supplied or claimed.**

- `data/simulated_observations.json`: deterministic synthetic traffic, pollution and energy examples, dated July 1–7, 2025. Dates do not turn synthetic values into historical measurements.
- `data/demo_wards.geojson`: three invented rectangular study areas and local IDs, not official GHMC ward numbers or boundaries.
- `data/historical/`: downloaded Open-Meteo/Copernicus ERA5 historical precipitation reanalysis for July 1–7, 2025. The returned grid coordinate is **17.5 N, 78.5 E**; this is gridded modeled weather context, not a ward rain gauge or traffic sensor. The original response, query, attribution and normalized CSV are included. It is seeded as historical weather context for area 1.
- `data/knowledge.json`: authored demonstration guidance, not official standards. Costs, benefit scores and authority assignments are illustrative and must be verified.
- SUMO geometry and demand are generated examples, not calibrated Hyderabad traffic.

See [data and external requirements](docs/DATA_AND_EXTERNALS.md), [architecture](docs/ARCHITECTURE.md), and [verification](docs/VERIFICATION.md).

## Historical imports

After startup, import your licensed, verified CSV. Required columns:
`ward_id,domain,metric,value,unit,observed_at`.
Domains: traffic, pollution, energy, weather. Values must be finite and nonnegative; timestamps must be in the past and include a timezone. Area IDs must already exist. Imports are transactional and idempotent by source/area/domain/metric/timestamp.

```powershell
docker compose cp .\my-history.csv api:/tmp/history.csv
docker compose exec api python -m backend.ingest /tmp/history.csv --source "Publisher, dataset/version, URL" --license "Actual dataset license"
```

The importer trusts the operator's source declaration; it cannot certify that a submitted CSV is authentic. Do not import generated samples as historical data.

The bundled historical download can be reproduced from the workspace root with `python scripts/fetch_history.py`; it requires internet access.

## OpenAI configuration

Leave `OPENAI_API_KEY` blank for the deterministic offline application. To enable OpenAI, set a valid key and an available `OPENAI_MODEL` in local `.env`, then recreate API and worker:
`docker compose up -d --force-recreate api sumo`.

The server-only key is never sent to either frontend. Enabling it sends planning briefs/retrieved reference text and submitted media to OpenAI; use only data you are authorized to process. API calls incur provider costs. No external authority, email or SMS is contacted.

Official API references used: [Responses quickstart](https://developers.openai.com/api/docs/quickstart), [embeddings](https://platform.openai.com/docs/api-reference/embeddings/create). Actual credentialed OpenAI calls need separate verification; offline and provider-error behavior are covered by tests.

## Development and checks

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.venv\Scripts\python.exe -m pytest -q
cd apps
npm ci
npm run build
npx playwright install chromium
npm run test:e2e # expects the Compose services already running
```

For local backend-only development: set `DATABASE_URL=sqlite:///./smartcity.db` and run `.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000`. SQLite does not verify PostgreSQL extensions or the SUMO worker. Frontend development scripts use 3000 and 3001. Compose is the integrated target.

## Scope and limits

This is a local planning prototype, not an operational municipal service. Free-text social/political constraints are flagged for human review; only displayed structured constraints are machine-enforced. Candidate benefits are heuristic scores, not a congestion forecast. Approving a plan creates an audit record, not a work order. The application does not actuate signals, route actual vehicles, contact departments, certify drainage engineering, or claim official emissions/health effects.

The older blueprint's Kubernetes, Airflow, TimescaleDB, MinIO, email/SMS, calibrated citywide rerouting, official GIS/ROW engineering and production identity integration are not configured by the agreed Compose architecture. Required datasets, credentials and remaining integrations are documented explicitly.

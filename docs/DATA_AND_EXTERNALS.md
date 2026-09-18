# Data and external requirements

| Item | Included / current behavior | External material required |
|---|---|---|
| Historical context | Open-Meteo ERA5 daily rainfall sample, raw response + CSV + provenance | Internet to refresh; observe data terms and attribution |
| Traffic observations | Explicit simulated indicators | Licensed dated junction counts, speeds, incidents, source timestamps and spatial mapping |
| Ward routing | Three labeled rectangular study polygons | Verified GHMC boundaries, authoritative IDs, effective date and usage rights |
| Road network | SUMO-generated four-arm junction | Licensed Hyderabad road topology, lane/turn geometry, demand/OD counts and calibration observations |
| RAG | Authored local guidance + offline retrieval | OPENAI_API_KEY for embeddings/generation; licensed engineering/municipal documents for substantive retrieval |
| Pollution | Synthetic values; no live AQI | Licensed dated air/water/waste data and units; no assumed public API access |
| Energy | Synthetic indicators | Utility-approved interval consumption and outage data |
| Engineering | Illustrative cost/benefit constraints | Current schedule of rates, right-of-way, utilities/heritage restrictions, drainage geometry/rainfall design criteria, engineer review |
| Authority routing | Illustrative config/authorities.json | Confirm current agency names, ownership, jurisdiction and escalation contacts |
| Media analysis | Offline human-review label; optional image/video analysis code | OpenAI credentials and consent/authorization to process submitted material |
| Notifications | In-app polling; Redis publications | Provider credentials and explicit deployment authorization for email/SMS (not configured) |
| Account identity | Local demo and citizen registration | Municipal employee provisioning / production identity integration |

Historical rainfall source: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). Dataset attribution: Open-Meteo and Copernicus Climate Change Service ERA5. API-delivered data is under CC BY 4.0 according to the provider; verify provider/source terms for your intended redistribution. ERA5 is historical **reanalysis**, not a point sensor measurement. The raw response retains the actual returned grid coordinates and units.

The `provenance` field is exposed on observation exports and indicator cards. Original date, source and license accompany each imported record. Synthetic seed dates are fixed for reproducibility; there is no artificial "updated just now" timestamp.

No official traffic, administrative boundary, power-meter or pollution dataset has been supplied. The project does not silently fetch third-party private data or represent placeholders as integrations.

References used for implementation:
- https://developers.openai.com/api/docs/quickstart
- https://platform.openai.com/docs/api-reference/embeddings/create
- https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html
- https://open-meteo.com/en/docs/historical-weather-api

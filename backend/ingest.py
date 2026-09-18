"""Local, idempotent historical CSV importer. No network or invented provenance."""
import argparse, csv, hashlib, math
from datetime import datetime, timezone
from .db import Session, Observation, Ward

def ingest(path, source, license):
    if not source.strip() or not license.strip():
        raise ValueError("Source and license are mandatory")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    prepared = []
    with Session() as db:
        for row in rows:
            ward_id = int(row["ward_id"])
            if not db.get(Ward, ward_id): raise ValueError("Unknown ward")
            if row["domain"] not in ("traffic", "pollution", "energy", "weather"): raise ValueError("Invalid domain")
            instant = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
            if instant.tzinfo is None or instant > datetime.now(timezone.utc): raise ValueError("Historical timestamps must include timezone and be in the past")
            value = float(row["value"])
            if not math.isfinite(value) or value < 0: raise ValueError("Invalid reading")
            if not row["metric"].strip() or not row["unit"].strip(): raise ValueError("Metric and unit are required")
            identity = source + "|" + str(ward_id) + "|" + row["domain"] + "|" + row["metric"] + "|" + instant.isoformat()
            prepared.append(dict(id=hashlib.sha256(identity.encode()).hexdigest(), ward_id=ward_id, domain=row["domain"],
                                  metric=row["metric"], value=value, unit=row["unit"], observed_at=instant.isoformat(),
                                  provenance="historical", source=source, license=license))
        for row in prepared: db.merge(Observation(**row))
        db.commit()
    return len(prepared)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path"); p.add_argument("--source", required=True); p.add_argument("--license", required=True)
    a = p.parse_args()
    print("Imported", ingest(a.path, a.source, a.license), "historical rows")

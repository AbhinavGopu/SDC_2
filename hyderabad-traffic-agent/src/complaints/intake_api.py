# API endpoints for submitting complaints (multipart form data)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from src.complaints.classifier import ComplaintClassifier
from src.complaints.ward_matcher import WardMatcher
from src.complaints.alert_dispatcher import AlertDispatcher


@dataclass
class ComplaintSubmission:
    citizen_name: str
    contact_email: str
    locality: str
    category: str
    description: str
    severity: str = "medium"
    lat: Optional[float] = None
    lon: Optional[float] = None
    media_file: Optional[str] = None


@dataclass
class ComplaintRecord:
    id: str
    citizen_name: str
    contact_email: str
    locality: str
    category: str
    description: str
    severity: str
    status: str
    ward_id: Optional[int] = None
    responsible_authority: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintIntakeService:
    def __init__(self) -> None:
        self._records: List[ComplaintRecord] = []
        self.classifier = ComplaintClassifier()
        self.ward_matcher = WardMatcher()
        self.alert_dispatcher = AlertDispatcher()

    def submit(self, submission: ComplaintSubmission, db=None) -> ComplaintRecord:
        db_created = False
        db_id = None
        local_db = db

        # 1. Classify complaint and detect authority
        classification = self.classifier.classify_complaint(
            text=f"{submission.description} at {submission.locality}"
        )
        final_cat = submission.category if submission.category and submission.category != "other" else classification["category"]
        final_sev = classification["severity"] if submission.severity == "medium" else submission.severity
        authority = classification["responsible_authority"]

        # 2. Match Ward
        resolved_ward = self.ward_matcher.resolve_ward(
            lat=submission.lat,
            lon=submission.lon,
            location_text=f"{submission.locality} {submission.description}"
        )
        resolved_ward_id = resolved_ward["ward_id"]

        if local_db is None:
            try:
                from src.db.db import SessionLocal
                local_db = SessionLocal()
                db_created = True
            except Exception:
                pass

        if local_db is not None:
            try:
                from src.db.models import Complaint
                from datetime import datetime, timezone

                db_complaint = Complaint(
                    citizen_email=submission.contact_email,
                    citizen_name=submission.citizen_name,
                    locality=submission.locality,
                    description=submission.description,
                    category=final_cat,
                    severity=final_sev,
                    ward_id=resolved_ward_id,
                    status="received",
                    created_at=datetime.now(timezone.utc)
                )
                local_db.add(db_complaint)
                local_db.commit()
                local_db.refresh(db_complaint)
                db_id = db_complaint.id

                # 3. Dispatch alert if high severity
                if final_sev == "high":
                    self.alert_dispatcher.dispatch_alert(
                        complaint_id=db_id,
                        ward_id=resolved_ward_id,
                        title=f"URGENT: {final_cat.upper()} issue at {submission.locality}",
                        severity=final_sev,
                        authority=authority
                    )
            except Exception:
                if local_db:
                    local_db.rollback()
            finally:
                if db_created and local_db:
                    local_db.close()

        record = ComplaintRecord(
            id=str(db_id) if db_id is not None else f"complaint-{len(self._records) + 1}",
            citizen_name=submission.citizen_name,
            contact_email=submission.contact_email,
            locality=submission.locality,
            category=final_cat,
            description=submission.description,
            severity=final_sev,
            status="received",
            ward_id=resolved_ward_id,
            responsible_authority=authority
        )
        self._records.append(record)
        return record

    def list_recent(self, limit: int = 10, db=None) -> List[ComplaintRecord]:
        local_db = db
        db_created = False

        if local_db is None:
            try:
                from src.db.db import SessionLocal
                local_db = SessionLocal()
                db_created = True
            except Exception:
                pass

        if local_db is not None:
            try:
                from src.db.models import Complaint
                db_complaints = local_db.query(Complaint).order_by(Complaint.created_at.desc()).limit(limit).all()
                
                records = []
                for c in db_complaints:
                    records.append(ComplaintRecord(
                        id=str(c.id),
                        citizen_name=c.citizen_name or "Anonymous Citizen",
                        contact_email=c.citizen_email,
                        locality=c.locality or (c.ward.locality if c.ward else "Unknown"),
                        category=c.category,
                        description=c.description,
                        severity=c.severity,
                        status=c.status,
                        ward_id=c.ward_id,
                        created_at=c.created_at
                    ))
                return records
            except Exception:
                pass
            finally:
                if db_created and local_db:
                    local_db.close()

        return self._records[-limit:][::-1]

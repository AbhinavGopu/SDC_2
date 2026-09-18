from fastapi import APIRouter, Form

from src.complaints.intake_api import ComplaintIntakeService, ComplaintSubmission

router = APIRouter()
complaint_service = ComplaintIntakeService()


@router.get("/health")
def citizen_health():
    return {"status": "citizen route online"}


@router.get("/welcome")
def citizen_welcome():
    return {"message": "Citizen portal API is ready."}


@router.post("/complaints")
def submit_complaint(
    citizen_name: str = Form(...),
    contact_email: str = Form(...),
    locality: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    severity: str = Form("medium"),
):
    submission = ComplaintSubmission(
        citizen_name=citizen_name,
        contact_email=contact_email,
        locality=locality,
        category=category,
        description=description,
        severity=severity,
    )
    record = complaint_service.submit(submission)
    return {
        "id": record.id,
        "status": record.status,
        "message": "Complaint received and routed for review.",
    }


@router.get("/complaints/recent")
def recent_complaints():
    return [
        {
            "id": record.id,
            "citizen_name": record.citizen_name,
            "locality": record.locality,
            "category": record.category,
            "severity": record.severity,
            "status": record.status,
            "created_at": record.created_at.isoformat(),
        }
        for record in complaint_service.list_recent(5)
    ]

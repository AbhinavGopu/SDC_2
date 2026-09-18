from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError

from src.auth.db import SessionLocal
from src.auth.models import Citizen, Planner, Base
from src.auth.security import hash_password, verify_password
from src.auth.jwt_utils import create_access_token

router = APIRouter()

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    ward_id: int | None = None

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/citizen/signup", response_model=TokenResponse)
def citizen_signup(request: SignupRequest, db=Depends(get_db)):
    if request.ward_id is None:
        request.ward_id = 0
    citizen = Citizen(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        ward_id=request.ward_id,
    )
    db.add(citizen)
    try:
        db.commit()
        db.refresh(citizen)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    token = create_access_token({"sub": citizen.email, "role": "citizen", "ward_id": str(citizen.ward_id)})
    return {"access_token": token}

@router.post("/planner/signup", response_model=TokenResponse)
def planner_signup(request: SignupRequest, db=Depends(get_db)):
    if request.ward_id is None:
        raise HTTPException(status_code=400, detail="ward_id is required for planner signup")
    planner = Planner(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        ward_id=request.ward_id,
    )
    db.add(planner)
    try:
        db.commit()
        db.refresh(planner)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    token = create_access_token({"sub": planner.email, "role": "planner", "ward_id": str(planner.ward_id)})
    return {"access_token": token}

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db=Depends(get_db)):
    user = db.query(Citizen).filter(Citizen.email == request.email).one_or_none()
    user_role = "citizen"
    if user is None:
        user = db.query(Planner).filter(Planner.email == request.email).one_or_none()
        user_role = "planner"
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email, "role": user_role, "ward_id": str(user.ward_id)})
    return {"access_token": token}

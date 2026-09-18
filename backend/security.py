import os, hashlib, hmac, secrets, uuid
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from .db import get_db, User

SECRET = os.getenv("JWT_SECRET", "local-development-only-change-before-sharing-123456")
bearer = HTTPBearer()

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    return salt + ":" + digest

def verify_password(password, encoded):
    salt, expected = encoded.split(":")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    return hmac.compare_digest(expected, actual)

def token(user):
    return jwt.encode({"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm="HS256")

def current_user(credentials=Depends(bearer), db=Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        user = db.get(User, payload["sub"])
        if not user:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid or expired login")

def planner(user=Depends(current_user)):
    if user.role != "planner":
        raise HTTPException(403, "Planner access required")
    return user

def own_ward(user, ward_id):
    if user.role != "planner" or user.ward_id != ward_id:
        raise HTTPException(403, "Changes are restricted to your assigned demonstration ward")

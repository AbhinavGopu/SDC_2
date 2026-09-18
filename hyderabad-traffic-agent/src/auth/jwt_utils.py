import os
import datetime
from typing import Dict, Optional

import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretdev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def create_access_token(data: Dict[str, str], expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, str]:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload

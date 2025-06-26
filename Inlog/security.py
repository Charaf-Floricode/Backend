# backend/security.py
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from typing import Any
from dotenv import load_dotenv
load_dotenv()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

PEPPER = os.getenv("PEPPER")      # extra geheim
SECRET_KEY = os.getenv("JWT_TOKEN")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def hash_password(password: str) -> str:
    return pwd_context.hash(password + PEPPER)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain + PEPPER, hashed)

# security.py
def create_access_token(user, expires_delta: timedelta | None = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": user.username, "role": user.role, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Any:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

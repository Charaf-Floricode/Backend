# app/auth_core.py ──────────────────────────────────────────
from jose import jwe
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import HTTPException, Request
import os, json

# ▸ cryptografie / gebruikers-“DB” ─────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"])
JWE_KEY = os.getenv("JWE_SECRET", "CHANGE_ME_32_BYTE_KEY").encode()

class User(BaseModel):
    username: str
    hashed_pw: str

_users: dict[str, User] = {}        # ↩︎ vervang door echte storage

# ▸ helpers -------------------------------------------------
def hash_pw(pw: str)        -> str:  return pwd_ctx.hash(pw)
def verify_pw(pw, hashed)   -> bool: return pwd_ctx.verify(pw, hashed)

def _encode(payload: dict, exp_min: int = 60) -> str:
    payload = payload | {
        "exp": (datetime.utcnow() + timedelta(minutes=exp_min)).timestamp()
    }
    return jwe.encrypt(
        json.dumps(payload).encode(),
        JWE_KEY,
        algorithm="dir",
        encryption="A256GCM",
    )

def _decode(token: str) -> dict:
    try:
        raw = jwe.decrypt(token, JWE_KEY)
        payload = json.loads(raw)
        if payload["exp"] < datetime.utcnow().timestamp():
            raise ValueError("Token verlopen")
        return payload
    except Exception as e:
        raise HTTPException(401, str(e))

# ▸ publieke API -------------------------------------------
class RegisterIn(BaseModel):
    username: str
    password: str

def register_user(data: RegisterIn):
    if data.username in _users:
        raise HTTPException(409, "Gebruiker bestaat al")
    _users[data.username] = User(
        username=data.username,
        hashed_pw=hash_pw(data.password)
    )

def create_access_token(username: str) -> str:
    return _encode({"sub": username})

def authenticate(username: str, password: str) -> str:
    user = _users.get(username)
    if not user or not verify_pw(password, user.hashed_pw):
        raise HTTPException(401, "Ongeldige inlog")
    return create_access_token(user.username)

def get_current_user(req: Request) -> str:
    auth = req.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Geen token")
    username = _decode(auth[7:])["sub"]
    if username not in _users:
        raise HTTPException(401, "Onbekende gebruiker")
    return username

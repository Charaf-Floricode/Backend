# Backend-main/Backend-main/Inlog/azure_ad.py
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, Set

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt

TENANT = os.getenv("AZURE_TENANT_ID")
AUDIENCE = os.getenv("AZURE_API_CLIENT_ID")  # jouw API app (client) ID
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
JWKS_URL = f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys"
REQUIRED_SCOPE = os.getenv("AZURE_REQUIRED_SCOPE", "access_as_user")

bearer = HTTPBearer(auto_error=True)

@lru_cache(maxsize=1)
def _jwks() -> Dict[str, Any]:
    r = requests.get(JWKS_URL, timeout=10)
    r.raise_for_status()
    return r.json()

def _rsa_key_for(token: str) -> Dict[str, str]:
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token header")
    for key in _jwks().get("keys", []):
        if key.get("kid") == kid:
            return {"kty": key["kty"], "kid": key["kid"], "n": key["n"], "e": key["e"]}
    raise HTTPException(status_code=401, detail="No matching JWK")

def verify_access_token(token: str) -> Dict[str, Any]:
    rsa_key = _rsa_key_for(token)
    try:
        claims = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    scopes: Set[str] = set((claims.get("scp") or "").split())
    roles: Set[str] = set(claims.get("roles") or [])
    # Minimaal: scope óf rol aanwezig
    if REQUIRED_SCOPE and (REQUIRED_SCOPE not in scopes) and not roles:
        raise HTTPException(status_code=403, detail="Missing required scope or role")
    return claims

def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
    return verify_access_token(creds.credentials)

def role_required(*allowed: str):
    allowed_set = set(allowed)
    def dep(claims: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        roles = set(claims.get("roles") or [])
        if allowed_set and roles.isdisjoint(allowed_set):
            # Geen rolmatch ⇒ 403
            raise HTTPException(status_code=403, detail="Insufficient role")
        return claims
    return dep

from typing import Callable, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select

from Inlog.database import get_session
from Inlog.models import User
from Inlog.security import decode_token

# ---------------------------------------------------------------------------
# 1. OAuth2-dependency om het Bearer-token uit de Authorization-header te halen
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # login-endpoint dat de token levert


# ---------------------------------------------------------------------------
# 2. Huidige gebruiker bepalen op basis van JWT
# ---------------------------------------------------------------------------
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db=Depends(get_session),
) -> User:
    """
    Decodeert JWT, haalt de User uit de database en geeft hem terug.
    Fout-afhandeling: 401 als token ongeldig of user niet gevonden.
    """
    payload = decode_token(token)  # {"sub": "username", "role": "admin", ...}

    user: User | None = db.exec(
        select(User).where(User.username == payload["sub"])
    ).first()

    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ---------------------------------------------------------------------------
# 3. Role-based dependency-factory
# ---------------------------------------------------------------------------
def role_required(*allowed_roles: str) -> Callable:  # e.g. ("admin", "viewer")
    """
    Gebruik als Depends(role_required(\"admin\" …)).
    Retourneert de actuele User als zijn rol toegestaan is,
    anders 403 Forbidden.
    """

    def _wrapper(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return _wrapper
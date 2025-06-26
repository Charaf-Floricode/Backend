# backend/models.py
from sqlmodel import SQLModel, Field
from typing import Optional


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str
    role: str = Field(default="user", index=True)   # 'admin' | 'ops' | 'viewer' …


from datetime import datetime

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=4, max_length=80)


class UserOut(BaseModel):
    id: int
    mobile: str
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserOut

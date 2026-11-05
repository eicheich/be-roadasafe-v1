from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class UserRegister(BaseModel):
    nama: str
    email: EmailStr
    password: str
    peran: Optional[str] = "pelapor"  # pelapor, admin, pengelola


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    nama: str
    email: EmailStr
    peran: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

from pydantic import BaseModel, Field


class UserRecord(BaseModel):
    id: str
    email: str
    password_hash: str
    api_keys: list[str]      # all keys for this account; primary = api_keys[0]
    balance: int
    created_at: str


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    email: str
    api_key: str      # primary key (first in list)
    balance: int


class MeResponse(BaseModel):
    email: str
    api_keys: list[str]
    balance: int


class NewKeyResponse(BaseModel):
    api_key: str
    all_keys: list[str]

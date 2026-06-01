from fastapi import APIRouter, Depends, Header, HTTPException

from app.dependencies import get_user_store
from app.models.user import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    NewKeyResponse,
    RegisterRequest,
)
from app.services.user_store import UserStore, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

AUTH_HEADER = "X-OneAPI-Key"


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    store: UserStore = Depends(get_user_store),
) -> AuthResponse:
    try:
        user = await store.create_user(body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return AuthResponse(email=user.email, api_key=user.api_keys[0], balance=user.balance)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    store: UserStore = Depends(get_user_store),
) -> AuthResponse:
    user = await store.get_by_email(body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(email=user.email, api_key=user.api_keys[0], balance=user.balance)


@router.get("/me", response_model=MeResponse)
async def me(
    x_oneapi_key: str = Header(..., alias=AUTH_HEADER),
    store: UserStore = Depends(get_user_store),
) -> MeResponse:
    user = await store.get_by_api_key(x_oneapi_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return MeResponse(email=user.email, api_keys=user.api_keys, balance=user.balance)


@router.get("/keys", response_model=list[str])
async def list_keys(
    x_oneapi_key: str = Header(..., alias=AUTH_HEADER),
    store: UserStore = Depends(get_user_store),
) -> list[str]:
    user = await store.get_by_api_key(x_oneapi_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return user.api_keys


@router.post("/keys", response_model=NewKeyResponse, status_code=201)
async def generate_key(
    x_oneapi_key: str = Header(..., alias=AUTH_HEADER),
    store: UserStore = Depends(get_user_store),
) -> NewKeyResponse:
    user = await store.get_by_api_key(x_oneapi_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    new_key, updated = await store.add_api_key(user.id)
    return NewKeyResponse(api_key=new_key, all_keys=updated.api_keys)

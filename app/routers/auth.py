import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from app.schemas import LoginRequest, LoginResponse, LogoutResponse, RoleEnum

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="用户名或密码为空")
    role = RoleEnum.admin if payload.username.lower().startswith("admin") else RoleEnum.user
    token = secrets.token_hex(16)
    expires = 3600
    return LoginResponse(token=token, role=role, expires_in=expires)


@router.post("/logout", response_model=LogoutResponse)
async def logout() -> LogoutResponse:
    return LogoutResponse()


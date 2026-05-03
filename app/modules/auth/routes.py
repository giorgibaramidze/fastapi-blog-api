from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from httpx import request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db  # შენი get_db dependency
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.modules.auth.services import AuthService
from app.modules.auth.dependencies import get_auth_service, get_current_user

REFRESH_TOKEN_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30


auth_router = APIRouter(prefix="/auth", tags=["Auth"])


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )

@auth_router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    try:
        login_response, raw_refresh = await service.login(db, data, request)
        set_refresh_cookie(response, raw_refresh)
        return login_response
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(e))


@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    try:
        return await service.register_user(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@auth_router.get(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> VerifyEmailResponse:
    try:
        return await service.verify_email(db, token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@auth_router.post("/resend-verification")
async def resend_verification(
    email: str,
    db: AsyncSession = Depends(get_db),
    service=Depends(get_auth_service),
):
    try:
        return await service.resend_verification_email(db, email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    raw_refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)

    if raw_refresh_token:
        await service.logout(db, raw_refresh_token)

    clear_refresh_cookie(response)

    return {"message": "Logged out successfully."}

@auth_router.post("/logout-all-devices")
async def logout_all_devices(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    await service.logout_all_devices(db, current_user.id)
    clear_refresh_cookie(response)
    return {"message": "Logged out from all devices successfully."}
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from httpx import request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_verification_email
from app.db.session import get_db

from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
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

    login_response, raw_refresh = await service.login(db, data, request)

    set_refresh_cookie(response, raw_refresh)

    return login_response


@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
):

    result = await service.register_user(db, data)

    background_tasks.add_task(
        send_verification_email,
        email=result.email,
        token=result.verification_token,
    )

    return RegisterResponse(
        message="Registration successful. Check your email.",
        email=result.email,
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
    return await service.verify_email(
        db,
        token,
    )

@auth_router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> ResendVerificationResponse:

    result = await service.resend_verification_email(
        db,
        payload.email,
    )

    if result.send_email:
        background_tasks.add_task(
            send_verification_email,
            email=result.email,
            token=result.verification_token,
        )

    return ResendVerificationResponse(
        message=result.message,
    )


@auth_router.post("/logout", response_model=LogoutResponse)
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

    return LogoutResponse(message="Logged out successfully.")

@auth_router.post("/logout-all-devices", response_model=LogoutResponse)
async def logout_all_devices(
    response: Response,
    current_user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):

    count = await service.logout_all_devices(db, current_user.id)

    clear_refresh_cookie(response)

    return LogoutResponse(
        message=f"Logged out from {count} device(s)."
    )

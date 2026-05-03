from datetime import timedelta, datetime, timezone
from typing import Union
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.enums import AuthTokenType, SessionRevokeReason
from app.modules.auth.exceptions import AccountSuspended, EmailNotVerified, InvalidCredentials, InvalidToken
from app.modules.auth.repositories import AuthTokenRepository, SessionRepository
from app.modules.auth.results import (
    RegisterResult,
    ResendVerificationResult,
)
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    VerifyEmailResponse,
)
from app.modules.users.exceptions import EmailAlreadyExists, UserAlreadyVerified, UserNotFound, UsernameAlreadyExists
from app.modules.users.repositories import UserRepository

VERIFICATION_TOKEN_TTL = timedelta(minutes=30)
RESET_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        auth_token_repo: AuthTokenRepository,
        session_repo: SessionRepository,
    ):
        self.user_repo = user_repo
        self.auth_token_repo = auth_token_repo
        self.session_repo = session_repo

    async def register_user(
        self,
        db: AsyncSession,
        data: RegisterRequest,
    ) -> RegisterResult:

        async with db.begin():

            if await self.user_repo.get_by_email(db, data.email):
                raise EmailAlreadyExists()

            if await self.user_repo.get_by_username(db, data.username):
                raise UsernameAlreadyExists()

            user = await self.user_repo.create(
                db,
                email=data.email,
                username=data.username,
                hashed_password=hash_password(data.password),
            )

            raw_token = generate_refresh_token()
            token_hash = hash_token(raw_token)

            await self.auth_token_repo.create(
                db,
                user_id=user.id,
                token_hash=token_hash,
                token_type=AuthTokenType.EMAIL_VERIFICATION,
                expires_at=datetime.now(timezone.utc) + VERIFICATION_TOKEN_TTL,
            )

        return RegisterResult(
            email=user.email,
            verification_token=raw_token,
        )

    async def verify_email(
        self,
        db: AsyncSession,
        raw_token: str,
    ) -> VerifyEmailResponse:

        token_hash = hash_token(raw_token)

        async with db.begin():

            auth_token = await self.auth_token_repo.get_valid_token(
                db,
                token_hash=token_hash,
                token_type=AuthTokenType.EMAIL_VERIFICATION,
            )

            if not auth_token:
                raise InvalidToken()

            user = await self.user_repo.get_by_id(
                db,
                auth_token.user_id,
            )

            if not user:
                raise UserNotFound()

            if user.is_verified:
                raise UserAlreadyVerified()

            await self.auth_token_repo.mark_used(
                auth_token,
            )

            await self.user_repo.mark_verified(
                db,
                user,
            )

        return VerifyEmailResponse(
            message="Email verified successfully. You can now log in."
        )

    async def resend_verification_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> ResendVerificationResult:

        async with db.begin():

            user = await self.user_repo.get_by_email(db, email)

            if not user or user.is_verified:
                return ResendVerificationResult(
                    send_email=False,
                    message="If account exists, verification email has been sent.",
                )

            await self.auth_token_repo.deactivate_user_tokens(
                db,
                user_id=user.id,
                token_type=AuthTokenType.EMAIL_VERIFICATION,
            )

            raw_token = generate_refresh_token()
            token_hash = hash_token(raw_token)

            await self.auth_token_repo.create(
                db,
                user_id=user.id,
                token_hash=token_hash,
                token_type=AuthTokenType.EMAIL_VERIFICATION,
                expires_at=datetime.now(timezone.utc) + VERIFICATION_TOKEN_TTL,
            )

        return ResendVerificationResult(
            send_email=True,
            email=user.email,
            verification_token=raw_token,
            message="Verification email sent.",
        )

    async def login(
        self,
        db: AsyncSession,
        data: LoginRequest,
        request: Request,
    ) -> tuple[LoginResponse, str]:

        async with db.begin():

            user = await self.user_repo.get_by_email(db, data.email)

            if not user or not verify_password(data.password, user.hashed_password):
                raise InvalidCredentials()

            if not user.is_active:
                raise AccountSuspended()

            if not user.is_verified:
                raise EmailNotVerified()

            raw_refresh = generate_refresh_token()
            device_id = str(uuid.uuid4())

            await self.session_repo.create(
                db,
                user_id=user.id,
                refresh_token_hash=hash_token(raw_refresh),
                device_id=device_id,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
                expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_TTL,
            )

            await self.user_repo.update_last_login(db, user)

        access_token = create_access_token(subject=user.id)

        return LoginResponse(access_token=access_token), raw_refresh

    async def logout(
        self,
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> None:

        session = await self.session_repo.get_valid_session(
            db,
            refresh_token_hash=hash_token(raw_refresh_token),
        )

        if session:
            await self.session_repo.revoke(
                db,
                session_id=session.id,
                reason=SessionRevokeReason.LOGOUT,
            )
            
        await db.commit() 

    async def logout_all_devices(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:

        count = await self.session_repo.revoke_all_for_user(
            db,
            user_id=user_id,
            reason=SessionRevokeReason.LOGOUT,
        )
        
        await db.commit() 

        return count

from datetime import timedelta, datetime, timezone
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_verification_email
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.enums import AuthTokenType, SessionRevokeReason
from app.modules.auth.repositories import AuthTokenRepository, SessionRepository
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    VerifyEmailResponse,
)
from app.modules.users.repositories import UserRepository

VERIFICATION_TOKEN_TTL = timedelta(hours=24)
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
    ) -> RegisterResponse:

        if await self.user_repo.get_by_email(db, data.email):
            raise ValueError("Email is already registered.")

        if await self.user_repo.get_by_username(db, data.username):
            raise ValueError("Username is already taken.")

        try:
            # Create user
            user = await self.user_repo.create(
                db,
                email=data.email,
                username=data.username,
                hashed_password=hash_password(data.password),
            )

            # Create verification token
            raw_token = generate_refresh_token()
            token_hash = hash_token(raw_token)

            await self.auth_token_repo.create(
                db,
                user_id=user.id,
                token_hash=token_hash,
                token_type=AuthTokenType.EMAIL_VERIFICATION,
                expires_at=datetime.now(timezone.utc) + VERIFICATION_TOKEN_TTL,
            )

            # Commit transaction
            await db.commit()

        except Exception:
            await db.rollback()
            raise

        # Send email after successful commit
        await send_verification_email(
            email=user.email,
            token=raw_token,
        )

        return RegisterResponse(
            message=(
                "Registration successful. "
                "Please check your email to verify your account."
            ),
            email=user.email,
        )

    async def verify_email(
        self,
        db: AsyncSession,
        raw_token: str,
    ) -> VerifyEmailResponse:

        token_hash = hash_token(raw_token)

        # Find valid token
        auth_token = await self.auth_token_repo.get_valid_token(
            db,
            token_hash=token_hash,
            token_type=AuthTokenType.EMAIL_VERIFICATION,
        )

        if not auth_token:
            raise ValueError("Invalid or expired verification link.")

        # Load user
        user = await self.user_repo.get_by_id(
            db,
            auth_token.user_id,
        )

        if not user:
            raise ValueError("User not found.")

        if user.is_verified:
            raise ValueError("Email is already verified.")

        try:
            # Mark token used
            await self.auth_token_repo.mark_used(
                db,
                auth_token,
            )

            # Mark user verified
            await self.user_repo.mark_verified(
                db,
                user,
            )

            # Commit transaction
            await db.commit()

        except Exception:
            await db.rollback()
            raise

        return VerifyEmailResponse(
            message="Email verified successfully. You can now log in."
        )

    async def resend_verification_email(self, db: AsyncSession, email: str):
        try:
            user = await self.user_repo.get_by_email(db, email)

            if not user:
                raise ValueError("User not found.")

            if user.is_verified:
                raise ValueError("User is already verified.")

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

            await db.commit()

        except Exception:
            await db.rollback()
            raise

        await send_verification_email(email=user.email, token=raw_token)

        return {"message": "Verification email resent."}

    async def login(
        self,
        db: AsyncSession,
        data: LoginRequest,
        request: Request,
    ) -> tuple[LoginResponse, str]:
        """
        Returns (LoginResponse, raw_refresh_token).
        raw_refresh_token → cookie-ში ჩაწერა routes.py-დან.
        """
        user = await self.user_repo.get_by_email(db, data.email)

        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Your account has been suspended.")

        if not user.is_verified:
            raise ValueError("Please verify your email before logging in.")

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

        await db.commit()

        access_token = create_access_token(subject=user.id)

        return LoginResponse(access_token=access_token), raw_refresh

    async def logout(
        self,
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> LogoutResponse:
        session = await self.session_repo.get_valid_session(
            db,
            refresh_token_hash=hash_token(raw_refresh_token),
        )

        if session:
            await self.session_repo.revoke(
                db,
                session=session,
                reason=SessionRevokeReason.LOGOUT,
            )
            await db.commit()

        return LogoutResponse(message="Logged out successfully.")

    async def logout_all_devices(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> LogoutResponse:
        count = await self.session_repo.revoke_all_for_user(
            db,
            user_id=user_id,
            reason=SessionRevokeReason.LOGOUT,
        )
        await db.commit()

        return LogoutResponse(message=f"Logged out from {count} device(s).")

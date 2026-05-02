from datetime import timedelta, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_verification_email
from app.core.security import (
    generate_refresh_token,
    hash_password,
    hash_token,
)
from app.db.enums import AuthTokenType
from app.modules.auth.repositories import AuthTokenRepository
from app.modules.auth.schemas import (
    RegisterRequest,
    RegisterResponse,
    VerifyEmailResponse,
)
from app.modules.users.repositories import UserRepository

VERIFICATION_TOKEN_TTL = timedelta(hours=24)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        auth_token_repo: AuthTokenRepository,
    ):
        self.user_repo = user_repo
        self.auth_token_repo = auth_token_repo

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

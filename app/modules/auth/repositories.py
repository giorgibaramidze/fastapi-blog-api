from datetime import datetime, timezone
import uuid
from typing import cast
from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AuthTokenType, SessionRevokeReason
from app.modules.auth.models import AuthToken, UserSession


class AuthTokenRepository:
    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        token_type: AuthTokenType,
        expires_at: datetime,
    ) -> AuthToken:
        auth_token = AuthToken(
            user_id=user_id,
            token_hash=token_hash,
            type=token_type,
            expires_at=expires_at,
        )
        db.add(auth_token)
        await db.flush()
        return auth_token

    async def get_valid_token(
        self,
        db: AsyncSession,
        *,
        token_hash: str,
        token_type: AuthTokenType,
    ) -> AuthToken | None:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(AuthToken).where(
                AuthToken.token_hash == token_hash,
                AuthToken.type == token_type,
                AuthToken.is_used == False,
                AuthToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(
        self,
        db: AsyncSession,
        token: AuthToken,
    ) -> AuthToken:
        token.is_used = True
        db.add(token)
        await db.flush()
        return token

    async def deactivate_user_tokens(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        token_type: AuthTokenType,
    ):
        await db.execute(
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.type == token_type,
                AuthToken.is_used.is_(False),
            )
            .values(is_used=True)
        )


class SessionRepository:
    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        device_id: str,
        user_agent: str | None,
        ip_address: str | None,
        expires_at: datetime,
    ) -> UserSession:
        session = UserSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            device_id=device_id,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
        db.add(session)
        await db.flush()
        return session

    async def get_valid_session(
        self,
        db: AsyncSession,
        refresh_token_hash: str,
    ) -> UserSession | None:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.is_revoked == False,
                UserSession.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def revoke(
        self,
        db: AsyncSession,
        session: UserSession,
        reason: SessionRevokeReason,
    ) -> None:
        session.is_revoked = True
        session.revoke_reason = reason
        db.add(session)
        await db.flush()

    async def revoke_all_for_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        reason: SessionRevokeReason,
    ) -> int:
        result = await db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False,  # noqa: E712
            )
            .values(
                is_revoked=True,
                revoke_reason=reason,
            )
        )

        await db.flush()

        result = cast(CursorResult, result)

        return result.rowcount or 0

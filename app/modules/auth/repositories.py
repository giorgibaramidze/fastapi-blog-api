from datetime import datetime, timezone
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import AuthTokenType
from app.modules.auth.models import AuthToken


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

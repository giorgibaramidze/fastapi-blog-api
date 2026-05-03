from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        email: str,
        username: str,
        hashed_password: str,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
        )
        db.add(user)
        await db.flush()
        return user

    async def mark_verified(self, db: AsyncSession, user: User) -> User:
        user.is_verified = True
        return user

    async def update_password(
        self, db: AsyncSession, user: User, hashed_password: str
    ) -> User:
        user.hashed_password = hashed_password
        return user

    async def update_last_login(self, db: AsyncSession, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)

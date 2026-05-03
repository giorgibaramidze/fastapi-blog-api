from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.auth.repositories import (
    AuthTokenRepository,
    SessionRepository,
)
from app.modules.users.repositories import UserRepository

from app.modules.auth.services import AuthService



def get_user_repository() -> UserRepository:
    return UserRepository()


def get_session_repository() -> SessionRepository:
    return SessionRepository()


def get_auth_token_repository() -> AuthTokenRepository:
    return AuthTokenRepository()


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    auth_token_repo: AuthTokenRepository = Depends(
        get_auth_token_repository
    ),
) -> AuthService:

    return AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        auth_token_repo=auth_token_repo,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False),
    ),
    db: AsyncSession = Depends(get_db),
    service: UserRepository = Depends(get_user_repository),
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    user = await service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user

async def get_current_active_user(
    user=Depends(get_current_user),
):
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user.")
    return user

async def get_current_admin_user(
    user=Depends(get_current_active_user),
):
    if not user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
    return user
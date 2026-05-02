from fastapi import Depends

from app.modules.auth.repositories import (
    AuthTokenRepository,
)
from app.modules.users.repositories import UserRepository

from app.modules.auth.services import AuthService



def get_user_repository() -> UserRepository:
    return UserRepository()


# def get_session_repository() -> SessionRepository:
#     return SessionRepository()


def get_auth_token_repository() -> AuthTokenRepository:
    return AuthTokenRepository()


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    # session_repo: SessionRepository = Depends(get_session_repository),
    auth_token_repo: AuthTokenRepository = Depends(
        get_auth_token_repository
    ),
) -> AuthService:

    return AuthService(
        user_repo=user_repo,
        # session_repo=session_repo,
        auth_token_repo=auth_token_repo,
    )


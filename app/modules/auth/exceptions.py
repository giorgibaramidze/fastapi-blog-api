from app.core.exceptions.base import AppException


class AuthenticationRequired(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_REQUIRED"
    detail = "Authentication required."


class InvalidCredentials(AppException):
    status_code = 401
    error_code = "INVALID_CREDENTIALS"
    detail = "Invalid email or password."


class InvalidToken(AppException):
    status_code = 401
    error_code = "INVALID_TOKEN"
    detail = "Invalid or expired token."


class InvalidTokenPayload(AppException):
    status_code = 401
    error_code = "INVALID_TOKEN_PAYLOAD"
    detail = "Invalid token payload."


class EmailNotVerified(AppException):
    status_code = 403
    error_code = "EMAIL_NOT_VERIFIED"
    detail = "Please verify your email before logging in."


class AccountSuspended(AppException):
    status_code = 403
    error_code = "ACCOUNT_SUSPENDED"
    detail = "Your account has been suspended."
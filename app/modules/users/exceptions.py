from app.core.exceptions.base import AppException


class UserNotFound(AppException):
    status_code = 404
    error_code = "USER_NOT_FOUND"
    detail = "User not found."


class EmailAlreadyExists(AppException):
    status_code = 409
    error_code = "EMAIL_ALREADY_EXISTS"
    detail = "Email already exists."


class UsernameAlreadyExists(AppException):
    status_code = 409
    error_code = "USERNAME_ALREADY_EXISTS"
    detail = "Username already exists."


class UserAlreadyVerified(AppException):
    status_code = 409
    error_code = "USER_ALREADY_VERIFIED"
    detail = "User already verified."
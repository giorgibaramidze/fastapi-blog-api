from enum import Enum

class AuthTokenType(str, Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class SessionRevokeReason(str, Enum):
    LOGOUT = "logout"
    ROTATED = "rotated"
    REUSE_DETECTED = "reuse_detected"
    PASSWORD_CHANGED = "password_changed"
    ADMIN_REVOKED = "admin_revoked"
    ACCOUNT_DISABLED = "account_disabled"
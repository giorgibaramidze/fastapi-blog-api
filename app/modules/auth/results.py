from dataclasses import dataclass


@dataclass(slots=True)
class RegisterResult:
    email: str
    verification_token: str


@dataclass(slots=True)
class ResendVerificationResult:
    send_email: bool
    message: str
    email: str = ""
    verification_token: str = ""
from pydantic import NameEmail, SecretStr
from fastapi_mail import (
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
)

from app.core.config import settings


conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.EMAILS_FROM_EMAIL,
    MAIL_FROM_NAME=settings.EMAILS_FROM_NAME,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

mailer = FastMail(conf)


async def send_verification_email(email: str, token: str):

    verify_url = f"{settings.FRONTEND_URL}/api/v1/auth/verify-email?token={token}"

    html = f"""
    <h2>Verify your email</h2>

    <a href="{verify_url}">
        Verify Email
    </a>
    """

    message = MessageSchema(
        subject="Verify your email",
        recipients=[
            NameEmail(
                name=email,
                email=email,
            )
        ],
        body=html,
        subtype=MessageType.html,
    )

    await mailer.send_message(message)
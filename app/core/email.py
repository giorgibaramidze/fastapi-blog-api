from pydantic import NameEmail
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

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


async def send_verification_email(email: str, token: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/api/v1/auth/verify-email?token={token}"
    message = MessageSchema(
        subject="Verify your email",
        recipients=[NameEmail(name=email, email=email)],
        body=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
            <h2>Verify your email</h2>
            <a href="{verify_url}"
               style="display:inline-block; padding:12px 24px;
                      background:#000; color:#fff;
                      border-radius:6px; text-decoration:none;">
                Verify Email
            </a>
        </div>
        """,
        subtype=MessageType.html,
    )
    await mailer.send_message(message)


async def send_password_reset_email(email: str, token: str) -> None:
    url = f"{settings.FRONTEND_URL}/api/v1/auth/reset-password?token={token}"
    message = MessageSchema(
        subject="Reset your password",
        recipients=[NameEmail(name=email, email=email)],
        body=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
            <h2>Reset your password</h2>
            <p>Click the button below to set a new password.</p>
            <a href="{url}"
               style="display:inline-block; padding:12px 24px;
                      background:#000; color:#fff;
                      border-radius:6px; text-decoration:none;">
                Reset Password
            </a>
            <p style="color:#999; font-size:12px; margin-top:24px;">
                Link expires in 1 hour. If you didn't request this, ignore this email.
            </p>
        </div>
        """,
        subtype=MessageType.html,
    )
    await mailer.send_message(message)

"""Email service for Music Bank — password reset, notifications."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class EmailService:
    """Send emails via SMTP."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("SMTP_FROM", "noreply@musicbank.io")
        self._available = bool(self.smtp_host and self.smtp_user)

    @property
    def available(self) -> bool:
        return self._available

    async def send_password_reset(self, to_email: str, reset_token: str, artist_name: str) -> bool:
        """Send password reset email."""
        if not self.available:
            # Dev mode: just print
            print(f"[DEV] Password reset for {artist_name} ({to_email}): token={reset_token}")
            return True

        reset_url = f"{os.getenv('APP_URL', 'http://localhost:8090')}/auth/reset-password?token={reset_token}"

        subject = "Music Bank — Password Reset"
        body = f"""
Hi {artist_name},

You requested a password reset for your Music Bank account.

Click the link below to reset your password:
{reset_url}

This link expires in 1 hour.

If you didn't request this, ignore this email.

— Music Bank Team
        """

        return await self.send_email(to_email, subject, body)

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False


email_service = EmailService()

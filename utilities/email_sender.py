"""
Email sending via SMTP (Outlook/Office365).
Uses SENDER_EMAIL and EMAIL_PASSWORD environment variables.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

SMTP_HOST = "smtp-mail.outlook.com"
SMTP_PORT = 587

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> dict:
    """
    Send an email via Outlook SMTP.
    Returns {'ok': bool, 'message': str}
    """
    if not SENDER_EMAIL or not EMAIL_PASSWORD:
        return {"ok": False, "message": "Email service not configured (missing SENDER_EMAIL or EMAIL_PASSWORD)."}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, to, msg.as_string())
        return {"ok": True, "message": f"Email sent to {to}."}
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", SENDER_EMAIL)
        return {"ok": False, "message": "Email authentication failed. Check SENDER_EMAIL and EMAIL_PASSWORD."}
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
        return {"ok": False, "message": f"Email send failed: {e}"}
    except Exception as e:
        logger.error("Unexpected email error: %s", e)
        return {"ok": False, "message": f"Email send failed: {e}"}


def is_configured() -> bool:
    """Return True if email sending is configured."""
    return bool(SENDER_EMAIL and EMAIL_PASSWORD)

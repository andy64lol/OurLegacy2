import os
import logging
from typing import Optional

import resend

RESEND_API_KEY = os.environ.get("RESEND_API", "")
SENDER_EMAIL = os.environ.get("RESEND_EMAIL", "")

logger = logging.getLogger(__name__)

def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> dict:
    if not RESEND_API_KEY:
        return {"ok": False, "message": "Email service not configured (missing RESEND_API_KEY)."}
    if not SENDER_EMAIL:
        return {"ok": False, "message": "Email service not configured (missing SENDER_EMAIL)."}

    resend.api_key = RESEND_API_KEY

    params: resend.Emails.SendParams = {
        "from": SENDER_EMAIL,
        "to": [to],
        "subject": subject,
        "html": body_html,
    }
    if body_text:
        params["text"] = body_text

    try:
        result = resend.Emails.send(params)
        if result and result.get("id"):
            return {"ok": True, "message": f"Email sent to {to}."}
        return {"ok": False, "message": f"Resend returned unexpected response: {result}"}
    except Exception as e:
        logger.error("Resend error: %s", e)
        return {"ok": False, "message": f"Email send failed: {e}"}

def is_configured() -> bool:
    return bool(RESEND_API_KEY and SENDER_EMAIL)

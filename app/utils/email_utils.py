import os
import smtplib
from email.mime.text import MIMEText
from typing import Iterable, Tuple


def send_email(recipients: Iterable[str], subject: str, body: str) -> Tuple[bool, str | None]:
    """Send an email using SMTP. Returns (success, error_message)."""
    server = os.environ.get("SMTP_SERVER")
    if not server:
        return False, "SMTP_SERVER not configured"
    port = int(os.environ.get("SMTP_PORT", "25"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("EMAIL_FROM", username or "noreply@example.com")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(server, port) as smtp:
            if username and password:
                smtp.login(username, password)
            smtp.sendmail(sender, list(recipients), msg.as_string())
        return True, None
    except Exception as exc:  # pragma: no cover - best effort
        return False, str(exc)

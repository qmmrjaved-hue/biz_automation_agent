"""
email_adapter.py — reads unread mail via IMAP and sends replies via SMTP.

Requires in .env: IMAP_HOST, IMAP_USER, IMAP_PASSWORD (for reading) and
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (for sending). When DRY_RUN
is true (the default), send_email() logs the message instead of sending it.

Public functions:
  - fetch_unread(limit=10) -> list[dict]   # {id, subject, sender, body}
  - send_email(to_addr, subject, body) -> bool
"""

import email
import imaplib
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText

from config import settings


def _require_imap():
    if not (settings.imap_host and settings.imap_user and settings.imap_password):
        raise EnvironmentError(
            "[email_adapter] IMAP_HOST, IMAP_USER, and IMAP_PASSWORD must be "
            "set in .env to read the inbox."
        )


def _decode(value: str) -> str:
    parts = decode_header(value or "")
    decoded = ""
    for text, enc in parts:
        decoded += text.decode(enc or "utf-8", errors="ignore") if isinstance(text, bytes) else text
    return decoded


def fetch_unread(limit: int = 10) -> list:
    """
    Fetch up to `limit` unread messages from the inbox via IMAP.

    Returns:
        A list of dicts: {"id": str, "subject": str, "sender": str, "body": str}

    Raises:
        EnvironmentError: if IMAP credentials are not configured.
        imaplib.IMAP4.error: if the connection or login fails.
    """
    _require_imap()

    print(f"[email_adapter] Connecting to {settings.imap_host} as {settings.imap_user} ...")
    conn = imaplib.IMAP4_SSL(settings.imap_host)
    conn.login(settings.imap_user, settings.imap_password)
    conn.select("INBOX")

    status, data = conn.search(None, "UNSEEN")
    ids = data[0].split()[:limit] if status == "OK" else []

    messages = []
    for msg_id in ids:
        status, msg_data = conn.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        messages.append({
            "id": msg_id.decode(),
            "subject": _decode(msg.get("Subject")),
            "sender": _decode(msg.get("From")),
            "body": body.strip(),
        })

    conn.logout()
    print(f"[email_adapter] Fetched {len(messages)} unread message(s).")
    return messages


def send_email(to_addr: str, subject: str, body: str) -> bool:
    """
    Send an email via SMTP, unless DRY_RUN is enabled (default), in which
    case the message is logged and not transmitted.

    Returns:
        True if the message was sent (or would-be-sent in dry-run logging), False on failure.
    """
    if settings.dry_run:
        print(f"[email_adapter] DRY_RUN — would send email to {to_addr!r}\n"
              f"  Subject: {subject}\n  Body: {body[:200]}")
        return True

    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        raise EnvironmentError(
            "[email_adapter] SMTP_HOST, SMTP_USER, and SMTP_PASSWORD must be "
            "set in .env to send email (or leave DRY_RUN=true)."
        )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, [to_addr], msg.as_string())
        print(f"[email_adapter] Sent email to {to_addr!r}.")
        return True
    except smtplib.SMTPException as e:
        print(f"[email_adapter] Failed to send email to {to_addr!r}: {e}")
        return False

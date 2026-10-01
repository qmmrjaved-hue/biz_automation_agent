"""
whatsapp_adapter.py — sends messages via the Meta WhatsApp Business Cloud API.

Requires in .env: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID. When DRY_RUN is true
(the default), send_message() logs the composed message instead of calling
the live API — safe to use before a WhatsApp Business account is approved.

Public function:
  - send_message(to_phone, text) -> bool
"""

import requests

from config import settings

_API_VERSION = "v21.0"


def send_message(to_phone: str, text: str) -> bool:
    """
    Send a WhatsApp text message to a phone number (E.164 format, e.g. "+3934...").

    Returns:
        True if the message was sent (or would-be-sent in dry-run logging), False on failure.
    """
    if settings.dry_run:
        print(f"[whatsapp_adapter] DRY_RUN — would send WhatsApp message to {to_phone!r}: {text}")
        return True

    if not (settings.whatsapp_token and settings.whatsapp_phone_id):
        raise EnvironmentError(
            "[whatsapp_adapter] WHATSAPP_TOKEN and WHATSAPP_PHONE_ID must be "
            "set in .env to send live WhatsApp messages (or leave DRY_RUN=true)."
        )

    url = f"https://graph.facebook.com/{_API_VERSION}/{settings.whatsapp_phone_id}/messages"
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"[whatsapp_adapter] Sent WhatsApp message to {to_phone!r}.")
        return True
    except requests.RequestException as e:
        print(f"[whatsapp_adapter] Failed to send WhatsApp message to {to_phone!r}: {e}")
        return False

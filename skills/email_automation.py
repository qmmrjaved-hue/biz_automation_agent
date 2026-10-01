"""
email_automation.py — reads unread inbox mail, classifies it, drafts a
reply, routes it to the right person, and produces a short WhatsApp-style
version of the same reply.

Categories are Italian-first: fatturazione (billing), assistenza (support),
logistica (logistics), appuntamento (appointment), altro (other).

Public functions:
  - handle_inbox(limit=10, language="it") -> list[EmailClassification]
  - draft_reply(subject, body, language="it") -> str
"""

from adapters import email_adapter, llm_adapter
from config import settings
from models import EmailClassification

# Category values stay Italian regardless of UI language — they're the
# canonical keys ROUTING_MAP is configured against, not user-facing prose.
_CLASSIFY_SYSTEM_PROMPT_IT = """
Sei un assistente che smista le email in arrivo per una piccola impresa
italiana. Rispondi SOLO con un oggetto JSON con questa forma:

{
  "category": "fatturazione" | "assistenza" | "logistica" | "appuntamento" | "altro",
  "draft_reply": string,        // risposta professionale e cordiale, in italiano
  "whatsapp_message": string    // versione breve (max 2 frasi) della stessa risposta, adatta a WhatsApp
}
"""

_CLASSIFY_SYSTEM_PROMPT_EN = """
You triage incoming email for a small Italian business. Reply ONLY with a
JSON object of this shape:

{
  "category": "fatturazione" | "assistenza" | "logistica" | "appuntamento" | "altro",
  "draft_reply": string,        // a professional, friendly reply, in English
  "whatsapp_message": string    // a short version (max 2 sentences) of the same reply, suited to WhatsApp
}

Keep "category" as one of the Italian values listed above even though your
reply text is in English — it's an internal routing key, not shown to users.
"""


def _classify_and_draft(subject: str, sender: str, body: str, language: str = "it") -> dict:
    prompt = f"Da: {sender}\nOggetto: {subject}\n\nMessaggio:\n{body}"
    system_prompt = _CLASSIFY_SYSTEM_PROMPT_EN if language == "en" else _CLASSIFY_SYSTEM_PROMPT_IT
    return llm_adapter.generate_json(prompt=prompt, system_instruction=system_prompt)


def draft_reply(subject: str, body: str, language: str = "it") -> str:
    """
    Draft a standalone reply to a piece of email text, without touching the
    inbox. Useful for the controller to expose as a quick single-shot tool.

    Args:
        subject:  The email subject.
        body:     The email body text.
        language: "it" or "en" — language of the drafted reply.

    Returns:
        The drafted reply text.
    """
    result = _classify_and_draft(subject=subject, sender="", body=body, language=language)
    return result.get("draft_reply", "")


def handle_inbox(limit: int = 10, language: str = "it") -> list:
    """
    Fetch unread inbox messages, classify each one, draft a reply, route it
    to the configured recipient for its category, and send both the email
    reply and a WhatsApp-style message (both respect DRY_RUN).

    Args:
        limit:    Maximum number of unread messages to process.
        language: "it" or "en" — language of the drafted reply/WhatsApp text.

    Returns:
        A list of EmailClassification, one per processed message.

    Raises:
        EnvironmentError: if IMAP credentials are not configured.
    """
    messages = email_adapter.fetch_unread(limit=limit)
    routing = settings.routing_table()
    results = []

    for msg in messages:
        classification = _classify_and_draft(
            subject=msg["subject"], sender=msg["sender"], body=msg["body"], language=language
        )
        category = classification.get("category", "altro")
        routed_to = routing.get(category, routing.get("altro", ""))

        reply = classification.get("draft_reply", "")
        whatsapp_msg = classification.get("whatsapp_message", "")

        if routed_to:
            email_adapter.send_email(
                to_addr=routed_to,
                subject=f"[{category}] {msg['subject']}",
                body=f"Email originale da {msg['sender']}:\n\n{msg['body']}\n\n---\nBozza di risposta:\n{reply}",
            )

        results.append(EmailClassification(
            email_id=msg["id"],
            subject=msg["subject"],
            sender=msg["sender"],
            category=category,
            routed_to=routed_to,
            draft_reply=reply,
            whatsapp_message=whatsapp_msg,
        ))

    print(f"[email_automation] Processed {len(results)} message(s).")
    return results

"""
models.py — shared dataclasses passed between skills, adapters, and the controller.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractedDocument:
    source_file: str
    doc_type: str                  # "invoice" | "receipt" | "contract" | "unknown"
    fields: dict                   # e.g. {"numero_fattura": "...", "totale": "...", "partita_iva": "..."}
    summary: str
    saved_to: str = ""             # path or sink reference where the record was persisted
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class EmailClassification:
    email_id: str
    subject: str
    sender: str
    category: str                  # "fatturazione" | "assistenza" | "logistica" | "appuntamento" | "altro"
    routed_to: str
    draft_reply: str
    whatsapp_message: str


@dataclass
class ApprovalRequest:
    request_id: str
    title: str
    requester: str
    steps: list                    # e.g. ["manager", "finance"]
    current_step_index: int = 0
    status: str = "pending"        # "pending" | "approved" | "rejected"
    history: list = field(default_factory=list)  # [{"step": str, "decision": str, "actor": str, "at": str}]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

"""
reporting.py — periodic digest of what the agent has done: documents
processed and approvals opened/decided, summarized in Italian and exported
to Excel.

Public function:
  - generate_report(period="week", language="it") -> dict
"""

from datetime import datetime, timedelta

import memory
from adapters import excel_adapter, llm_adapter

_PERIOD_DAYS = {"day": 1, "week": 7, "month": 30}


def _within(record_created_at: str, cutoff: datetime) -> bool:
    try:
        return datetime.fromisoformat(record_created_at) >= cutoff
    except ValueError:
        return False


def generate_report(period: str = "week", language: str = "it") -> dict:
    """
    Build a summary of agent activity over the given period.

    Args:
        period:   "day" | "week" | "month".
        language: "it" or "en" — language of the generated summary text.

    Returns:
        {
            "period": str, "documents_count": int, "approvals_count": int,
            "summary": str, "exported_to": str,
        }

    Raises:
        ValueError: if period is not one of "day", "week", "month".
    """
    if period not in _PERIOD_DAYS:
        raise ValueError(f"[reporting] period must be one of {list(_PERIOD_DAYS)}, got {period!r}")

    days = _PERIOD_DAYS[period]
    cutoff = datetime.now() - timedelta(days=days)

    documents = memory.list_extracted_documents(since_days=days)
    approvals = [a for a in memory.list_approvals() if _within(a["updated_at"], cutoff)]

    exported_to = ""
    for doc in documents:
        exported_to = excel_adapter.append_row("report_documents", {
            "source_file": doc["source_file"], "doc_type": doc["doc_type"],
            "summary": doc["summary"], "created_at": doc["created_at"],
        })
    for appr in approvals:
        exported_to = excel_adapter.append_row("report_approvals", {
            "request_id": appr["request_id"], "title": appr["title"],
            "status": appr["status"], "updated_at": appr["updated_at"],
        })

    empty_docs = "(none)" if language == "en" else "(nessuno)"
    empty_appr = "(none)" if language == "en" else "(nessuna)"
    doc_lines = "\n".join(f"- {d['doc_type']}: {d['summary']}" for d in documents) or empty_docs
    appr_lines = "\n".join(f"- {a['title']}: {a['status']}" for a in approvals) or empty_appr

    if language == "en":
        prompt = (
            f"Write a brief report in English for the owner of a small business, "
            f"based on this data.\n\n"
            f"Documents processed ({len(documents)}):\n{doc_lines}\n\n"
            f"Approval requests ({len(approvals)}):\n{appr_lines}\n\n"
            f"Period: last {days} day(s)."
        )
    else:
        prompt = (
            f"Scrivi un breve report in italiano per il titolare di una "
            f"piccola impresa, basato su questi dati.\n\n"
            f"Documenti elaborati ({len(documents)}):\n{doc_lines}\n\n"
            f"Richieste di approvazione ({len(approvals)}):\n{appr_lines}\n\n"
            f"Periodo: ultimi {days} giorni."
        )

    summary = llm_adapter.generate_text(prompt=prompt)

    print(f"[reporting] Generated {period} report — {len(documents)} document(s), "
          f"{len(approvals)} approval(s).")

    return {
        "period": period,
        "documents_count": len(documents),
        "approvals_count": len(approvals),
        "summary": summary,
        "exported_to": exported_to,
    }

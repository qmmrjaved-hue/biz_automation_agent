"""
demo.py — end-to-end walkthrough of every skill using local files/SQLite
only. Requires GEMINI_API_KEY in .env for the LLM-powered steps (extraction,
classification, SQL generation); everything else (ETL cleaning, the
approval state machine) runs with no external service at all.

Usage:
    python demo.py
"""

import os

from config import settings
from skills import approval_workflow, document_processing, etl, voice_to_db

_SAMPLE_CSV = os.path.join("sample_data", "sample_customers.csv")
_SAMPLE_INVOICE = os.path.join("sample_data", "sample_invoice.txt")


def step(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    if not settings.gemini_api_key:
        print(
            "GEMINI_API_KEY is not set — the document extraction, email, and "
            "voice-to-db steps below will fail. Copy .env.example to .env and "
            "add your key, then re-run. Running the ETL and approval steps "
            "only for now (they need no LLM)."
        )

    step("1/4 — ETL: clean & load sample_customers.csv into local SQLite")
    etl_report = etl.clean_and_load(_SAMPLE_CSV, sink="sqlite", table_name="customers")
    print(etl_report)

    step("2/4 — Approval workflow: open and approve a request")
    approval = approval_workflow.create_request(
        title="Acquisto materiali ufficio", requester="Mario Rossi",
        steps=["manager", "finance"],
    )
    print(f"Created: {approval}")
    approval = approval_workflow.decide(approval.request_id, "approve", actor="Manager")
    print(f"After step 1: {approval}")
    approval = approval_workflow.decide(approval.request_id, "approve", actor="Finance")
    print(f"After step 2 (final): {approval}")

    if not settings.gemini_api_key:
        return

    step("3/4 — Document processing: extract fields from sample_invoice.txt")
    doc = document_processing.process_document(_SAMPLE_INVOICE, sink="excel")
    print(f"Extracted: {doc.fields}")
    print(f"Summary: {doc.summary}")
    print(f"Saved to: {doc.saved_to}")

    step("4/4 — Voice-to-DB: ask a question (text mode) against the loaded data")
    result = voice_to_db.ask(db_target=settings.warehouse_db_path, text="Quali clienti hanno sede a Napoli?")
    print(f"SQL: {result['sql']}")
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(result["results"])

    print("\nDemo complete.")


if __name__ == "__main__":
    main()

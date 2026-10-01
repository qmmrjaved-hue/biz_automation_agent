"""
document_processing.py — extracts structured fields from invoices, receipts,
and contracts (PDF or plain text), validates them, saves them to the
configured sink, and generates a short summary.

Field names are Italian-first (this agent targets Italian SMBs) since that's
what will appear on real source documents: numero_fattura, data,
partita_iva, imponibile, iva, totale, fornitore, cliente.

Public function:
  - process_document(file_path, sink=None, language="it") -> ExtractedDocument
"""

import os

from adapters import excel_adapter, llm_adapter, postgres_adapter, sheets_adapter
from config import settings
from models import ExtractedDocument
import memory

_EXTRACTION_SYSTEM_PROMPT = """
Sei un assistente che estrae dati strutturati da documenti aziendali italiani
(fatture, ricevute, contratti). Rispondi SOLO con un oggetto JSON con questa forma:

{
  "doc_type": "invoice" | "receipt" | "contract" | "unknown",
  "fields": {
    "numero_documento": string | null,
    "data": string | null,
    "fornitore": string | null,
    "cliente": string | null,
    "partita_iva": string | null,
    "imponibile": string | null,
    "iva": string | null,
    "totale": string | null
  },
  "missing_required": [string]   // subset of ["numero_documento", "data", "totale"] that could not be found
}

Usa null per i campi non presenti nel testo. Non inventare valori.
"""


def _read_text(file_path: str) -> str:
    """Extract raw text from a PDF or plain-text file."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)

    if ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    raise ValueError(f"[document_processing] Unsupported file type: '{ext}'. Use .pdf or .txt.")


def _save(doc_type: str, fields: dict, sink: str) -> str:
    """Persist extracted fields to the chosen sink; returns a location string."""
    row = {"doc_type": doc_type, **fields}

    if sink == "excel":
        return excel_adapter.append_row("documents", row)
    if sink == "sheets":
        sheets_adapter.append_row("documents", row)
        return f"google_sheets:{settings.sheets_spreadsheet_id}/documents"
    if sink == "postgres":
        postgres_adapter.append_row("documents", row)
        return "postgres:documents"

    raise ValueError(f"[document_processing] Unknown sink: '{sink}'")


def process_document(file_path: str, sink: str = None, language: str = "it") -> ExtractedDocument:
    """
    Extract structured fields from an invoice/receipt/contract, validate the
    required fields are present, persist the record, and produce a summary.

    Args:
        file_path: Path to a .pdf or .txt source document.
        sink:      "excel" | "sheets" | "postgres". Defaults to config.settings.default_sink.
        language:  "it" or "en" — language of the generated summary sentence.
                   Extracted field names stay Italian (numero_documento, totale,
                   ecc.) regardless, since they name canonical Italian invoice fields.

    Returns:
        An ExtractedDocument with fields, a summary, and where it was saved.

    Raises:
        FileNotFoundError: if file_path does not exist.
        ValueError: if the file type is unsupported.
        RuntimeError: if the LLM extraction step fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[document_processing] File not found: '{file_path}'")

    sink = sink or settings.default_sink
    print(f"[document_processing] Processing '{file_path}' (sink={sink}) ...")

    raw_text = _read_text(file_path)
    extraction = llm_adapter.generate_json(
        prompt=f"Testo del documento:\n\n{raw_text}",
        system_instruction=_EXTRACTION_SYSTEM_PROMPT,
    )

    doc_type = extraction.get("doc_type", "unknown")
    fields = extraction.get("fields", {})
    missing = extraction.get("missing_required", [])
    if missing:
        print(f"[document_processing] Warning — missing required fields: {missing}")

    saved_to = _save(doc_type, fields, sink)

    summary_prompt = (
        f"Summarize in one sentence, in English, this '{doc_type}' document with these fields: {fields}"
        if language == "en" else
        f"Riassumi in una frase, in italiano, questo documento di tipo '{doc_type}' con questi campi: {fields}"
    )
    summary = llm_adapter.generate_text(prompt=summary_prompt)

    doc = ExtractedDocument(
        source_file=file_path,
        doc_type=doc_type,
        fields=fields,
        summary=summary,
        saved_to=saved_to,
    )
    memory.save_extracted_document(doc)
    print(f"[document_processing] Done — saved to {saved_to}.")
    return doc

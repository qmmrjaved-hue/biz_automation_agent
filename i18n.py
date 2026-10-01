"""
i18n.py — UI string translations for app.py (Italian / English).

Keeps every user-visible label, button, caption, and message the Streamlit
dashboard needs, keyed by a short identifier, in both languages. Skill-level
content (LLM-generated summaries, drafts, reports) is localized separately
via each skill's own `language` parameter — this module only covers static
UI chrome.

Public function:
  - t(key, lang, **kwargs) -> str
"""

_STRINGS = {
    "nav_chat": {"it": "Chat", "en": "Chat"},
    "nav_documents": {"it": "Documenti", "en": "Documents"},
    "nav_inbox": {"it": "Posta", "en": "Inbox"},
    "nav_approvals": {"it": "Approvazioni", "en": "Approvals"},
    "nav_ask_db": {"it": "Interroga Database", "en": "Ask Database"},
    "nav_etl": {"it": "ETL", "en": "ETL"},
    "nav_reports": {"it": "Report", "en": "Reports"},

    "language_label": {"it": "Lingua / Language", "en": "Lingua / Language"},
    "session_label": {"it": "Sessione: {id}", "en": "Session: {id}"},
    "sink_dry_run": {"it": "Archivio: {sink} · DRY_RUN: {dry_run}", "en": "Sink: {sink} · DRY_RUN: {dry_run}"},
    "gemini_key_label": {"it": "Chiave Gemini:", "en": "Gemini key:"},
    "configured": {"it": "configurata", "en": "configured"},
    "missing": {"it": "mancante", "en": "missing"},

    "header_tagline": {
        "it": "Automazione AI unificata per le PMI italiane — documenti, email, approvazioni, database vocale, ETL, report",
        "en": "Unified AI automation for Italian SMBs — documents, email, approvals, voice-to-database, ETL, reporting",
    },
    "footer": {
        "it": "Business Automation Agent · Controller + 6 competenze, instradate da Gemini",
        "en": "Business Automation Agent · Controller + 6 skills, routed by Gemini function calling",
    },
    "gemini_warning": {
        "it": "GEMINI_API_KEY non è impostata — questa pagina ne ha bisogno. Aggiungila a <code>.env</code> e riavvia l'app.",
        "en": "GEMINI_API_KEY is not set — this page needs it. Add it to <code>.env</code> and restart the app.",
    },
    "dry_run_note": {
        "it": "DRY_RUN è attivo — l'invio di email/WhatsApp/API viene registrato, non trasmesso.",
        "en": "DRY_RUN is on — sending email/WhatsApp/API calls will be logged, not transmitted.",
    },
    "error_prefix": {"it": "Errore", "en": "Error"},

    # Chat page
    "section_chat": {"it": "Chat", "en": "Chat"},
    "chat_input_placeholder": {
        "it": "Scrivi una richiesta, es. 'Crea una richiesta di approvazione per...'",
        "en": "Type a request, e.g. 'Create an approval request for...'",
    },
    "chat_spinner": {"it": "L'agente sta elaborando...", "en": "The agent is processing..."},

    # Documents page
    "section_documents": {"it": "Elaborazione Documenti", "en": "Document Processing"},
    "upload_document_label": {"it": "Carica fattura, ricevuta o contratto", "en": "Upload invoice, receipt, or contract"},
    "save_to_label": {"it": "Salva in", "en": "Save to"},
    "process_document_btn": {"it": "Elabora documento", "en": "Process document"},
    "extracting_spinner": {"it": "Estrazione in corso...", "en": "Extracting..."},
    "document_processed": {"it": "Documento elaborato — tipo: {type}", "en": "Document processed — type: {type}"},
    "extracted_fields": {"it": "Campi estratti", "en": "Extracted fields"},
    "field_col": {"it": "Campo", "en": "Field"},
    "value_col": {"it": "Valore", "en": "Value"},
    "summary_label": {"it": "**Riepilogo:**", "en": "**Summary:**"},
    "saved_to_label": {"it": "Salvato in:", "en": "Saved to:"},
    "recent_documents": {"it": "Documenti recenti", "en": "Recent documents"},
    "no_documents_yet": {"it": "Nessun documento elaborato finora.", "en": "No documents processed yet."},

    # Inbox page
    "section_inbox": {"it": "Automazione Email", "en": "Email Automation"},
    "imap_not_configured": {
        "it": "IMAP non configurato — imposta IMAP_HOST, IMAP_USER, IMAP_PASSWORD in .env per leggere la posta in arrivo. Puoi comunque generare una bozza di risposta qui sotto.",
        "en": "IMAP is not configured — set IMAP_HOST, IMAP_USER, IMAP_PASSWORD in .env to read the inbox. You can still generate a draft reply below.",
    },
    "max_emails_label": {"it": "Numero massimo di email da elaborare", "en": "Maximum number of emails to process"},
    "check_inbox_btn": {"it": "Controlla posta in arrivo", "en": "Check inbox"},
    "reading_spinner": {"it": "Lettura e classificazione in corso...", "en": "Reading and classifying..."},
    "no_unread_emails": {"it": "Nessuna email non letta.", "en": "No unread emails."},
    "quick_draft_section": {"it": "Genera bozza rapida", "en": "Generate quick draft"},
    "subject_label": {"it": "Oggetto", "en": "Subject"},
    "message_text_label": {"it": "Testo del messaggio ricevuto", "en": "Received message text"},
    "generate_draft_btn": {"it": "Genera bozza di risposta", "en": "Generate draft reply"},
    "generating_spinner": {"it": "Generazione in corso...", "en": "Generating..."},

    # Approvals page
    "section_approvals": {"it": "Flusso di Approvazione", "en": "Approval Workflow"},
    "new_request_label": {"it": "**Nuova richiesta**", "en": "**New request**"},
    "title_label": {"it": "Titolo", "en": "Title"},
    "requester_label": {"it": "Richiedente", "en": "Requester"},
    "steps_label": {"it": "Passaggi (separati da virgola)", "en": "Steps (comma-separated)"},
    "create_request_btn": {"it": "Crea richiesta", "en": "Create request"},
    "request_created": {"it": "Richiesta creata — ID: {id}", "en": "Request created — ID: {id}"},
    "pending_requests": {"it": "Richieste in attesa", "en": "Pending requests"},
    "no_pending_requests": {"it": "Nessuna richiesta in attesa.", "en": "No pending requests."},
    "approval_card": {
        "it": "ID: {id} · Richiedente: {requester} · Step corrente: <strong>{owner}</strong> ({i}/{n})",
        "en": "ID: {id} · Requester: {requester} · Current step: <strong>{owner}</strong> ({i}/{n})",
    },
    "actor_placeholder": {"it": "Il tuo nome", "en": "Your name"},
    "approve_btn": {"it": "Approva", "en": "Approve"},
    "reject_btn": {"it": "Rifiuta", "en": "Reject"},
    "all_requests": {"it": "Tutte le richieste", "en": "All requests"},
    "id_col": {"it": "id", "en": "id"},
    "title_col": {"it": "titolo", "en": "title"},
    "status_col": {"it": "stato", "en": "status"},
    "updated_col": {"it": "aggiornato", "en": "updated"},

    # Ask Database page
    "section_ask_db": {"it": "Interroga il Database (voce o testo)", "en": "Voice-to-Database"},
    "db_target_label": {"it": "Database (percorso SQLite o DSN Postgres)", "en": "Database (SQLite path or Postgres DSN)"},
    "tab_text_question": {"it": "Domanda testuale", "en": "Text question"},
    "tab_voice_question": {"it": "Domanda vocale", "en": "Voice question"},
    "text_question_label": {"it": "Fai una domanda sui tuoi dati", "en": "Ask a question about your data"},
    "upload_audio_label": {"it": "Carica un file audio (wav/mp3)", "en": "Upload an audio file (wav/mp3)"},
    "audio_ready": {"it": "Audio pronto per la trascrizione.", "en": "Audio ready for transcription."},
    "run_query_btn": {"it": "Esegui interrogazione", "en": "Run query"},
    "processing_spinner": {"it": "Elaborazione in corso...", "en": "Processing..."},
    "transcript_label": {"it": "Trascrizione: {text}", "en": "Transcript: {text}"},
    "error_with_stage": {"it": "Errore (fase: {stage}): {error}", "en": "Error (stage: {stage}): {error}"},
    "generated_sql": {"it": "SQL generato", "en": "Generated SQL"},
    "no_rows_returned": {"it": "La query non ha restituito righe.", "en": "The query returned no rows."},

    # ETL page
    "section_etl": {"it": "ETL — Pulizia e Caricamento Dati", "en": "ETL — Data Cleaning and Loading"},
    "upload_csv_label": {"it": "Carica un file CSV o Excel", "en": "Upload a CSV or Excel file"},
    "destination_label": {"it": "Destinazione", "en": "Destination"},
    "table_name_label": {"it": "Nome tabella/foglio (opzionale)", "en": "Table/sheet name (optional)"},
    "clean_load_btn": {"it": "Pulisci e carica", "en": "Clean and load"},
    "cleaning_spinner": {"it": "Pulizia e caricamento in corso...", "en": "Cleaning and loading..."},
    "rows_loaded": {"it": "Caricate {n} righe in {dest}", "en": "Loaded {n} rows into {dest}"},
    "empty_rows_removed": {"it": "Righe vuote rimosse", "en": "Empty rows removed"},
    "cells_cleaned": {"it": "Celle ripulite", "en": "Cells cleaned"},
    "columns_renamed": {"it": "Colonne rinominate", "en": "Columns renamed"},

    # Reports page
    "section_reports": {"it": "Report", "en": "Reporting"},
    "period_label": {"it": "Periodo", "en": "Period"},
    "period_day": {"it": "Giorno", "en": "Day"},
    "period_week": {"it": "Settimana", "en": "Week"},
    "period_month": {"it": "Mese", "en": "Month"},
    "generate_report_btn": {"it": "Genera report", "en": "Generate report"},
    "generating_report_spinner": {"it": "Generazione del report...", "en": "Generating report..."},
    "documents_processed": {"it": "Documenti elaborati", "en": "Documents processed"},
    "approval_requests": {"it": "Richieste di approvazione", "en": "Approval requests"},
    "exported_to_label": {"it": "Esportato in:", "en": "Exported to:"},
}


def t(key: str, lang: str = "it", **kwargs) -> str:
    """Look up a translated UI string and format it with kwargs, if any."""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang, entry.get("it", key))
    return text.format(**kwargs) if kwargs else text

# Business Automation Agent

A unified AI agent for small businesses in Italy. One controller, six
modular skills, routed by natural language:
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bizautomationagent-ehjvbmyowjpx5qmvj38srt.streamlit.app/)
1. **Document processing** — extract structured fields from invoices,
   receipts, and contracts (PDF/TXT); validate; save to Excel/Sheets/Postgres;
   summarize.
2. **Email automation** — read the inbox, classify each message
   (fatturazione/assistenza/logistica/appuntamento), draft a reply, route it
   to the right person, and produce a short WhatsApp-style version.
3. **Approval workflow** — move a request through an ordered sequence of
   approval steps, notifying the next owner and tracking status.
4. **Voice-to-database** — ask a question by voice or text and get SQL
   results back, against SQLite or Postgres (ported from the Voice2Query
   project).
5. **ETL** — clean a CSV/Excel file (drop empty rows, trim whitespace,
   standardize column names) and load it into a sink.
6. **Reporting** — a periodic digest of what the agent has done.

## Architecture

```
controller.py   Agent: Gemini function-calling router over the 7 tools below
skills/         one module per workflow, plain functions, no I/O credentials baked in
adapters/       swappable I/O: llm, transcribe (Whisper), excel, sheets, postgres, email, whatsapp, http
memory.py       SQLite-backed state: conversation turns, workflow state, documents, approvals
config.py       loads .env into a single Settings object
```

Skills never call external services directly — they go through `adapters/`.
This means Postgres/Sheets/Email/WhatsApp can be swapped or added without
touching skill logic, and skills can be tested without real credentials.

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set at least `GEMINI_API_KEY` (get one at
https://aistudio.google.com/apikey). Everything else is optional — see the
**Safety and defaults** section below for what runs out of the box.

## Safety and defaults

- **`DRY_RUN=true` by default.** Sending email, sending WhatsApp messages, and
  calling the custom CRM/logistics API all log the composed message instead
  of transmitting it, until you set `DRY_RUN=false` and fill in real
  credentials.
- **Local-first storage.** `SINK=excel` (default) and the ETL `sqlite` sink
  need zero setup. Postgres and Google Sheets are opt-in via `.env`.
- **Voice input is optional.** `voice_to_db.ask()` accepts `text=` directly —
  the demo and the controller's `tool_ask_database` use text mode, so you
  don't need Whisper/ffmpeg/a microphone installed unless you want live audio
  (`pip install openai-whisper sounddevice scipy`, see the commented-out
  block in `requirements.txt`).

## Running it

```
pytest tests/            # pure-logic tests, no credentials needed
python demo.py            # end-to-end walkthrough, needs GEMINI_API_KEY
python cli.py              # interactive chat with the full agent, terminal
streamlit run app.py       # web dashboard: Chat page + one page per skill
```

`app.py` is a Streamlit dashboard with a **Chat** page (talks directly to the
`Agent` controller, same routing as `cli.py`) plus dedicated pages —
**Documents**, **Inbox**, **Approvals**, **Ask Database**, **ETL**,
**Reports** — with proper upload widgets, forms, and tables for each skill.
The ETL and Approvals pages work with no external credentials at all; the
rest need `GEMINI_API_KEY` and show an in-page warning if it's missing.

**Language:** a toggle in the sidebar switches the whole dashboard between
Italian and English (`i18n.py` holds the UI string table). It's not just the
labels — the selected language is passed through to Gemini, so chat replies,
document summaries, drafted email replies, and report text are generated in
that language too. Extracted invoice/receipt field *names* (numero_documento,
partita_iva, totale, etc.) always stay Italian regardless, since they're
canonical terms tied to the source documents, not UI chrome.

Example CLI prompts once running:
- "Estrai i dati dalla fattura in sample_data/sample_invoice.txt"
- "Crea una richiesta di approvazione per l'acquisto di un laptop, passaggi manager e finance"
- "Quanti clienti hanno sede a Napoli?" (after running the ETL step, which
  loads `sample_data/sample_customers.csv` into `data/warehouse.db`)

## Wiring up real integrations

| Integration | .env keys | Notes |
|---|---|---|
| Postgres | `POSTGRES_DSN` | SQLAlchemy DSN, e.g. `postgresql+psycopg2://user:pass@host:5432/db` |
| Google Sheets | `SHEETS_CREDENTIALS_PATH`, `SHEETS_SPREADSHEET_ID` | Service-account JSON; share the sheet with the service account's email as Editor |
| Email | `IMAP_*`, `SMTP_*`, `ROUTING_MAP` | Use an app password for Gmail/Outlook, not your normal login password |
| WhatsApp | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | Meta WhatsApp Business Cloud API; requires an approved business account |
| CRM/logistics | `CUSTOM_API_BASE_URL`, `CUSTOM_API_KEY` | Generic bearer-token REST client in `adapters/http_adapter.py` — adjust auth if your API differs |

## Italian-first design

Field names, classification categories, and LLM prompts are written for
Italian source documents and correspondence (Partita IVA, Imponibile, IVA,
Totale; fatturazione/assistenza/logistica/appuntamento) but handle English
input too — the LLM prompts don't hard-restrict the input language.

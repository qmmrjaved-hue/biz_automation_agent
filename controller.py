"""
controller.py — the unified agent: routes a free-text instruction to the
right skill(s) using Gemini automatic function calling, then returns a
natural-language reply. Every turn (and any workflow it triggers) is
persisted via memory.py so multi-step conversations keep context.

Public class:
  - Agent(session_id="default", language="it")
      .handle(user_input: str) -> str
"""

import memory
from adapters import llm_adapter
from skills import approval_workflow, document_processing, email_automation, etl, reporting, voice_to_db

_SYSTEM_PROMPT_IT = """
Sei l'assistente AI di automazione dei processi aziendali per una piccola
impresa italiana. Hai accesso a strumenti per: elaborare documenti
(fatture/ricevute/contratti), gestire la posta in arrivo, aprire e decidere
richieste di approvazione, interrogare un database a voce/testo, pulire e
caricare dati (ETL), e generare report periodici.

Usa lo strumento più adatto alla richiesta dell'utente. Se mancano
informazioni necessarie per usare uno strumento (es. il percorso di un
file), chiedile prima di procedere. Rispondi sempre in italiano, in modo
conciso.
"""

_SYSTEM_PROMPT_EN = """
You are the AI business-process-automation assistant for a small Italian
business. You have tools to: process documents (invoices/receipts/
contracts), handle the email inbox, open and decide approval requests,
query a database by voice/text, clean and load data (ETL), and generate
periodic reports.

Use whichever tool best matches the user's request. If information needed
to use a tool is missing (e.g. a file path), ask for it before proceeding.
Always reply in English, concisely.
"""


# ── Tool wrappers ──────────────────────────────────────────────────────────
# Gemini's automatic function calling reads each function's name, type
# hints, and Google-style docstring (Args: section) to decide when and how
# to call it, then executes it locally and feeds the JSON-serializable
# return value back into the conversation. `language` is bound via closure
# from the Agent's own setting, not exposed as a tool parameter — the LLM
# shouldn't need to guess the UI's language.

def _build_tools(language: str) -> list:

    def tool_process_document(file_path: str, sink: str = "excel") -> dict:
        """Estrae i campi da una fattura, ricevuta o contratto (PDF o TXT) e li salva.

        Args:
            file_path: Percorso del file PDF o TXT da elaborare.
            sink: Dove salvare i dati estratti: "excel", "sheets" o "postgres".
        """
        doc = document_processing.process_document(file_path, sink=sink, language=language)
        return {"doc_type": doc.doc_type, "fields": doc.fields, "summary": doc.summary, "saved_to": doc.saved_to}

    def tool_handle_inbox(limit: int = 10) -> dict:
        """Legge le email non lette, le classifica, prepara risposte e le instrada al responsabile giusto.

        Args:
            limit: Numero massimo di email da elaborare.
        """
        results = email_automation.handle_inbox(limit=limit, language=language)
        return {"processed": len(results), "items": [r.__dict__ for r in results]}

    def tool_create_approval(title: str, requester: str, steps: str) -> dict:
        """Crea una nuova richiesta di approvazione con una sequenza di passaggi.

        Args:
            title: Titolo o descrizione della richiesta.
            requester: Chi richiede l'approvazione.
            steps: Elenco dei responsabili separati da virgola, in ordine (es. "manager,finance").
        """
        step_list = [s.strip() for s in steps.split(",") if s.strip()]
        approval = approval_workflow.create_request(title, requester, step_list)
        return {"request_id": approval.request_id, "status": approval.status, "steps": approval.steps}

    def tool_decide_approval(request_id: str, decision: str, actor: str) -> dict:
        """Approva o rifiuta il passaggio corrente di una richiesta di approvazione.

        Args:
            request_id: ID della richiesta da aggiornare.
            decision: "approve" oppure "reject".
            actor: Chi prende la decisione.
        """
        approval = approval_workflow.decide(request_id, decision, actor)
        return {"request_id": approval.request_id, "status": approval.status,
                 "current_step_index": approval.current_step_index}

    def tool_ask_database(db_target: str, question: str) -> dict:
        """Risponde a una domanda in linguaggio naturale interrogando un database SQLite o Postgres.

        Args:
            db_target: Percorso del file SQLite, oppure DSN Postgres (postgresql+psycopg2://...).
            question: La domanda in linguaggio naturale.
        """
        result = voice_to_db.ask(db_target=db_target, text=question)
        df = result.get("results")
        return {
            "sql": result.get("sql"),
            "error": result.get("error"),
            "rows": df.to_dict(orient="records") if df is not None else None,
        }

    def tool_clean_and_load(file_path: str, sink: str = "sqlite", table_name: str = "") -> dict:
        """Pulisce un file CSV/Excel (righe vuote, spazi, nomi colonne) e lo carica in un sink.

        Args:
            file_path: Percorso del file CSV o XLSX da pulire e caricare.
            sink: Destinazione dei dati puliti: "excel", "sheets", "postgres" o "sqlite".
            table_name: Nome opzionale della tabella/foglio di destinazione; se vuoto, deriva dal nome del file.
        """
        return etl.clean_and_load(file_path, sink=sink, table_name=table_name or None)

    def tool_generate_report(period: str = "week") -> dict:
        """Genera un report riepilogativo delle attività dell'agente in un periodo.

        Args:
            period: "day", "week" oppure "month".
        """
        return reporting.generate_report(period, language=language)

    return [
        tool_process_document,
        tool_handle_inbox,
        tool_create_approval,
        tool_decide_approval,
        tool_ask_database,
        tool_clean_and_load,
        tool_generate_report,
    ]


class Agent:
    """Stateful conversational wrapper around the tool-calling controller."""

    def __init__(self, session_id: str = "default", language: str = "it"):
        self.session_id = session_id
        self.language = language
        self.tools = _build_tools(language)

    def handle(self, user_input: str) -> str:
        """
        Process one turn of conversation: log the user's message, let Gemini
        route it to zero or more tools, and return the final natural-language
        reply (also logged).

        Args:
            user_input: The user's free-text instruction or question.

        Returns:
            The agent's natural-language reply.

        Raises:
            EnvironmentError: if GEMINI_API_KEY is not set.
        """
        memory.log_turn(self.session_id, "user", user_input)

        history = memory.recent_turns(self.session_id, limit=10)
        contents = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)

        system_prompt = _SYSTEM_PROMPT_EN if self.language == "en" else _SYSTEM_PROMPT_IT
        reply = llm_adapter.generate_with_tools(
            contents=contents,
            tools=self.tools,
            system_instruction=system_prompt,
        )

        memory.log_turn(self.session_id, "assistant", reply)
        return reply

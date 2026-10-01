"""
voice_to_db.py — voice or text question -> SQL -> results, against either a
local SQLite file or a Postgres database. This is a generalized port of
Voice2Query's pipeline.py / schema_loader.py / error_correction.py /
text_to_sql.py / query_executor.py, adapted to plug into this agent's
llm_adapter and postgres_adapter instead of standing alone.

Stages: audio (optional) -> transcribe -> schema-aware correction ->
text-to-SQL -> execute.

Public function:
  - ask(db_target, audio_path=None, text=None, language=None, correction_cutoff=0.8) -> dict
"""

import difflib
import sqlite3
import traceback

import pandas as pd

from adapters import llm_adapter, postgres_adapter, transcribe_adapter

_SQL_RULES = (
    "Sei un esperto assistente SQL. Converti la domanda dell'utente in una "
    "query SQL valida (SQLite o Postgres, secondo lo schema fornito).\n\n"
    "Regole:\n"
    "- Restituisci SOLO la query SQL, nient'altro.\n"
    "- Nessun blocco markdown, nessuna spiegazione.\n"
    "- Usa solo le tabelle e le colonne definite nello schema sottostante.\n"
    "- Usa sempre JOIN espliciti, mai join impliciti con virgola.\n"
    "- Termina ogni query con un punto e virgola.\n\n"
)


def _is_postgres(db_target: str) -> bool:
    return db_target.startswith("postgresql") or db_target.startswith("postgres://")


def _sqlite_schema_prompt(db_path: str) -> str:
    """Build a schema description string from a SQLite file (ported from Voice2Query's schema_loader)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    lines = ["Database schema:\n"]
    for table in tables:
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table,)
        )
        ddl_row = cursor.fetchone()
        lines.append(f"Table: {table}")
        lines.append(ddl_row[0] if ddl_row else "")
        lines.append("")
    conn.close()
    return "\n".join(lines).strip()


def _sqlite_vocabulary(db_path: str) -> list:
    """Collect table/column names and sample text values for fuzzy correction."""
    vocabulary = set()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        vocabulary.add(table)
        cursor.execute(f"PRAGMA table_info('{table}');")
        columns = [row[1] for row in cursor.fetchall()]
        vocabulary.update(columns)
        for col in columns:
            try:
                cursor.execute(
                    f'SELECT DISTINCT "{col}" FROM "{table}" '
                    f'WHERE typeof("{col}") = \'text\' LIMIT 100;'
                )
                for (val,) in cursor.fetchall():
                    if val:
                        vocabulary.add(str(val))
            except sqlite3.OperationalError:
                pass
    conn.close()
    return sorted(vocabulary)


def _correct_transcript(transcript: str, vocabulary: list, cutoff: float = 0.8) -> str:
    """Fuzzy-repair ASR errors by replacing words that closely match known schema/vocabulary terms."""
    vocab_lower = [v.lower() for v in vocabulary]
    corrected_words = []
    for word in transcript.split():
        cleaned = word.strip(".,!?;:'\"").lower()
        matches = difflib.get_close_matches(cleaned, vocab_lower, n=1, cutoff=cutoff)
        if matches and matches[0] != cleaned:
            original_case = next((v for v in vocabulary if v.lower() == matches[0]), matches[0])
            corrected_words.append(original_case)
        else:
            corrected_words.append(word)
    return " ".join(corrected_words)


def _generate_sql(question: str, schema_prompt: str) -> str:
    return llm_adapter.generate_text(
        prompt=f"{_SQL_RULES}{schema_prompt}\n\nDomanda: {question}\nSQL:"
    )


def _execute_sqlite(sql: str, db_path: str) -> pd.DataFrame:
    stripped = sql.strip().lstrip(";")
    if not stripped.upper().startswith("SELECT"):
        raise ValueError(f"[voice_to_db] Only SELECT queries are allowed. Got: {sql!r}")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df


def _fail(state: dict, stage: str, exc: Exception) -> dict:
    state["stage"] = stage
    state["error"] = f"{type(exc).__name__}: {exc}"
    print(f"[voice_to_db] ERROR in stage '{stage}': {exc}")
    print(traceback.format_exc())
    return state


def ask(
    db_target: str,
    audio_path: str = None,
    text: str = None,
    language: str = None,
    correction_cutoff: float = 0.8,
) -> dict:
    """
    Answer a natural-language question against a database using voice or text.

    Args:
        db_target:          A SQLite file path, or a Postgres SQLAlchemy DSN
                            (postgresql+psycopg2://...).
        audio_path:         Path to an audio file to transcribe. Ignored if `text` is given.
        text:               Plain-text question, bypassing audio/transcription. Takes priority.
        language:           ISO-639-1 language code for Whisper (e.g. "it"). None = auto-detect.
        correction_cutoff:  Fuzzy-match threshold (0-1) for transcript correction. SQLite only.

    Returns:
        {
            "transcript": str | None, "corrected": str | None, "sql": str | None,
            "results": pandas.DataFrame | None, "error": str | None, "stage": str | None,
        }
    """
    state = {"transcript": None, "corrected": None, "sql": None, "results": None,
              "error": None, "stage": None}
    is_pg = _is_postgres(db_target)

    if text is not None:
        state["transcript"] = text
        state["corrected"] = text
    else:
        if audio_path is None:
            return _fail(state, "audio_input", ValueError("Either 'audio_path' or 'text' must be provided."))
        try:
            state["transcript"] = transcribe_adapter.transcribe(audio_path=audio_path, language=language)
        except Exception as e:
            return _fail(state, "transcribe", e)

        try:
            if is_pg:
                state["corrected"] = state["transcript"]  # vocabulary-based correction is SQLite-only for now
            else:
                vocabulary = _sqlite_vocabulary(db_target)
                state["corrected"] = _correct_transcript(state["transcript"], vocabulary, correction_cutoff)
        except Exception as e:
            return _fail(state, "error_correction", e)

    try:
        schema_prompt = postgres_adapter.format_schema_for_prompt(db_target) if is_pg \
            else _sqlite_schema_prompt(db_target)
        state["sql"] = _generate_sql(state["corrected"], schema_prompt)
    except Exception as e:
        return _fail(state, "text_to_sql", e)

    try:
        state["results"] = postgres_adapter.execute_select(state["sql"], db_target) if is_pg \
            else _execute_sqlite(state["sql"], db_target)
    except Exception as e:
        return _fail(state, "query_executor", e)

    return state

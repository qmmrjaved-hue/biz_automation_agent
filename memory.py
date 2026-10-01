"""
memory.py — SQLite-backed persistent state for the agent.

Tracks conversation turns (for multi-step context), workflow state per
skill run, extracted documents, and approval requests. This is the agent's
"memory": every skill result worth remembering later is written here.

Public functions:
  - log_turn(session_id, role, content) -> None
  - recent_turns(session_id, limit=10) -> list[dict]
  - save_workflow_state(workflow_id, skill, status, payload) -> None
  - get_workflow_state(workflow_id) -> dict | None
  - save_extracted_document(doc) -> int
  - list_extracted_documents(since=None) -> list[dict]
  - save_approval(approval) -> None
  - load_approval(request_id) -> dict | None
  - list_approvals(status=None) -> list[dict]
"""

import json
import sqlite3
from datetime import datetime, timedelta

from config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_state (
    workflow_id TEXT PRIMARY KEY,
    skill TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extracted_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    summary TEXT NOT NULL,
    saved_to TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    request_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    requester TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    current_step_index INTEGER NOT NULL,
    status TEXT NOT NULL,
    history_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.memory_db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def log_turn(session_id: str, role: str, content: str) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?);",
        (session_id, role, content, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def recent_turns(session_id: str, limit: int = 10) -> list:
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content, created_at FROM conversations "
        "WHERE session_id = ? ORDER BY id DESC LIMIT ?;",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def save_workflow_state(workflow_id: str, skill: str, status: str, payload: dict) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO workflow_state (workflow_id, skill, status, payload_json, updated_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(workflow_id) DO UPDATE SET "
        "skill=excluded.skill, status=excluded.status, "
        "payload_json=excluded.payload_json, updated_at=excluded.updated_at;",
        (workflow_id, skill, status, json.dumps(payload), datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def get_workflow_state(workflow_id: str) -> dict:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM workflow_state WHERE workflow_id = ?;", (workflow_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    result["payload"] = json.loads(result.pop("payload_json"))
    return result


def save_extracted_document(doc) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO extracted_documents (source_file, doc_type, fields_json, summary, saved_to, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (doc.source_file, doc.doc_type, json.dumps(doc.fields), doc.summary, doc.saved_to, doc.created_at),
    )
    conn.commit()
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def list_extracted_documents(since_days: int = None) -> list:
    conn = _connect()
    if since_days is not None:
        cutoff = (datetime.now() - timedelta(days=since_days)).isoformat(timespec="seconds")
        rows = conn.execute(
            "SELECT * FROM extracted_documents WHERE created_at >= ? ORDER BY id DESC;",
            (cutoff,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM extracted_documents ORDER BY id DESC;").fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        d["fields"] = json.loads(d.pop("fields_json"))
        results.append(d)
    return results


def save_approval(approval) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO approvals (request_id, title, requester, steps_json, current_step_index, "
        "status, history_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(request_id) DO UPDATE SET "
        "current_step_index=excluded.current_step_index, status=excluded.status, "
        "history_json=excluded.history_json, updated_at=excluded.updated_at;",
        (
            approval.request_id, approval.title, approval.requester,
            json.dumps(approval.steps), approval.current_step_index, approval.status,
            json.dumps(approval.history), approval.created_at, approval.updated_at,
        ),
    )
    conn.commit()
    conn.close()


def load_approval(request_id: str) -> dict:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM approvals WHERE request_id = ?;", (request_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["steps"] = json.loads(d.pop("steps_json"))
    d["history"] = json.loads(d.pop("history_json"))
    return d


def list_approvals(status: str = None) -> list:
    conn = _connect()
    if status:
        rows = conn.execute(
            "SELECT * FROM approvals WHERE status = ? ORDER BY updated_at DESC;", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM approvals ORDER BY updated_at DESC;").fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        d["steps"] = json.loads(d.pop("steps_json"))
        d["history"] = json.loads(d.pop("history_json"))
        results.append(d)
    return results

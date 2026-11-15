"""SQLite store: journey state per user, the audit trail and the consent log.

The database is rebuilt from the persona files on every start, so a restart is a clean demo.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time

from .config import DB_PATH

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS state (user_id TEXT PRIMARY KEY, json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ts REAL,
                kind TEXT, title TEXT, detail TEXT);
            CREATE TABLE IF NOT EXISTS consent_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ts REAL,
                scope TEXT, detail TEXT);
            """
        )


def clear(user_id: str | None = None) -> None:
    with _lock, _conn() as c:
        for table in ("state", "audit_log", "consent_log"):
            if user_id:
                c.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            else:
                c.execute(f"DELETE FROM {table}")


def get_state(user_id: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute("SELECT json FROM state WHERE user_id = ?", (user_id,)).fetchone()
    return json.loads(row["json"]) if row else None


def save_state(state: dict) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO state (user_id, json) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET json = excluded.json",
            (state["user_id"], json.dumps(state, ensure_ascii=False)),
        )


def trace(user_id: str, kind: str, title: str, detail: str = "") -> None:
    """kind: event | lender | rule | tool | llm | guard | consent | voice | nudge"""
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO audit_log (user_id, ts, kind, title, detail) VALUES (?, ?, ?, ?, ?)",
            (user_id, time.time(), kind, title, detail),
        )


def get_trace(user_id: str, after: int = 0) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT id, ts, kind, title, detail FROM audit_log WHERE user_id = ? AND id > ? ORDER BY id",
            (user_id, after),
        ).fetchall()
    return [dict(r) for r in rows]


def consent(user_id: str, scope: str, detail: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO consent_log (user_id, ts, scope, detail) VALUES (?, ?, ?, ?)",
            (user_id, time.time(), scope, detail),
        )
    trace(user_id, "consent", f"Consent recorded: {scope}", detail)


def get_consents(user_id: str) -> list[dict]:
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT ts, scope, detail FROM consent_log WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]

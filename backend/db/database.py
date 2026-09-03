"""
SQLite storage for Checkpoint.

Deliberately plain: sqlite3 + JSON columns for nested fields, no ORM.
Per the spec, don't add Postgres/Redis unless it becomes genuinely
necessary — for a single-agent MVP demo this is more than enough.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent / "checkpoint.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    runtime_handle TEXT
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    snapshot_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    note TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    checkpoint_id TEXT,
    type TEXT NOT NULL,
    intent TEXT NOT NULL,
    target TEXT,
    parameters TEXT NOT NULL,
    reversible INTEGER NOT NULL,
    status TEXT NOT NULL,
    risk_score INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    diff TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS risk_findings (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    severity INTEGER NOT NULL,
    message TEXT NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY (action_id) REFERENCES actions(id)
);

CREATE TABLE IF NOT EXISTS rollback_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dumps(value) -> str:
    return json.dumps(value, default=str)


def loads(value: str | None):
    if value is None:
        return None
    return json.loads(value)

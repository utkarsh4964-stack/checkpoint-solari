"""
Checkpoint UI state bridge.

The core Checkpoint runtime remains responsible for actually executing
actions, snapshots, diffs, risk analysis and recovery.

This module only keeps a lightweight in-memory representation of the
currently running session so the Next.js dashboard can observe it.

No database is required for the demo UI.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


_lock = threading.Lock()

_sessions: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def create_session(
    agent_id: str = "workspace-agent",
    runtime: str = "solari_sandbox",
    task: str = "",
) -> dict[str, Any]:

    session_id = _new_id("sess")

    session = {
        "id": session_id,
        "agent_id": agent_id,
        "runtime": runtime,
        "status": "running",
        "task": task,
        "started_at": _now(),
        "ended_at": None,

        "actions": [],
        "checkpoints": [],
        "rollback_events": [],

        "stats": {
            "actions": 0,
            "checkpoints": 0,
            "blocked": 0,
            "paused": 0,
            "rollback": 0,
            "permanent_damage": 0,
        },

        "current_action_id": None,
        "last_update": _now(),
    }

    with _lock:
        _sessions[session_id] = session

    add_event(
        session_id=session_id,
        title="Session started",
        description="Checkpoint interceptor is active",
        status="running",
        risk=0,
        action_type="session.start",
        intent=task or "Tracked agent session",
        actual="Session initialized",
    )

    return get_session(session_id)


def get_session(session_id: str) -> dict[str, Any] | None:
    with _lock:
        session = _sessions.get(session_id)

        if session is None:
            return None

        return _copy(session)


def get_latest_session() -> dict[str, Any] | None:
    with _lock:
        if not _sessions:
            return None

        latest = max(
            _sessions.values(),
            key=lambda item: item.get("started_at", 0),
        )

        return _copy(latest)


def list_sessions() -> list[dict[str, Any]]:
    with _lock:
        sessions = list(_sessions.values())

    sessions.sort(
        key=lambda item: item.get("started_at", 0),
        reverse=True,
    )

    return [_copy(item) for item in sessions]


def add_event(
    session_id: str,
    title: str,
    description: str = "",
    status: str = "completed",
    risk: int = 0,
    action_type: str = "unknown",
    intent: str = "",
    actual: str = "",
    findings: list[dict[str, Any]] | None = None,
    diff: list[dict[str, Any]] | None = None,
    checkpoint_id: str | None = None,
    snapshot_id: str | None = None,
    command: str | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:

    with _lock:

        session = _sessions.get(session_id)

        if session is None:
            raise KeyError(f"Unknown session: {session_id}")

        action_number = len(session["actions"]) + 1

        action_id = _new_id("act")

        if checkpoint_id is None and status not in {
            "blocked",
            "session",
        }:
            checkpoint_id = _new_id("chk")

        event = {
            "id": action_id,
            "sequence": action_number,
            "title": title,
            "description": description,
            "status": status,
            "risk": max(0, min(100, int(risk or 0))),
            "type": action_type,
            "intent": intent,
            "actual": actual,
            "command": command,

            "timestamp": _now(),
            "duration_ms": duration_ms,

            "checkpoint_id": checkpoint_id,
            "snapshot_id": snapshot_id,

            "findings": findings or [],
            "diff": diff or [],

            "before_snapshot": snapshot_id,

            "result": None,
        }

        session["actions"].append(event)

        session["stats"]["actions"] += 1

        if status == "blocked":
            session["stats"]["blocked"] += 1

        if status == "paused":
            session["stats"]["paused"] += 1

        if checkpoint_id:
            existing = next(
                (
                    cp
                    for cp in session["checkpoints"]
                    if cp["id"] == checkpoint_id
                ),
                None,
            )

            if existing is None:
                session["checkpoints"].append(
                    {
                        "id": checkpoint_id,
                        "sequence": len(session["checkpoints"]) + 1,
                        "snapshot_id": snapshot_id,
                        "created_at": _now(),
                        "action_id": action_id,
                    }
                )

                session["stats"]["checkpoints"] += 1

        session["current_action_id"] = action_id
        session["last_update"] = _now()

        return _copy(event)


def update_event(
    session_id: str,
    action_id: str,
    **updates: Any,
) -> dict[str, Any] | None:

    with _lock:

        session = _sessions.get(session_id)

        if session is None:
            return None

        for action in session["actions"]:
            if action["id"] == action_id:

                for key, value in updates.items():
                    if value is not None:
                        action[key] = value

                action["timestamp"] = _now()

                session["last_update"] = _now()

                return _copy(action)

    return None


def add_rollback(
    session_id: str,
    checkpoint_id: str,
    reason: str,
    files_restored: int = 0,
) -> dict[str, Any]:

    with _lock:

        session = _sessions.get(session_id)

        if session is None:
            raise KeyError(f"Unknown session: {session_id}")

        event = {
            "id": _new_id("rollback"),
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
            "reason": reason,
            "files_restored": files_restored,
            "timestamp": _now(),
        }

        session["rollback_events"].append(event)

        session["stats"]["rollback"] += 1
        session["stats"]["permanent_damage"] = 0

        session["last_update"] = _now()

        return _copy(event)


def finish_session(
    session_id: str,
    status: str = "completed",
) -> dict[str, Any] | None:

    with _lock:

        session = _sessions.get(session_id)

        if session is None:
            return None

        session["status"] = status
        session["ended_at"] = _now()
        session["last_update"] = _now()

        return _copy(session)


def clear_sessions() -> None:
    with _lock:
        _sessions.clear()


def _copy(value: Any) -> Any:
    """
    Cheap deep-copy for JSON-compatible dictionaries/lists.
    """

    import json

    return json.loads(json.dumps(value))
"""
Checkpoint Python SDK — deliberately narrow (per spec: don't build a
universal framework-agnostic SDK for the challenge).

This talks to the Checkpoint backend over HTTP so an agent process can
be fully decoupled from the backend's internals. For the demo you can
also skip HTTP and use CheckpointManager directly in-process — see
examples/workspace_agent.py for both patterns.

Desired developer experience (from the spec):

    from checkpoint import Checkpoint

    checkpoint = Checkpoint(api_key=CHECKPOINT_KEY, solari_api_key=SOLARI_KEY)
    session = checkpoint.start_session(agent_id="workspace-agent", runtime="solari_sandbox")
    result = await session.run(intent="Clean temporary files", action=agent_action)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx


@dataclass
class ActionResult:
    id: str
    status: str
    risk_score: int
    raw: dict[str, Any]


class CheckpointSession:
    def __init__(self, client: "Checkpoint", session_id: str):
        self._client = client
        self.session_id = session_id

    def run(self, intent: str, type: str, target: str | None = None,
            parameters: dict | None = None) -> ActionResult:
        """
        Submit one action through Checkpoint. Blocks until the action
        completes (or is blocked/paused) — no separate poll step needed
        for the MVP's synchronous flow.
        """
        resp = self._client._http.post(
            f"/sessions/{self.session_id}/actions",
            json={
                "session_id": self.session_id,
                "type": type,
                "intent": intent,
                "target": target,
                "parameters": parameters or {},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return ActionResult(id=data["id"], status=data["status"], risk_score=data["risk_score"], raw=data)

    def approve(self, action_id: str) -> ActionResult:
        resp = self._client._http.post(f"/actions/{action_id}/approve")
        resp.raise_for_status()
        data = resp.json()
        return ActionResult(id=data["id"], status=data["status"], risk_score=data["risk_score"], raw=data)

    def reject(self, action_id: str, rollback: bool = True) -> ActionResult:
        resp = self._client._http.post(f"/actions/{action_id}/reject", params={"rollback": rollback})
        resp.raise_for_status()
        data = resp.json()
        return ActionResult(id=data["id"], status=data["status"], risk_score=data["risk_score"], raw=data)

    def timeline(self) -> dict:
        resp = self._client._http.get(f"/sessions/{self.session_id}/timeline")
        resp.raise_for_status()
        return resp.json()

    def end(self, status_ok: bool = True) -> None:
        resp = self._client._http.post(f"/sessions/{self.session_id}/end", params={"status_ok": status_ok})
        resp.raise_for_status()


class Checkpoint:
    """Entry point for the SDK. Points at a running Checkpoint backend."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "http://localhost:8000"):
        self.api_key = api_key  # reserved for auth once the backend needs it
        self._http = httpx.Client(base_url=base_url, timeout=30.0)

    def start_session(self, agent_id: str, runtime: str = "solari_sandbox",
                       task_description: str = "") -> CheckpointSession:
        resp = self._http.post(
            "/sessions", json={"agent_id": agent_id, "task_description": task_description}
        )
        resp.raise_for_status()
        session_id = resp.json()["id"]
        return CheckpointSession(self, session_id)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import registry
from backend.core.checkpoint_manager import CheckpointManager
from backend.db import repositories as repo
from backend.models.schemas import Session

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    agent_id: str
    task_description: str = ""


@router.post("", response_model=Session)
def start_session(req: StartSessionRequest) -> Session:
    manager = CheckpointManager(task_description=req.task_description)
    session = manager.start_session(agent_id=req.agent_id)
    registry.register(session.id, manager)
    return session


@router.get("/{session_id}", response_model=Session)
def get_session(session_id: str) -> Session:
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.post("/{session_id}/end")
def end_session(session_id: str, status_ok: bool = True):
    manager = registry.get(session_id)
    if not manager:
        raise HTTPException(404, "No active manager for this session (already ended or unknown)")
    manager.end_session(status_ok=status_ok)
    registry.remove(session_id)
    return {"status": "ended"}


@router.get("/{session_id}/timeline")
def get_timeline(session_id: str):
    actions = repo.list_actions(session_id)
    checkpoints = repo.list_checkpoints(session_id)
    rollbacks = repo.list_rollback_events(session_id)
    entries = []
    for action in actions:
        entries.append({
            "action": action.model_dump(),
            "findings": [f.model_dump() for f in repo.list_findings(action.id)],
        })
    return {
        "session_id": session_id,
        "actions": entries,
        "checkpoints": [c.model_dump() for c in checkpoints],
        "rollback_events": [r.model_dump() for r in rollbacks],
        "summary": {
            "total_actions": len(actions),
            "total_checkpoints": len(checkpoints),
            "blocked_actions": sum(1 for a in actions if a.status.value == "blocked"),
            "rollbacks": len(rollbacks),
        },
    }

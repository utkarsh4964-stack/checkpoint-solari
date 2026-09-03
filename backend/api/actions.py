from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import registry
from backend.db import repositories as repo
from backend.models.schemas import ActionType, AgentAction

router = APIRouter(tags=["actions"])


class SubmitActionRequest(BaseModel):
    session_id: str
    type: ActionType
    intent: str
    target: str | None = None
    parameters: dict = {}


@router.post("/sessions/{session_id}/actions", response_model=AgentAction)
def submit_action(session_id: str, req: SubmitActionRequest) -> AgentAction:
    manager = registry.get(session_id)
    if not manager:
        raise HTTPException(404, "No active session/manager")
    return manager.submit_action(
        type=req.type, intent=req.intent, target=req.target, parameters=req.parameters
    )


@router.get("/actions/{action_id}", response_model=AgentAction)
def get_action(action_id: str) -> AgentAction:
    action = repo.get_action(action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    return action


@router.get("/actions/{action_id}/risk")
def get_action_risk(action_id: str):
    action = repo.get_action(action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    findings = repo.list_findings(action_id)
    return {
        "action_id": action_id,
        "risk_score": action.risk_score,
        "status": action.status,
        "findings": [f.model_dump() for f in findings],
    }


@router.post("/actions/{action_id}/approve", response_model=AgentAction)
def approve_action(action_id: str) -> AgentAction:
    action = repo.get_action(action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    manager = registry.get(action.session_id)
    if not manager:
        raise HTTPException(404, "No active session/manager")
    return manager.approve_action(action_id)


@router.post("/actions/{action_id}/reject", response_model=AgentAction)
def reject_action(action_id: str, rollback: bool = True) -> AgentAction:
    action = repo.get_action(action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    manager = registry.get(action.session_id)
    if not manager:
        raise HTTPException(404, "No active session/manager")
    return manager.reject_action(action_id, rollback=rollback)

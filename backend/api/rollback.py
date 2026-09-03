from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import registry
from backend.models.schemas import RollbackEvent, RollbackTrigger

router = APIRouter(prefix="/sessions", tags=["rollback"])


class RollbackRequest(BaseModel):
    reason: str = "Manual rollback requested"


@router.post("/{session_id}/rollback/{checkpoint_id}", response_model=RollbackEvent)
def rollback_to_checkpoint(session_id: str, checkpoint_id: str, req: RollbackRequest) -> RollbackEvent:
    manager = registry.get(session_id)
    if not manager:
        raise HTTPException(404, "No active session/manager")
    return manager.rollback(checkpoint_id, reason=req.reason, trigger=RollbackTrigger.MANUAL)

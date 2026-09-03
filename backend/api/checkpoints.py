from fastapi import APIRouter, HTTPException

from backend.db import repositories as repo
from backend.models.schemas import Checkpoint

router = APIRouter(prefix="/sessions", tags=["checkpoints"])


@router.get("/{session_id}/checkpoints", response_model=list[Checkpoint])
def list_checkpoints(session_id: str) -> list[Checkpoint]:
    return repo.list_checkpoints(session_id)


@router.get("/checkpoints/{checkpoint_id}", response_model=Checkpoint)
def get_checkpoint(checkpoint_id: str) -> Checkpoint:
    cp = repo.get_checkpoint(checkpoint_id)
    if not cp:
        raise HTTPException(404, "Checkpoint not found")
    return cp

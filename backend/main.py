from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import init_db
from backend.api import actions, checkpoints, rollback, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the SQLite database when FastAPI starts.
    """
    init_db()
    yield


app = FastAPI(
    title="Checkpoint",
    description="Git for AI agent actions.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
#
# The Next.js frontend normally runs on:
#
#     http://localhost:3000
#
# FastAPI normally runs on:
#
#     http://127.0.0.1:8000
#
# Allow both localhost and 127.0.0.1 during local development.
#

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------------------------
#
# Primary routes:
#
#     /sessions
#     /sessions/{id}
#     /sessions/{id}/timeline
#     /sessions/{id}/checkpoints
#     /sessions/{id}/rollback/{checkpoint_id}
#     /actions/{id}
#     /actions/{id}/risk
#     /actions/{id}/approve
#     /actions/{id}/reject
#
# We also expose the exact same routes under /api.
#
# This makes the backend tolerant of either frontend convention:
#
#     http://localhost:8000/sessions/...
#
# or:
#
#     http://localhost:8000/api/sessions/...
#
# This specifically prevents the frontend 404 problem you were seeing.
#

app.include_router(sessions.router)
app.include_router(actions.router)
app.include_router(checkpoints.router)
app.include_router(rollback.router)

# /api aliases
app.include_router(
    sessions.router,
    prefix="/api",
)

app.include_router(
    actions.router,
    prefix="/api",
)

app.include_router(
    checkpoints.router,
    prefix="/api",
)

app.include_router(
    rollback.router,
    prefix="/api",
)


# ---------------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "Checkpoint",
        "tagline": "Git for AI agent actions.",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "checkpoint-api",
    }


@app.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "service": "checkpoint-api",
    }
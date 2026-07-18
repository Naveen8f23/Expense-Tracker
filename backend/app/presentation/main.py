import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.bootstrap import ensure_default_user, ensure_hdfc_sender_rules
from app.infrastructure.db import SessionLocal
from app.presentation.gmail_router import router as gmail_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Baseline config data (BACKLOG.md A2/B2) must exist whenever the app is actually running,
    # not just lazily on first use -- migrations (alembic upgrade head) still only run via
    # scripts/setup.py, this only ensures rows, never touches schema.
    session = SessionLocal()
    try:
        ensure_default_user(session)
        ensure_hdfc_sender_rules(session)
    finally:
        session.close()
    yield


app = FastAPI(title="Expense Tracker API", lifespan=lifespan)
app.include_router(gmail_router)

# Local-first, single-user (ADR-0002): the only expected caller is our own dashboard,
# running on a different dev port (Vite) or later served by this same backend. Origins are
# configurable via env var rather than hardcoded, per the platform-independence goal (ADR-0015).
_allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

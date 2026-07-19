import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.infrastructure.bootstrap import ensure_default_user, ensure_hdfc_sender_rules
from app.infrastructure.db import SessionLocal
from app.infrastructure.sync_scheduler import SyncScheduler
from app.presentation.categories_router import router as categories_router
from app.presentation.gmail_router import router as gmail_router
from app.presentation.needs_review_router import router as needs_review_router
from app.presentation.sync_router import router as sync_router
from app.presentation.transactions_router import router as transactions_router

_scheduler = SyncScheduler()


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
    _scheduler.start()
    yield
    _scheduler.stop()


app = FastAPI(title="Expense Tracker API", lifespan=lifespan)
app.include_router(gmail_router)
app.include_router(transactions_router)
app.include_router(needs_review_router)
app.include_router(categories_router)
app.include_router(sync_router)

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


# Serves the built dashboard (`npm run build` -> frontend/dist) so a real deployment (e.g. the
# VM, ADR-0019/0020) is one process on one port -- no separate Vite dev server, no CORS needed
# for that origin. Mounted last and only if the build exists, so `npm run dev` (a separate origin,
# already covered by the CORS middleware above) keeps working unchanged for local development,
# and the test suite (which never builds the frontend) is unaffected.
_frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="dashboard")

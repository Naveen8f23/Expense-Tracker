import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Expense Tracker API")

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

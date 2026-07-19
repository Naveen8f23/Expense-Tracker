"""SyncScheduler (ARCHITECTURE.md #3's previously-deferred Ingestion component; ADR-0013:
"a simple in-process timer... no external job queue").

Runs the existing sync + classify/extract pipeline on a background thread so new transactions
appear without a manual "sync now" action. A plain `threading.Thread`, not asyncio: the pipeline
(SQLAlchemy sessions, google-api-python-client calls) is fully synchronous/blocking, and running
it in its own OS thread keeps FastAPI's async event loop free without rewriting that pipeline.

Interval default (5s) and rationale: Gmail's per-user rate limit (250 quota units/second) makes
even 1-second polling technically safe -- the real latency floor is the bank's own email delivery
lag, not our poll granularity. 5 seconds is fast enough to feel instant to a human watching the
dashboard while still being a sane, low-churn default; configurable via SYNC_POLL_INTERVAL_SECONDS
for anyone who wants to tune it either direction.
"""

import logging
import os
import threading

from app.application.run_classify_and_extract import run_classify_and_extract
from app.application.run_incremental_sync import NoSyncCheckpointError, run_incremental_sync
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import SessionLocal
from app.infrastructure.models import GmailConnection

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = float(os.environ.get("SYNC_POLL_INTERVAL_SECONDS", "5"))


class SyncScheduler:
    def __init__(self, interval_seconds: float = DEFAULT_INTERVAL_SECONDS):
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="sync-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)
            self._thread = None

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                run_sync_cycle()
            except Exception:  # noqa: BLE001 -- one bad cycle must never kill the scheduler
                logger.exception("Sync scheduler cycle failed")
            self._stop_event.wait(self._interval)


def run_sync_cycle() -> None:
    """One pass: incremental-sync the connected mailbox, then classify/extract anything new.

    A standalone function (not a method) so a test -- or a future "sync now" caller -- can invoke
    exactly one cycle without spinning up a thread.
    """
    session = SessionLocal()
    try:
        connection = session.query(GmailConnection).first()
        if connection is None:
            return  # nothing connected yet -- nothing to sync
        user = ensure_default_user(session)
        try:
            run_incremental_sync(session, connection)
        except NoSyncCheckpointError:
            return  # the initial backfill (B3) hasn't run yet for this connection
        run_classify_and_extract(session, user)
    finally:
        session.close()

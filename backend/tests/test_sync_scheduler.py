"""Background SyncScheduler: polls incremental sync + classify/extract on an interval, without
requiring a manual "sync now" trigger."""

import time

import pytest

import app.infrastructure.sync_scheduler as sync_scheduler
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import GmailConnection
from app.infrastructure.sync_scheduler import SyncScheduler, run_sync_cycle


@pytest.fixture()
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY_PATH", str(tmp_path / "secret.key"))
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    Session = make_session_factory(engine)
    session = Session()

    # SyncScheduler always opens its own session via SessionLocal() -- point that at the same
    # throwaway engine as this test's session, so both see the same rows.
    monkeypatch.setattr(sync_scheduler, "SessionLocal", Session)
    yield session
    session.close()


def test_run_sync_cycle_does_nothing_when_no_gmail_connection_exists(session, monkeypatch):
    ensure_default_user(session)
    session.commit()

    called = []
    monkeypatch.setattr(
        sync_scheduler, "run_incremental_sync", lambda *a, **k: called.append("sync")
    )
    monkeypatch.setattr(
        sync_scheduler, "run_classify_and_extract", lambda *a, **k: called.append("extract")
    )

    run_sync_cycle()

    assert called == []


def test_run_sync_cycle_calls_sync_then_extract_when_connected(session, monkeypatch):
    user = ensure_default_user(session)
    session.add(GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}"))
    session.commit()

    called = []
    monkeypatch.setattr(
        sync_scheduler, "run_incremental_sync", lambda *a, **k: called.append("sync")
    )
    monkeypatch.setattr(
        sync_scheduler, "run_classify_and_extract", lambda *a, **k: called.append("extract")
    )

    run_sync_cycle()

    assert called == ["sync", "extract"]


def test_run_sync_cycle_skips_extract_if_backfill_hasnt_run_yet(session, monkeypatch):
    user = ensure_default_user(session)
    session.add(GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}"))
    session.commit()

    def _raise_no_checkpoint(*a, **k):
        raise sync_scheduler.NoSyncCheckpointError("no backfill yet")

    called = []
    monkeypatch.setattr(sync_scheduler, "run_incremental_sync", _raise_no_checkpoint)
    monkeypatch.setattr(
        sync_scheduler, "run_classify_and_extract", lambda *a, **k: called.append("extract")
    )

    run_sync_cycle()  # must not raise

    assert called == []


class TestSyncSchedulerThreadLifecycle:
    def test_runs_at_least_once_then_stops_cleanly(self, session, monkeypatch):
        call_count = {"n": 0}

        def _count(*a, **k):
            call_count["n"] += 1

        monkeypatch.setattr(sync_scheduler, "run_sync_cycle", _count)

        scheduler = SyncScheduler(interval_seconds=0.01)
        scheduler.start()
        time.sleep(0.1)
        scheduler.stop()

        assert call_count["n"] >= 1

    def test_one_bad_cycle_does_not_kill_the_scheduler(self, session, monkeypatch):
        call_count = {"n": 0}

        def _always_fails(*a, **k):
            call_count["n"] += 1
            raise RuntimeError("boom")

        monkeypatch.setattr(sync_scheduler, "run_sync_cycle", _always_fails)

        scheduler = SyncScheduler(interval_seconds=0.01)
        scheduler.start()
        time.sleep(0.1)
        scheduler.stop()

        assert call_count["n"] >= 2  # kept retrying despite every cycle raising

    def test_start_is_idempotent(self, monkeypatch):
        monkeypatch.setattr(sync_scheduler, "run_sync_cycle", lambda: None)
        scheduler = SyncScheduler(interval_seconds=1)
        scheduler.start()
        first_thread = scheduler._thread
        scheduler.start()
        assert scheduler._thread is first_thread
        scheduler.stop()

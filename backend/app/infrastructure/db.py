import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "app.db"


def _db_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", str(_DEFAULT_DB_PATH)))


def get_database_url() -> str:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None) -> Engine:
    """Build a fresh engine for the given URL (or the configured app database if omitted).

    Tests should call this directly with an explicit URL (e.g. "sqlite:///:memory:")
    rather than relying on the module-level `engine` below, so test runs never touch the
    real application database and don't depend on import order.
    """
    return create_engine(
        database_url or get_database_url(), connect_args={"check_same_thread": False}
    )


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Default engine/session for actual app runtime use (FastAPI dependency injection, Alembic).
engine = make_engine()
SessionLocal = make_session_factory(engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session. Overridden in tests via
    app.dependency_overrides so they never touch the real application database."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

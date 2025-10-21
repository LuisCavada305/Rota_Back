from __future__ import annotations

from contextlib import contextmanager
from typing import Optional, Callable, Iterator

from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import settings


engine_kwargs = {
    "pool_pre_ping": True,
    "future": True,
}

if settings.url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    )
else:
    engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout,
            "pool_recycle": settings.db_pool_recycle,
            "pool_use_lifo": True,
        }
    )

engine = create_engine(settings.url, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

_session_factory: Callable[[], Session] = SessionLocal
_session_override: Optional[Session] = None


def set_session_factory(factory: Callable[[], Session]) -> None:
    """Allow replacing the session factory (useful for tests)."""

    global _session_factory
    _session_factory = factory


def reset_session_factory() -> None:
    global _session_factory
    _session_factory = SessionLocal


def set_db_session_override(session: Session | None) -> None:
    """Force returning a specific session (used by tests)."""

    global _session_override
    _session_override = session


def clear_db_session_override() -> None:
    set_db_session_override(None)


def _new_session() -> Session:
    return _session_factory()


def get_db() -> Session:
    """Return the active session, creating one per Flask request if needed."""

    if _session_override is not None:
        return _session_override

    if "db_session" not in g:
        g.db_session = _new_session()
    return g.db_session


def close_db(_=None) -> None:
    if _session_override is not None:
        return

    db: Optional[Session] = g.pop("db_session", None)
    if db is not None:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = _new_session()
    try:
        yield session
    finally:
        session.close()

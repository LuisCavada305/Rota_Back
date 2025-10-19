# tests/conftest.py
import os

os.environ.setdefault("JWT_SECRET", "test-secret-change-me-123")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.db import (
    engine as global_engine,
    clear_db_session_override,
    reset_session_factory,
    set_db_session_override,
    set_session_factory,
)
from app.core.settings import settings
from app.models.base import Base
from app.models.lookups import LkRole, LkSex, LkColor


app.config.update({"TESTING": True})


@pytest.fixture(scope="function")
def engine():
    engine_options = {"pool_pre_ping": True}
    if settings.url.startswith("sqlite"):
        engine_options.update(
            {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        )
    eng = create_engine(settings.url, **engine_options)
    Base.metadata.create_all(bind=eng)
    Base.metadata.create_all(bind=global_engine)
    with eng.begin() as conn:
        existing_sex = set(conn.execute(select(LkSex.code)).scalars())
        for code in ["MC", "MT", "WC", "WT", "OT", "NS"]:
            if code not in existing_sex:
                conn.execute(insert(LkSex).values(code=code))
        existing_colors = set(conn.execute(select(LkColor.code)).scalars())
        for code in ["BR", "PR", "PA", "AM", "IN", "OU", "NS"]:
            if code not in existing_colors:
                conn.execute(insert(LkColor).values(code=code))
        existing_roles = set(conn.execute(select(LkRole.code)).scalars())
        for code in ["Admin", "User", "Manager"]:
            if code not in existing_roles:
                conn.execute(insert(LkRole).values(code=code))
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture(scope="function")
def db_connection(engine):
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()


@pytest.fixture(scope="function")
def db_session(db_connection):
    SessionLocal = sessionmaker(
        bind=db_connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = SessionLocal()
    nested = db_connection.begin_nested()

    def restart_savepoint(sess, trans_):
        nonlocal nested
        if trans_.nested and not trans_.connection.closed:
            nested = db_connection.begin_nested()

    event.listen(session, "after_transaction_end", restart_savepoint)

    set_session_factory(SessionLocal)
    set_db_session_override(session)

    try:
        yield session
    finally:
        event.remove(session, "after_transaction_end", restart_savepoint)
        clear_db_session_override()
        reset_session_factory()
        session.close()


@pytest.fixture(scope="function")
def client():
    with app.test_client() as client:
        yield client

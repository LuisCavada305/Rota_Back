# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_db
from app.core.settings import settings

@pytest.fixture(scope="function")
def engine():
    eng = create_engine(settings.url, pool_pre_ping=True)
    try:
        yield eng
    finally:
        eng.dispose()  # <- importantíssimo

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
    SessionLocal = sessionmaker(bind=db_connection, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()
    nested = db_connection.begin_nested()
    @db.dispatch.after_transaction_end
    def _restart_savepoint(sess, trans_):
        nonlocal nested
        if trans_.nested and not trans_.connection.closed:
            nested = db_connection.begin_nested()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function", autouse=True)
def override_get_db(db_session):
    def _get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client():
    return TestClient(app)

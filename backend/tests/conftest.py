"""Shared pytest fixtures: isolated test DB with seed data, authenticated clients."""
import os
import sys

# Ensure the parent dir is on sys.path so 'app' is importable when running pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def _configure_test_env():
    """Use an isolated in-memory DB and disable the scheduler for the test session."""
    settings.DATABASE_URL = "sqlite:///./test_tickets.db"
    settings.ENABLE_SCHEDULER = False
    settings.JWT_SECRET = "test-secret-for-pytest-only"


@pytest.fixture(scope="session")
def test_engine(_configure_test_env):
    """Build a fresh engine pointing at the test DB."""
    from app.db import session as session_mod
    engine = create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Patch the module so all imports use the test engine/session
    session_mod.engine = engine
    session_mod.SessionLocal = TestSession

    yield engine

    # Cleanup
    engine.dispose()
    if os.path.exists("./test_tickets.db"):
        try:
            os.remove("./test_tickets.db")
        except PermissionError:
            pass


@pytest.fixture(autouse=True)
def fresh_db(test_engine):
    """Reset all tables before each test and re-seed."""
    from app.db.session import Base
    from app.db.seed import seed

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    seed()
    yield


@pytest.fixture
def client(test_engine):
    """Plain (unauthenticated) test client."""
    from app.main import app
    return TestClient(app)


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_client(client):
    token = _login(client, "admin@empresa.pt", "admin123")
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def tech_client(test_engine):
    """A fresh client authenticated as a tech (separate instance to avoid header collisions)."""
    from app.main import app
    c = TestClient(app)
    token = _login(c, "tecnico@empresa.pt", "tecnico123")
    c.headers["Authorization"] = f"Bearer {token}"
    return c


@pytest.fixture
def user_client(test_engine):
    from app.main import app
    c = TestClient(app)
    token = _login(c, "utilizador@empresa.pt", "user123")
    c.headers["Authorization"] = f"Bearer {token}"
    return c

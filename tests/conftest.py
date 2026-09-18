import os, tempfile
from pathlib import Path
TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(TEST_DIR.name) / "test.db")
os.environ["MEDIA_DIR"] = str(Path(TEST_DIR.name) / "media")
os.environ.pop("OPENAI_API_KEY", None)
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import Base, engine

@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c: yield c

def auth(client, role):
    r = client.post("/auth/login", json={"email": role+"@demo.local", "password":"CityDemo-2026!"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer "+r.json()["token"]}

def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    TEST_DIR.cleanup()

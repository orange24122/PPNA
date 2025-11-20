from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.db.session import get_db
from main import app


test_engine = create_engine(
    "sqlite:///./test_router.db",
    future=True,
    connect_args={"check_same_thread": False},
)
models.Base.metadata.create_all(test_engine)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=Session,
    expire_on_commit=False,
)


def override_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db

client = TestClient(app)


def test_login():
    resp = client.post("/api/v1/auth/login", json={"username": "user", "password": "123"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_task_lifecycle(monkeypatch):
    def fake_delay(**kwargs):
        return None

    from app.tasks import detection_task

    monkeypatch.setattr(detection_task.detect_policy_task, "delay", fake_delay)

    resp = client.post(
        "/api/v1/detection/tasks",
        json={"app_name": "TestApp", "policy_text": "正文"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    models.Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, class_=Session, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def stub_model_layers(monkeypatch):
    from app.services import detection

    class DummyModelManager:
        def segment_policy_text(self, text):
            return [text[:100]] if text else []

        def classify_chunk(self, text):
            return {"score": 0.6}

        def embed_text(self, text):
            return [0.1, 0.2, 0.3]

        def build_generation_prompt(self, *args, **kwargs):
            return "prompt"

        def generate_text(self, prompt):
            return "风险描述 建议补充说明"

        def predict_risk_level(self, features):
            return "medium"

    class DummyRetriever:
        def __init__(self, db):
            self.db = db

        def search(self, vector, kb_type, top_k=3):
            return [
                {"kb_id": f"{kb_type}_001", "title": "法规", "content": "示例法规"},
            ]

    monkeypatch.setattr(detection.ModelManager, "get_instance", lambda: DummyModelManager())
    monkeypatch.setattr(detection, "RagRetriever", lambda db: DummyRetriever(db))


import json
import random
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.logging_config import setup_logging
from app.db.session import db_session
from app.models import KnowledgeBaseItem

setup_logging()

MOCK_DATA = [
    {
        "kb_id": "reg_001",
        "kb_type": "regulation",
        "content_text": "个人信息保护法 第 27 条：最小必要原则。",
    },
    {
        "kb_id": "reg_002",
        "kb_type": "regulation",
        "content_text": "网络安全法 第 41 条：收集使用规则。",
    },
    {
        "kb_id": "case_001",
        "kb_type": "case",
        "content_text": "XX 社交软件非法收集案，被罚 50 万元。",
    },
]


def load_mock_data(session: Session, data=None) -> None:
    records = data or MOCK_DATA
    for item in records:
        vector_id = f"vec_{random.randint(100000, 999999)}"
        session.merge(
            KnowledgeBaseItem(
                kb_id=item["kb_id"],
                kb_type=item["kb_type"],
                content_text=item["content_text"],
                milvus_vector_id=vector_id,
            )
        )
    session.commit()


if __name__ == "__main__":
    with db_session() as session:
        load_mock_data(session)
        print("知识库初始化完成。")


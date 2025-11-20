from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON, TypeDecorator
from sqlalchemy.orm import declarative_base, relationship


class JSONBCompat(TypeDecorator):
    """兼容 SQLite 测试环境的 JSONB 类型."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String(255), primary_key=True, index=True)
    detection_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    basic_info = Column(JSONBCompat, nullable=False)
    statistics = Column(JSONBCompat, nullable=False)
    risk_details_json = Column(JSONBCompat, nullable=False)
    operation_logs_json = Column(JSONBCompat, nullable=False)

    task = relationship("DetectionTask", back_populates="report", uselist=False)


class DetectionTask(Base):
    __tablename__ = "detection_tasks"

    task_id = Column(String(255), primary_key=True, index=True)
    submission_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    report_id = Column(String(255), ForeignKey("reports.report_id"), nullable=True)

    report = relationship("Report", back_populates="task")


class KnowledgeBaseItem(Base):
    __tablename__ = "knowledge_base"

    kb_id = Column(String(255), primary_key=True, index=True)
    kb_type = Column(String(50), nullable=False)
    milvus_vector_id = Column(String(255), nullable=False)
    content_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def update_timestamp(self) -> None:
        self.updated_at = datetime.utcnow()


import logging
import time
from typing import Dict, Optional

from celery import states
from celery import current_task

from app.config.logging_config import setup_logging
from app.db.session import db_session
from app.services.detection import DetectionService
from app.tasks.celery_app import celery_app

setup_logging()
logger = logging.getLogger(__name__)


def _update_progress(progress: int, meta: Optional[Dict] = None) -> None:
    if current_task:
        meta_payload = {"progress": progress}
        if meta:
            meta_payload.update(meta)
        current_task.update_state(state=states.STARTED, meta=meta_payload)
        logger.info("任务 %s 进度 %s%%", current_task.request.id, progress)


@celery_app.task(name="detect_policy_task")
def detect_policy_task(task_id: str, app_name: str, policy_text: str) -> str:
    """核心 Celery 任务，模拟 RAG + MOE 的检测流程。"""
    logger.info("Celery 任务开始 task_id=%s", task_id)
    step_progress = [5, 15, 55, 90, 100]
    with db_session() as session:
        service = DetectionService(session)

        # --- 预处理 ---
        cleaned_text = policy_text.strip()
        _update_progress(step_progress[0], {"stage": "preprocess"})
        time.sleep(0.2)

        # --- 智能分块 ---
        chunks = [cleaned_text[i : i + 500] for i in range(0, len(cleaned_text), 500)]
        _update_progress(step_progress[1], {"stage": "chunking", "chunk_count": len(chunks)})
        time.sleep(0.2)

        # --- MOE 专家协作 ---
        fused_text = " ".join(chunks)
        _update_progress(step_progress[2], {"stage": "rag"})
        time.sleep(0.2)

        # --- 汇总报告 ---
        report = service.build_report(task_id=task_id, app_name=app_name, policy_text=fused_text)
        _update_progress(step_progress[3], {"stage": "aggregation"})
        time.sleep(0.2)

        # --- 持久化 ---
        service.persist_report(task_id=task_id, report=report)
        _update_progress(step_progress[4], {"stage": "persisted"})

    logger.info("Celery 任务完成 task_id=%s", task_id)
    return report.report_id


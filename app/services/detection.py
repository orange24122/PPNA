import logging
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import models
from app.schemas import (
    BasicInfo,
    CaseItem,
    FragmentPosition,
    OperationLog,
    RegulationItem,
    ReportPayload,
    RiskDetail,
    TaskResultResponse,
    TaskStatusResponse,
    TaskSubmissionRequest,
    TaskSubmissionResponse,
)
from app.services.model_manager import ModelManager
from app.services.rag_retriever import RagRetriever

logger = logging.getLogger(__name__)


class MilvusClientStub:
    """简化的 Milvus 客户端，用于本地模拟检索。"""

    def search(self, text: str, kb_type: str, top_k: int = 2) -> List[Dict[str, Any]]:
        fake_hits = []
        for idx in range(top_k):
            fake_hits.append(
                {
                    "kb_id": f"{kb_type[:3]}_{random.randint(1,99)}",
                    "title": f"{kb_type.title()} 示例 {idx + 1}",
                    "content": f"{kb_type} 检索结果：与“{text[:12]}...”高度相关的内容。",
                }
            )
        return fake_hits


class DetectionService:
    def __init__(self, db: Session):
        self.db = db
        self.milvus = MilvusClientStub()
        self.model_manager = ModelManager.get_instance()
        self.rag_retriever = RagRetriever(db)

    def submit_task(self, payload: TaskSubmissionRequest) -> TaskSubmissionResponse:
        payload.validate_payload()
        task_id = str(uuid.uuid4())
        task = models.DetectionTask(
            task_id=task_id,
            status="pending",
            progress=0,
        )
        self.db.add(task)
        self.db.commit()
        logger.info("提交检测任务 task_id=%s", task_id)
        return TaskSubmissionResponse(task_id=task_id)

    def get_task_status(self, task_id: str) -> Optional[TaskStatusResponse]:
        task = self.db.get(models.DetectionTask, task_id)
        if not task:
            return None
        return TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,  # type: ignore[arg-type]
            progress=task.progress,
        )

    def get_task_result(self, task_id: str) -> Optional[TaskResultResponse]:
        task = self.db.get(models.DetectionTask, task_id)
        if not task:
            return None
        report_payload = None
        if task.report:
            report_payload = ReportPayload(
                report_id=task.report.report_id,
                basic_info=BasicInfo(**task.report.basic_info),
                statistics=task.report.statistics,
                risk_details=[
                    RiskDetail(**detail) for detail in task.report.risk_details_json
                ],
                operation_logs=[
                    OperationLog(**log) for log in task.report.operation_logs_json
                ],
            )
        return TaskResultResponse(
            task_id=task.task_id,
            status=task.status,  # type: ignore[arg-type]
            progress=task.progress,
            report=report_payload,
        )

    def persist_report(self, task_id: str, report: ReportPayload) -> None:
        task = self.db.get(models.DetectionTask, task_id)
        if not task:
            raise ValueError(f"task {task_id} 不存在")

        report_model = models.Report(
            report_id=report.report_id,
            detection_time=report.basic_info.detection_time,
            basic_info=report.basic_info.dict(),
            statistics=report.statistics.dict(),
            risk_details_json=[detail.dict() for detail in report.risk_details],
            operation_logs_json=[log.dict() for log in report.operation_logs],
        )
        self.db.add(report_model)
        task.report = report_model
        task.status = "completed"
        task.progress = 100
        self.db.commit()
        logger.info("任务 %s 已完成，报告 %s 已保存。", task_id, report.report_id)

    # ---- 以下方法为 Celery 任务内部调用的模拟逻辑 ----

    # ---- 新检测逻辑 ----

    def build_report(self, task_id: str, app_name: str, policy_text: str) -> ReportPayload:
        detection_time = datetime.utcnow()
        chunks = self.model_manager.segment_policy_text(policy_text)
        if not chunks:
            chunks = [policy_text[:500]]

        risk_details: List[RiskDetail] = []
        cursor = 0
        for idx, chunk in enumerate(chunks, start=1):
            classification = self.model_manager.classify_chunk(chunk)
            if classification["score"] < 0.25:
                continue

            start_index = policy_text.find(chunk, cursor)
            if start_index == -1:
                start_index = cursor
            end_index = start_index + len(chunk)
            cursor = end_index

            embedding = self.model_manager.embed_text(chunk)
            regulations_raw = self.rag_retriever.search(embedding, kb_type="regulation")
            cases_raw = self.rag_retriever.search(embedding, kb_type="case")

            regulations = [
                RegulationItem(kb_id=item["kb_id"], title=item["title"], excerpt=item["content"][:280])
                for item in regulations_raw
            ]
            cases = [
                CaseItem(kb_id=item["kb_id"], title=item["title"], penalty="参考案例")
                for item in cases_raw
            ]

            prompt = self.model_manager.build_generation_prompt(app_name, chunk, regulations_raw, cases_raw)
            generation = self.model_manager.generate_text(prompt)
            risk_desc, suggestion = self._split_generation(generation)

            features = [
                classification["score"],
                len(chunk) / 1000,
                len(regulations) / 5,
            ]
            level = self.model_manager.predict_risk_level(features)

            risk_details.append(
                RiskDetail(
                    risk_id=f"{task_id[:8]}-{idx}",
                    category=self._infer_category(chunk),
                    level=level,  # type: ignore[arg-type]
                    policy_fragment=chunk,
                    fragment_position=FragmentPosition(start_index=start_index, end_index=end_index),
                    violated_regulations=regulations,
                    related_cases=cases,
                    risk_description=risk_desc,
                    rectification_suggestion=suggestion,
                )
            )

        if not risk_details:
            risk_details.append(
                RiskDetail(
                    risk_id=f"{task_id[:8]}-fallback",
                    category="信息收集",
                    level="low",  # type: ignore[arg-type]
                    policy_fragment=policy_text[:200],
                    fragment_position=FragmentPosition(start_index=0, end_index=min(200, len(policy_text))),
                    violated_regulations=[],
                    related_cases=[],
                    risk_description="未检测到高风险分段，建议人工复核关键条款。",
                    rectification_suggestion="补充用户知情同意义务说明。",
                )
            )

        summary = self._build_statistics(risk_details)
        return ReportPayload(
            report_id=str(uuid.uuid4()),
            basic_info=BasicInfo(
                app_name=app_name,
                detection_time=detection_time,
                status="completed",
                reviewer="AutoMoE",
            ),
            statistics=summary,
            risk_details=risk_details,
            operation_logs=[
                OperationLog(
                    log_id=str(uuid.uuid4()),
                    operated_by="system",
                    operation_time=detection_time,
                    action="任务完成并生成报告",
                )
            ],
        )

    def _split_generation(self, text: str) -> (str, str):
        if "[MOCK RESPONSE]" in text:
            return ("根据启发式规则，建议关注数据收集合规性。", "请补充处理目的、权限申请与撤回机制。")
        parts = text.split("建议")
        desc = parts[0].strip()
        suggestion = "建议" + parts[1].strip() if len(parts) > 1 else "请根据法规要求补充整改措施。"
        return desc, suggestion

    def _infer_category(self, chunk: str) -> str:
        keywords = {
            "共享": "信息共享",
            "第三方": "信息共享",
            "权限": "信息收集",
            "定位": "信息收集",
            "存储": "信息存储",
            "删除": "信息存储",
            "权利": "用户权利",
        }
        for key, category in keywords.items():
            if key in chunk:
                return category
        return "信息收集"

    def _build_statistics(self, risks: List[RiskDetail]) -> Dict[str, Any]:
        total = len(risks)
        high = sum(1 for r in risks if r.level == "high")
        medium = sum(1 for r in risks if r.level == "medium")
        low = total - high - medium
        compliance = max(0.0, round(1 - (high * 0.25 + medium * 0.12 + low * 0.05), 2))
        return {
            "total_risk_count": total,
            "high_risk_count": high,
            "medium_risk_count": medium,
            "low_risk_count": low,
            "compliance_rate": compliance,
        }


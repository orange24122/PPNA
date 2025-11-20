from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.db.session import get_db
from app.schemas import (
    TaskResultResponse,
    TaskStatusResponse,
    TaskSubmissionRequest,
    TaskSubmissionResponse,
)
from app.services.detection import DetectionService
from app.tasks.detection_task import detect_policy_task

router = APIRouter(prefix="/detection", tags=["detection"])


def get_service(db=Depends(get_db)) -> DetectionService:
    return DetectionService(db)


@router.post("/upload")
async def upload_policy(file: UploadFile = File(...)) -> dict:
    contents = await file.read()
    text = contents.decode("utf-8", errors="ignore")
    if not text:
        raise HTTPException(status_code=400, detail="文件内容为空")
    return {"filename": file.filename, "text_preview": text[:2000]}


@router.post("/tasks", response_model=TaskSubmissionResponse)
async def create_detection_task(
    payload: TaskSubmissionRequest,
    service: DetectionService = Depends(get_service),
) -> TaskSubmissionResponse:
    if not payload.policy_text and payload.policy_url:
        payload.policy_text = f"模拟从 {payload.policy_url} 抓取的文本..."
    response = service.submit_task(payload)
    detect_policy_task.delay(
        task_id=response.task_id,
        app_name=payload.app_name,
        policy_text=payload.policy_text or "",
    )
    return response


@router.get("/tasks/{task_id}", response_model=TaskResultResponse)
async def get_detection_task(task_id: str, service: DetectionService = Depends(get_service)):
    result = service.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    if result.status == "completed":
        return result
    status_payload = service.get_task_status(task_id)
    if not status_payload:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResultResponse(
        task_id=status_payload.task_id,
        status=status_payload.status,  # type: ignore[arg-type]
        progress=status_payload.progress,
        report=None,
    )


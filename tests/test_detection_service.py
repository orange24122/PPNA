from app.services.detection import DetectionService, TaskSubmissionRequest
from app import models


def test_submit_task(db_session):
    service = DetectionService(db_session)
    payload = TaskSubmissionRequest(app_name="TestApp", policy_text="内容")
    response = service.submit_task(payload)
    assert response.task_id

    task = db_session.get(models.DetectionTask, response.task_id)
    assert task is not None
    assert task.status == "pending"


def test_build_report(db_session):
    service = DetectionService(db_session)
    report = service.build_report("task-1", "TestApp", "示例文本" * 30)
    assert report.statistics.total_risk_count > 0
    assert len(report.risk_details) == report.statistics.total_risk_count


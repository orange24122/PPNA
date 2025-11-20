from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RoleEnum(str, Enum):
    admin = "admin"
    user = "user"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: RoleEnum
    expires_in: int = Field(3600, description="Token 有效期（秒）")


class LogoutResponse(BaseModel):
    detail: str = "logged out"


class TaskSubmissionRequest(BaseModel):
    app_name: str
    policy_text: Optional[str] = None
    policy_url: Optional[str] = None

    def validate_payload(self) -> None:
        if not self.policy_text and not self.policy_url:
            raise ValueError("policy_text 和 policy_url 至少提供一个。")


class TaskSubmissionResponse(BaseModel):
    task_id: str
    status: str = "pending"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = Field(0, ge=0, le=100)


class FragmentPosition(BaseModel):
    start_index: int
    end_index: int


class RegulationItem(BaseModel):
    kb_id: str
    title: str
    excerpt: str


class CaseItem(BaseModel):
    kb_id: str
    title: str
    penalty: str


class RiskDetail(BaseModel):
    risk_id: str
    category: str
    level: Literal["high", "medium", "low"]
    policy_fragment: str
    fragment_position: FragmentPosition
    violated_regulations: List[RegulationItem]
    related_cases: List[CaseItem]
    risk_description: str
    rectification_suggestion: str
    handling_status: Literal["untreated", "processing", "resolved"] = "untreated"


class BasicInfo(BaseModel):
    app_name: str
    detection_time: datetime
    status: Literal["completed", "failed"]
    reviewer: str


class Statistics(BaseModel):
    total_risk_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    compliance_rate: float


class OperationLog(BaseModel):
    log_id: str
    operated_by: str
    operation_time: datetime
    action: str


class ReportPayload(BaseModel):
    report_id: str
    basic_info: BasicInfo
    statistics: Statistics
    risk_details: List[RiskDetail]
    operation_logs: List[OperationLog]


class TaskResultResponse(BaseModel):
    task_id: str
    status: Literal["completed", "failed"]
    progress: int
    report: Optional[ReportPayload]


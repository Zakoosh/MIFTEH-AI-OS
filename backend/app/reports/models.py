from pydantic import BaseModel, Field
from typing import Optional


class ReportFinding(BaseModel):
    summary: str = ""
    findings: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    priority: str = "medium"
    score: float = Field(default=0.0, ge=0.0, le=100.0)


class StructuredReport(BaseModel):
    report_id: str = ""
    mission_id: str = ""
    project_id: str = ""
    agent_name: str = ""
    division: str = ""
    finding: ReportFinding = Field(default_factory=ReportFinding)
    mode: str = "unknown"
    success: bool = False
    execution_time: float = 0.0
    raw_content: str = ""
    error: Optional[str] = None
    created_at: str = ""


class ReportListEntry(BaseModel):
    report_id: str
    mission_id: str = ""
    project_id: str = ""
    agent_name: str = ""
    priority: str = "medium"
    score: float = 0.0
    success: bool = False
    mode: str = "unknown"
    created_at: str = ""


class ReportStats(BaseModel):
    total_reports: int = 0
    success_count: int = 0
    failed_count: int = 0
    average_score: float = 0.0
    by_project: dict[str, int] = Field(default_factory=dict)
    by_agent: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_mode: dict[str, int] = Field(default_factory=dict)


class ReportHistoryResponse(BaseModel):
    total_reports: int = 0
    reports: list[ReportListEntry] = Field(default_factory=list)

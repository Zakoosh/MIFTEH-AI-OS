from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MissionRequest(BaseModel):
    project_id: str
    mission_id: str
    agent_limit: int = Field(default=0, description="Max agents to run. 0 means all.")


class AgentFinding(BaseModel):
    summary: str = ""
    findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    priority: str = "medium"


class AgentResult(BaseModel):
    agent_name: str
    division: str = ""
    source_path: str = ""
    status: str = "pending"
    mode: str = "unknown"
    success: bool = False
    finding: AgentFinding = Field(default_factory=AgentFinding)
    raw_content: str = ""
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class MissionResult(BaseModel):
    mission_id: str
    project_id: str
    mission_title: str = ""
    status: str = "pending"
    agents_total: int = 0
    agents_completed: int = 0
    agents_failed: int = 0
    agent_results: list[AgentResult] = Field(default_factory=list)
    started_at: str = ""
    completed_at: Optional[str] = None


class MissionHistoryEntry(BaseModel):
    execution_id: str
    mission_id: str
    project_id: str
    mission_title: str = ""
    status: str = "pending"
    agents_total: int = 0
    agents_completed: int = 0
    agents_failed: int = 0
    started_at: str = ""
    completed_at: Optional[str] = None


class MissionHistorySummary(BaseModel):
    total_executions: int = 0
    executions: list[MissionHistoryEntry] = Field(default_factory=list)

from pydantic import BaseModel, Field
from typing import Optional


TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

SCHEDULE_TYPE_INTERVAL = "interval"


class AutomationTask(BaseModel):
    task_id: str
    mission_id: str
    project_id: str
    schedule_type: str = SCHEDULE_TYPE_INTERVAL
    interval_minutes: int
    enabled: bool = True
    status: str = TASK_STATUS_PENDING
    retry_count: int = 0
    max_retries: int = 2
    cooldown_minutes: int = 5
    agent_limit: int = 0
    created_at: str = ""
    updated_at: str = ""
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_completed_at: Optional[str] = None
    last_error: Optional[str] = None
    last_execution_id: Optional[str] = None


class AutomationHistoryEntry(BaseModel):
    history_id: str
    task_id: str
    mission_id: str
    project_id: str
    status: str
    attempt: int = 1
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0
    execution_id: Optional[str] = None
    error: Optional[str] = None
    mission_result: dict = Field(default_factory=dict)
    git_status: dict = Field(default_factory=dict)
    git_diff: dict = Field(default_factory=dict)
    reports_summary: dict = Field(default_factory=dict)


class AutomationPolicy(BaseModel):
    max_concurrent_tasks: int = 2
    default_max_retries: int = 2
    default_cooldown_minutes: int = 5


class AutomationTaskRunResult(BaseModel):
    success: bool = True
    task: Optional[AutomationTask] = None
    history: Optional[AutomationHistoryEntry] = None
    error: Optional[str] = None


class AutomationTaskList(BaseModel):
    tasks: list[AutomationTask] = Field(default_factory=list)
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0


class AutomationHistoryList(BaseModel):
    total: int = 0
    entries: list[AutomationHistoryEntry] = Field(default_factory=list)

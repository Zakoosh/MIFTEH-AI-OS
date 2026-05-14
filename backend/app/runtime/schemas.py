from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from .models import OperationType, RuntimeMode


class RuntimeStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: str
    mode: str
    active_operations: int
    queued_operations: int
    cycles_today: int
    limits: list[dict]
    safety_active: bool = True
    bounded_autonomy: bool = True


class OperationsListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    operations: list[dict]
    total: int
    active: int
    completed: int
    failed: int


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    period: str
    total_operations: int
    success_rate: float
    avg_duration_seconds: float
    total_cost_usd: float
    top_projects: list[str]
    operations_by_type: dict[str, int]
    operations_by_status: dict[str, int]


class RunRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    project: str
    mode: RuntimeMode = RuntimeMode.manual
    operation_type: OperationType = OperationType.health_check
    trust_score: float = 0.5
    metadata: dict = {}


class RunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    success: bool
    operation_id: str | None = None
    cycle_id: str | None = None
    message: str
    blocked_by: str | None = None


class RuntimeHealthResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: str
    layers_healthy: dict[str, bool]
    limits_status: list[dict]
    last_cycle: dict | None = None
    uptime_hours: float
    checked_at: str

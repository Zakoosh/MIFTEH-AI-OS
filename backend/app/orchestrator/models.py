from pydantic import BaseModel, Field
from typing import Optional


ORCHESTRATION_MODE_ADVISORY = "advisory"
ORCHESTRATION_STATUS_PLANNED = "planned"
ORCHESTRATION_STATUS_BLOCKED = "blocked"

IMPROVEMENT_AREAS = [
    "SEO",
    "UI/UX",
    "performance",
    "branding",
    "security",
    "monetization",
    "analytics",
    "conversion",
    "automation",
    "scalability",
]


class OrchestrationConstraint(BaseModel):
    name: str
    allowed: bool = True
    severity: str = "info"
    message: str = ""


class OrchestratorRecommendation(BaseModel):
    project_id: str
    project: str = ""
    mission_id: str
    title: str = ""
    priority: str = "medium"
    optimization_score: int = 0
    decision_score: int = 0
    urgency_score: int = 0
    impact_score: int = 0
    automation_readiness: int = 0
    recommended_agents: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    constraints: list[OrchestrationConstraint] = Field(default_factory=list)
    scheduler_action: str = "manual_review"
    execution_mode: str = ORCHESTRATION_MODE_ADVISORY
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)


class OrchestrationCycle(BaseModel):
    cycle_id: str
    status: str = ORCHESTRATION_STATUS_PLANNED
    started_at: str = ""
    completed_at: str = ""
    dry_run: bool = True
    projects_evaluated: int = 0
    recommendations_count: int = 0
    blocked_count: int = 0
    selected_recommendations: list[OrchestratorRecommendation] = Field(default_factory=list)
    constraints: list[OrchestrationConstraint] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class OrchestratorStatus(BaseModel):
    status: str = "ready"
    mode: str = ORCHESTRATION_MODE_ADVISORY
    safe_operations_only: bool = True
    projects_monitored: int = 0
    latest_cycle_id: Optional[str] = None
    latest_cycle_at: Optional[str] = None
    recommendations_count: int = 0
    blocked_count: int = 0
    improvement_areas: list[str] = Field(default_factory=lambda: IMPROVEMENT_AREAS.copy())
    safeguards: list[str] = Field(default_factory=list)


class OrchestratorTelemetry(BaseModel):
    cycles_total: int = 0
    recommendations_total: int = 0
    blocked_total: int = 0
    average_optimization_score: int = 0
    last_cycle_id: Optional[str] = None
    last_cycle_at: Optional[str] = None
    by_project: dict[str, int] = Field(default_factory=dict)
    by_area: dict[str, int] = Field(default_factory=dict)


class OrchestrationCycleList(BaseModel):
    cycles: list[OrchestrationCycle] = Field(default_factory=list)


class OrchestratorRecommendationList(BaseModel):
    recommendations: list[OrchestratorRecommendation] = Field(default_factory=list)

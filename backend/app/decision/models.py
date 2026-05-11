from pydantic import BaseModel, Field
from typing import Optional


CONTINUOUS_IMPROVEMENT_AREAS = [
    "UI/UX",
    "SEO",
    "performance",
    "security",
    "analytics",
    "monetization",
    "automation",
    "scalability",
]


class DecisionConstraint(BaseModel):
    name: str
    allowed: bool = True
    severity: str = "info"
    message: str = ""


class MissionDecision(BaseModel):
    project_id: str
    project: str = ""
    mission_id: str
    title: str = ""
    priority: str = "medium"
    urgency_score: int = 0
    impact_score: int = 0
    effort_score: int = 0
    automation_readiness: int = 0
    decision_score: int = 0
    recommended_agents: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    constraints: list[DecisionConstraint] = Field(default_factory=list)
    blocked: bool = False


class ExecutionPlan(BaseModel):
    plan_id: str
    project_id: str
    mission_id: str
    priority: str = "medium"
    recommended_agents: list[str] = Field(default_factory=list)
    estimated_effort: str = "medium"
    estimated_impact: int = 0
    automation_candidate: bool = False
    cooldown_minutes: int = 60
    steps: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    constraints: list[DecisionConstraint] = Field(default_factory=list)


class ProjectDecision(BaseModel):
    project_id: str
    project: str = ""
    recommended_mission: str = ""
    priority: str = "medium"
    estimated_impact: int = 0
    automation_readiness: int = 0
    continuous_improvement_areas: list[str] = Field(default_factory=list)
    decisions: list[MissionDecision] = Field(default_factory=list)
    execution_plan: Optional[ExecutionPlan] = None
    warnings: list[str] = Field(default_factory=list)


class DecisionOverview(BaseModel):
    projects_count: int = 0
    recommended_project: str = ""
    recommended_mission: str = ""
    priority: str = "medium"
    estimated_impact: int = 0
    automation_readiness: int = 0
    decisions: list[ProjectDecision] = Field(default_factory=list)


class DecisionRecommendationList(BaseModel):
    recommendations: list[MissionDecision] = Field(default_factory=list)


class DecisionPriorityList(BaseModel):
    critical: list[MissionDecision] = Field(default_factory=list)
    high: list[MissionDecision] = Field(default_factory=list)
    medium: list[MissionDecision] = Field(default_factory=list)
    low: list[MissionDecision] = Field(default_factory=list)


class ExecutionPlanList(BaseModel):
    plans: list[ExecutionPlan] = Field(default_factory=list)

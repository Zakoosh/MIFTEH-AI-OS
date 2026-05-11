from pydantic import BaseModel, Field
from typing import Optional


class WorkspaceMetadata(BaseModel):
    project_id: str
    name: str = ""
    project_type: str = ""
    path: str = ""
    path_exists: bool = False
    files_count: int = 0
    extensions: dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None


class ProjectSignals(BaseModel):
    mission_runs: int = 0
    mission_successes: int = 0
    mission_failures: int = 0
    mission_success_rate: int = 0
    report_count: int = 0
    report_successes: int = 0
    report_failures: int = 0
    report_success_rate: int = 0
    automation_runs: int = 0
    automation_failures: int = 0
    available_missions: int = 0
    days_since_last_activity: Optional[int] = None
    git_clean: Optional[bool] = None
    git_available: bool = False


class ScoreBreakdown(BaseModel):
    overall_health: int = 0
    risk_score: int = 0
    automation_readiness: int = 0
    reliability_score: int = 0
    activity_score: int = 0


class MissionRecommendation(BaseModel):
    project_id: str
    mission_id: str
    title: str = ""
    priority: str = "medium"
    score: int = 0
    reasons: list[str] = Field(default_factory=list)


class TrendSummary(BaseModel):
    project_id: str
    direction: str = "stable"
    failure_trend: str = "stable"
    mission_success_rate: int = 0
    report_success_rate: int = 0
    neglected: bool = False
    signals: list[str] = Field(default_factory=list)


class ProjectIntelligence(BaseModel):
    project_id: str
    name: str = ""
    project_type: str = ""
    health: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    signals: ProjectSignals = Field(default_factory=ProjectSignals)
    priorities: list[str] = Field(default_factory=list)
    recommendations: list[MissionRecommendation] = Field(default_factory=list)
    trend: TrendSummary = Field(default_factory=TrendSummary)
    workspace: WorkspaceMetadata = Field(default_factory=lambda: WorkspaceMetadata(project_id=""))
    warnings: list[str] = Field(default_factory=list)


class IntelligenceOverview(BaseModel):
    overall_health: int = 0
    highest_risk_project: str = ""
    recommended_next_mission: str = ""
    automation_readiness: int = 0
    projects_count: int = 0
    projects: list[ProjectIntelligence] = Field(default_factory=list)


class IntelligenceCollection(BaseModel):
    projects: list[ProjectIntelligence] = Field(default_factory=list)


class RecommendationCollection(BaseModel):
    recommendations: list[MissionRecommendation] = Field(default_factory=list)


class TrendCollection(BaseModel):
    trends: list[TrendSummary] = Field(default_factory=list)

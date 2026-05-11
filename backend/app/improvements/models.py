from pydantic import BaseModel, Field


class ImplementationPlan(BaseModel):
    proposal: str
    affected_modules: list[str] = Field(default_factory=list)
    estimated_effort: str = "medium"
    estimated_impact: int = 0
    steps: list[str] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    safe_apply: bool = True


class ImprovementProposal(BaseModel):
    project: str
    improvement_type: str
    priority: str = "medium"
    proposal: str
    expected_impact: int = 0
    estimated_effort: str = "medium"
    affected_modules: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    implementation_plan: ImplementationPlan


class ImprovementCollection(BaseModel):
    proposals: list[ImprovementProposal] = Field(default_factory=list)


class RoadmapProposal(BaseModel):
    project: str
    priority: str
    proposal: str
    estimated_impact: int
    estimated_effort: str
    sequence: int


class ImprovementRoadmap(BaseModel):
    roadmap: list[RoadmapProposal] = Field(default_factory=list)

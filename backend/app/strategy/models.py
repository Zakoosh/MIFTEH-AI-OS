from pydantic import BaseModel, Field


STRATEGIC_DOMAINS = [
    "growth",
    "monetization",
    "SEO",
    "branding",
    "automation",
    "scaling",
    "analytics",
    "conversion",
]


class StrategicOpportunity(BaseModel):
    project_id: str
    opportunity: str
    domain: str = "growth"
    priority: str = "medium"
    confidence: float = 0
    evidence: list[str] = Field(default_factory=list)


class RoadmapItem(BaseModel):
    project_id: str
    horizon: str
    title: str
    focus: str
    priority: str = "medium"
    expected_outcome: str = ""
    source: str = "strategy"


class GrowthStrategy(BaseModel):
    project_id: str
    focus: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    monetization_paths: list[str] = Field(default_factory=list)
    seo_strategy: list[str] = Field(default_factory=list)
    branding_strategy: list[str] = Field(default_factory=list)


class BusinessAlignment(BaseModel):
    project_id: str
    business_goal: str = ""
    alignment_score: int = 0
    alignment_notes: list[str] = Field(default_factory=list)


class ProjectStrategy(BaseModel):
    project_id: str
    project: str = ""
    project_type: str = ""
    strategy_focus: list[str] = Field(default_factory=list)
    recommended_roadmap: list[str] = Field(default_factory=list)
    roadmap_30_day: list[RoadmapItem] = Field(default_factory=list)
    roadmap_90_day: list[RoadmapItem] = Field(default_factory=list)
    growth_strategy: GrowthStrategy
    business_alignment: BusinessAlignment
    opportunities: list[StrategicOpportunity] = Field(default_factory=list)
    portfolio_role: str = "optimize"
    risks: list[str] = Field(default_factory=list)


class PortfolioStrategy(BaseModel):
    projects_count: int = 0
    strategic_priorities: list[str] = Field(default_factory=list)
    cross_project_opportunities: list[StrategicOpportunity] = Field(default_factory=list)
    portfolio_risks: list[str] = Field(default_factory=list)
    coordination_plan: list[str] = Field(default_factory=list)


class StrategyOverview(BaseModel):
    portfolio_focus: list[str] = Field(default_factory=list)
    highest_priority_project: str = ""
    recommended_next_strategy: str = ""
    opportunities_count: int = 0
    projects_count: int = 0
    portfolio: PortfolioStrategy
    projects: list[ProjectStrategy] = Field(default_factory=list)


class ProjectStrategyCollection(BaseModel):
    projects: list[ProjectStrategy] = Field(default_factory=list)


class RoadmapCollection(BaseModel):
    roadmap_30_day: list[RoadmapItem] = Field(default_factory=list)
    roadmap_90_day: list[RoadmapItem] = Field(default_factory=list)


class OpportunityCollection(BaseModel):
    opportunities: list[StrategicOpportunity] = Field(default_factory=list)

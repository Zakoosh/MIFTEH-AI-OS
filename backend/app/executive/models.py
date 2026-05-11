from pydantic import BaseModel, Field


EXECUTIVE_DOMAINS = [
    "growth",
    "conversion",
    "SEO",
    "branding",
    "automation",
    "analytics",
    "security",
    "scalability",
]


class ResourceAllocation(BaseModel):
    project_id: str
    project: str = ""
    allocation_percent: int = 0
    rationale: list[str] = Field(default_factory=list)


class CompanyPriority(BaseModel):
    priority: str
    domain: str = "growth"
    urgency: int = 0
    impact: int = 0
    projects: list[str] = Field(default_factory=list)


class BusinessMetric(BaseModel):
    name: str
    value: float | int | str
    trend: str = "stable"
    interpretation: str = ""


class ExecutiveRecommendation(BaseModel):
    executive_recommendation: str
    priority: str = "medium"
    expected_impact: int = 0
    projects: list[str] = Field(default_factory=list)
    supporting_signals: list[str] = Field(default_factory=list)


class OptimizationBalance(BaseModel):
    growth_focus: int = 0
    stability_focus: int = 0
    automation_focus: int = 0
    risk_focus: int = 0
    balance_notes: list[str] = Field(default_factory=list)


class ExecutiveMemorySignal(BaseModel):
    signal: str
    project_id: str = ""
    confidence: float = 0
    recommendation: str = ""


class ExecutiveOverview(BaseModel):
    company_focus: str = "growth"
    highest_priority_project: str = ""
    resource_distribution: dict[str, int] = Field(default_factory=dict)
    recommendations: list[ExecutiveRecommendation] = Field(default_factory=list)
    priorities: list[CompanyPriority] = Field(default_factory=list)
    metrics: list[BusinessMetric] = Field(default_factory=list)
    optimization_balance: OptimizationBalance = Field(default_factory=OptimizationBalance)


class ExecutivePriorityList(BaseModel):
    priorities: list[CompanyPriority] = Field(default_factory=list)


class ResourceDistribution(BaseModel):
    resource_distribution: dict[str, int] = Field(default_factory=dict)
    allocations: list[ResourceAllocation] = Field(default_factory=list)


class ExecutiveRecommendationList(BaseModel):
    recommendations: list[ExecutiveRecommendation] = Field(default_factory=list)


class BusinessMetricList(BaseModel):
    metrics: list[BusinessMetric] = Field(default_factory=list)
    memory_signals: list[ExecutiveMemorySignal] = Field(default_factory=list)

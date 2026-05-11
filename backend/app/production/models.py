from pydantic import BaseModel, Field


MODE_APPLY_READY = "apply_ready"
MODE_PROPOSAL_ONLY = "proposal_only"


class ProductionSafety(BaseModel):
    project_id: str
    mode: str
    implementation_allowed: bool = False
    destructive_operations_allowed: bool = False
    deployment_allowed: bool = False
    notes: list[str] = Field(default_factory=list)


class YallaPlaysGameIdea(BaseModel):
    game_idea: str
    genre: str
    category: str
    seo_title: str
    mobile_score: int
    implementation_tasks: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class YallaPlaysProductionPlan(BaseModel):
    project_id: str = "yallaplays"
    safety: ProductionSafety
    games: list[YallaPlaysGameIdea] = Field(default_factory=list)
    seo: list[dict] = Field(default_factory=list)
    categories: list[dict] = Field(default_factory=list)
    mobile_ux: list[dict] = Field(default_factory=list)
    content_pipeline: list[str] = Field(default_factory=list)


class FioneraInsight(BaseModel):
    symbol: str
    trend: str
    recommended_watchlist: bool = False
    insight: str
    confidence: float = 0
    actions: list[str] = Field(default_factory=list)


class FioneraProductionPlan(BaseModel):
    project_id: str = "fionera"
    safety: ProductionSafety
    market_signals: list[dict] = Field(default_factory=list)
    insights: list[FioneraInsight] = Field(default_factory=list)
    watchlists: list[dict] = Field(default_factory=list)
    ux_recommendations: list[dict] = Field(default_factory=list)
    analytics: list[dict] = Field(default_factory=list)


class MiftehRecommendation(BaseModel):
    landing_recommendation: str
    domain: str = "conversion"
    expected_impact: int = 0
    preview_only: bool = True
    rationale: list[str] = Field(default_factory=list)


class MiftehProductionPlan(BaseModel):
    project_id: str = "mifteh-main-site"
    safety: ProductionSafety
    landing: list[MiftehRecommendation] = Field(default_factory=list)
    seo_clusters: list[dict] = Field(default_factory=list)
    branding: list[dict] = Field(default_factory=list)
    lead_generation: list[dict] = Field(default_factory=list)


class ProductionOverview(BaseModel):
    mode: str = "safe_production_preview"
    projects: list[str] = Field(default_factory=list)
    implementation_allowed: dict[str, bool] = Field(default_factory=dict)
    proposal_only: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class ProductionResponse(BaseModel):
    success: bool = True
    data: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

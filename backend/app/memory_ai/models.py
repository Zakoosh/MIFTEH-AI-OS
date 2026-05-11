from pydantic import BaseModel, Field
from typing import Optional


MEMORY_AREAS = [
    "SEO",
    "UI/UX",
    "performance",
    "branding",
    "analytics",
    "conversion",
    "automation",
    "scalability",
]


class MemoryPattern(BaseModel):
    pattern: str
    project_id: str = ""
    mission_id: str = ""
    pattern_type: str = "optimization"
    confidence: float = 0
    recommended_frequency: str = "weekly"
    evidence: list[str] = Field(default_factory=list)


class SuccessMemory(BaseModel):
    project_id: str
    mission_id: str
    successes: int = 0
    success_rate: float = 0
    confidence: float = 0
    effective_sequence: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class FailureMemory(BaseModel):
    project_id: str
    mission_id: str
    failures: int = 0
    failure_rate: float = 0
    cooldown_recommended: bool = False
    retry_after_hours: int = 0
    evidence: list[str] = Field(default_factory=list)


class AdaptiveHeuristic(BaseModel):
    name: str
    description: str
    weight: float = 1
    applies_to: list[str] = Field(default_factory=list)


class MemoryRecommendation(BaseModel):
    project_id: str
    mission_id: str
    recommendation: str
    priority: str = "medium"
    confidence: float = 0
    cooldown_recommended: bool = False
    retry_after_hours: int = 0
    reasons: list[str] = Field(default_factory=list)


class AdaptiveMemorySnapshot(BaseModel):
    generated_at: str = ""
    projects_count: int = 0
    patterns: list[MemoryPattern] = Field(default_factory=list)
    successes: list[SuccessMemory] = Field(default_factory=list)
    failures: list[FailureMemory] = Field(default_factory=list)
    recommendations: list[MemoryRecommendation] = Field(default_factory=list)
    heuristics: list[AdaptiveHeuristic] = Field(default_factory=list)


class MemoryCollection(BaseModel):
    patterns: list[MemoryPattern] = Field(default_factory=list)


class SuccessCollection(BaseModel):
    successes: list[SuccessMemory] = Field(default_factory=list)


class FailureCollection(BaseModel):
    failures: list[FailureMemory] = Field(default_factory=list)


class RecommendationCollection(BaseModel):
    recommendations: list[MemoryRecommendation] = Field(default_factory=list)


class HeuristicCollection(BaseModel):
    heuristics: list[AdaptiveHeuristic] = Field(default_factory=list)

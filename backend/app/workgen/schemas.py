"""
schemas.py — Pydantic request/response schemas for the Work Generation API.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class GenerateWorkRequest(BaseModel):
    """Body for POST /workgen/generate."""

    project: str = Field("all", description="'yallaplays' | 'fionera' | 'all'")
    task_types: list[str] = Field(default_factory=list, description="Filter by task types (empty = all)")
    max_items: int = Field(20, description="Maximum items to generate per project")
    include_campaigns: bool = Field(True, description="Include SEO/marketing campaigns")
    include_roadmap: bool = Field(True, description="Include roadmap items")
    quarter: str = Field("Q3-2026", description="Target quarter for roadmap items")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class WorkItemResponse(BaseModel):
    item_id: str
    project: str
    task_type: str
    title: str
    description: str
    priority: str
    estimated_impact: float
    estimated_effort: str
    estimated_days: int
    recommended_agents: list[str]
    collaboration_mission: str
    apply_proposal_type: str
    tags: list[str]
    status: str
    source: str
    quarter: str
    roi_estimate: str
    dependencies: list[str]
    created_at: str
    metadata: dict[str, Any]


class CampaignResponse(BaseModel):
    campaign_id: str
    project: str
    campaign_type: str
    title: str
    description: str
    target_keywords: list[str]
    target_pages: list[str]
    estimated_impact: float
    estimated_effort: str
    timeline_weeks: int
    recommended_agents: list[str]
    work_item_ids: list[str]
    monthly_search_volume: int
    difficulty_score: float
    priority: str
    status: str
    created_at: str


class RoadmapItemResponse(BaseModel):
    roadmap_id: str
    project: str
    quarter: str
    title: str
    description: str
    theme: str
    work_item_ids: list[str]
    total_estimated_days: int
    expected_outcomes: list[str]
    success_metrics: list[str]
    priority: str
    status: str
    created_at: str


class PriorityScoreResponse(BaseModel):
    item_id: str
    title: str
    project: str
    task_type: str
    composite_score: float
    impact_score: float
    feasibility_score: float
    urgency_score: float
    alignment_score: float
    priority: str
    rank: int
    computed_at: str


class WorkItemListResponse(BaseModel):
    project: str
    total: int
    items: list[WorkItemResponse]
    summary: dict[str, Any]


class CampaignListResponse(BaseModel):
    total: int
    campaigns: list[CampaignResponse]


class RoadmapListResponse(BaseModel):
    total: int
    by_quarter: dict[str, list[RoadmapItemResponse]]
    roadmap_items: list[RoadmapItemResponse]


class PriorityListResponse(BaseModel):
    total: int
    top_items: list[PriorityScoreResponse]
    by_project: dict[str, list[PriorityScoreResponse]]
    by_type: dict[str, list[PriorityScoreResponse]]

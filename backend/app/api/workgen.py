"""
api/workgen.py — FastAPI router for the Real Autonomous Work Generation Layer.

Protected dashboard route: yallaplays.com/admin/os

Endpoints:
  GET  /workgen/yallaplays  — YallaPlays work items
  GET  /workgen/fionera     — Fionera work items
  GET  /workgen/campaigns   — SEO / marketing campaigns
  GET  /workgen/roadmap     — Strategic roadmap items
  GET  /workgen/priorities  — Priority-ranked work items

Additional endpoints:
  POST /workgen/generate    — Full generation run (all projects)
  GET  /workgen/status      — Layer status
  GET  /workgen/batch/{project} — Pre-built work batch
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Body

from app.workgen.work_generator import get_generator
from app.workgen.schemas import (
    GenerateWorkRequest,
    WorkItemListResponse,
    WorkItemResponse,
    CampaignListResponse,
    CampaignResponse,
    RoadmapListResponse,
    RoadmapItemResponse,
    PriorityListResponse,
    PriorityScoreResponse,
)

router = APIRouter(prefix="/workgen", tags=["Work Generation Layer"])

_gen = get_generator()


# ---------------------------------------------------------------------------
# GET /workgen/yallaplays
# ---------------------------------------------------------------------------

@router.get(
    "/yallaplays",
    response_model=WorkItemListResponse,
    summary="YallaPlays work items",
    description=(
        "Returns autonomously generated structured work items for YallaPlays. "
        "Covers SEO campaigns, features, UX, implementation, and optimisation tasks."
    ),
)
def get_yallaplays_items(
    task_types: list[str] = Query(default=[], description="Filter by task type (empty = all)"),
    max_items: int = Query(default=20, description="Maximum items to return"),
) -> WorkItemListResponse:
    try:
        items = _gen.generate_yallaplays(
            task_types=task_types or None,
            max_items=max_items,
        )
        responses = [WorkItemResponse(**i.to_dict()) for i in items]
        summary = _gen.summary_stats(items)
        return WorkItemListResponse(project="yallaplays", total=len(responses),
                                    items=responses, summary=summary)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /workgen/fionera
# ---------------------------------------------------------------------------

@router.get(
    "/fionera",
    response_model=WorkItemListResponse,
    summary="Fionera work items",
    description=(
        "Returns autonomously generated structured work items for Fionera. "
        "Covers features, dashboard, widgets, watchlist, analytics, and UX tasks."
    ),
)
def get_fionera_items(
    task_types: list[str] = Query(default=[], description="Filter by task type (empty = all)"),
    max_items: int = Query(default=20, description="Maximum items to return"),
) -> WorkItemListResponse:
    try:
        items = _gen.generate_fionera(
            task_types=task_types or None,
            max_items=max_items,
        )
        responses = [WorkItemResponse(**i.to_dict()) for i in items]
        summary = _gen.summary_stats(items)
        return WorkItemListResponse(project="fionera", total=len(responses),
                                    items=responses, summary=summary)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /workgen/campaigns
# ---------------------------------------------------------------------------

@router.get(
    "/campaigns",
    response_model=CampaignListResponse,
    summary="SEO and marketing campaigns",
    description=(
        "Returns structured SEO and marketing campaigns for YallaPlays and Fionera. "
        "Includes target keywords, impact estimates, and recommended agents."
    ),
)
def get_campaigns(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> CampaignListResponse:
    try:
        campaigns = _gen.get_campaigns(project)
        responses = [CampaignResponse(**c.to_dict()) for c in campaigns]
        return CampaignListResponse(total=len(responses), campaigns=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /workgen/roadmap
# ---------------------------------------------------------------------------

@router.get(
    "/roadmap",
    response_model=RoadmapListResponse,
    summary="Strategic roadmap items",
    description=(
        "Returns strategic roadmap items grouped by quarter. "
        "Each item spans multiple work items and carries expected outcomes and success metrics."
    ),
)
def get_roadmap(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
    quarter: str = Query(default="", description="Filter by quarter, e.g. 'Q3-2026'"),
) -> RoadmapListResponse:
    try:
        items = _gen.get_roadmap(project)
        if quarter:
            items = [r for r in items if r.quarter == quarter]
        responses = [RoadmapItemResponse(**r.to_dict()) for r in items]

        by_quarter: dict[str, list[RoadmapItemResponse]] = {}
        for r in responses:
            by_quarter.setdefault(r.quarter, []).append(r)

        return RoadmapListResponse(
            total=len(responses),
            by_quarter=by_quarter,
            roadmap_items=responses,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /workgen/priorities
# ---------------------------------------------------------------------------

@router.get(
    "/priorities",
    response_model=PriorityListResponse,
    summary="Priority-ranked work items",
    description=(
        "Returns all work items scored and ranked by composite priority: "
        "impact (50%), feasibility (20%), urgency (20%), strategic alignment (10%)."
    ),
)
def get_priorities(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
    top_n: int = Query(default=10, description="Number of top items to highlight"),
) -> PriorityListResponse:
    try:
        scores = _gen.get_priorities(project)
        responses = [PriorityScoreResponse(**s.to_dict()) for s in scores]

        by_project: dict[str, list[PriorityScoreResponse]] = {}
        by_type: dict[str, list[PriorityScoreResponse]] = {}
        for r in responses:
            by_project.setdefault(r.project, []).append(r)
            by_type.setdefault(r.task_type, []).append(r)

        return PriorityListResponse(
            total=len(responses),
            top_items=responses[:top_n],
            by_project=by_project,
            by_type=by_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /workgen/generate
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    summary="Full work generation run",
    description="Generates work items, campaigns, and roadmap for the specified project(s).",
)
def generate(body: GenerateWorkRequest = Body(...)) -> dict[str, Any]:
    try:
        result: dict[str, Any] = {}
        projects = (
            ["yallaplays", "fionera"]
            if body.project == "all"
            else [body.project]
        )

        for proj in projects:
            items = (
                _gen.generate_yallaplays(
                    task_types=body.task_types or None,
                    max_items=body.max_items,
                )
                if proj == "yallaplays"
                else _gen.generate_fionera(
                    task_types=body.task_types or None,
                    max_items=body.max_items,
                )
            )
            entry: dict[str, Any] = {
                "work_items": [i.to_dict() for i in items],
                "summary":    _gen.summary_stats(items),
            }
            if body.include_campaigns:
                entry["campaigns"] = [c.to_dict() for c in _gen.get_campaigns(proj)]
            if body.include_roadmap:
                roadmap = [r for r in _gen.get_roadmap(proj)
                           if not body.quarter or r.quarter == body.quarter]
                entry["roadmap"] = [r.to_dict() for r in roadmap]
            result[proj] = entry

        return {"projects": list(result.keys()), "results": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /workgen/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Work generation layer status",
)
def workgen_status() -> dict[str, Any]:
    try:
        yp_items = _gen.generate_yallaplays()
        fi_items = _gen.generate_fionera()
        campaigns = _gen.get_campaigns()
        roadmap   = _gen.get_roadmap()
        priorities = _gen.get_priorities()

        return {
            "status": "operational",
            "layer": "Real Autonomous Work Generation Layer",
            "projects_supported": ["yallaplays", "fionera"],
            "catalog_sizes": {
                "yallaplays_items": len(yp_items),
                "fionera_items":    len(fi_items),
                "campaigns":        len(campaigns),
                "roadmap_items":    len(roadmap),
            },
            "top_priority": priorities[0].to_dict() if priorities else None,
            "task_types_available": list({i.task_type for i in yp_items + fi_items}),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /workgen/batch/{project}
# ---------------------------------------------------------------------------

@router.get(
    "/batch/{project}",
    summary="Pre-built work batch for a project",
    description="Returns a cohesive batch summarising all work items, campaigns, and roadmap for the project.",
)
def get_batch(project: str) -> dict[str, Any]:
    if project not in ("yallaplays", "fionera"):
        raise HTTPException(status_code=400,
                            detail="project must be 'yallaplays' or 'fionera'")
    try:
        batch = _gen.build_batch(project)
        return batch.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

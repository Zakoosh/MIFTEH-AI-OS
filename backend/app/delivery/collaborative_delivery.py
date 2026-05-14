"""
collaborative_delivery.py — Collaborative delivery sessions integrating
agent roles from the Collaboration Layer into delivery execution.
"""

from __future__ import annotations

from .models import CollaborativeDeliverySession, _sim_score, _sim_success

# Mission → agent roster (mirrors collaboration layer without a direct import)
_MISSION_AGENTS: dict[str, list[str]] = {
    "seo-growth": [
        "marketing-seo-specialist", "engineering-frontend-developer",
        "product-manager",
    ],
    "feature-development": [
        "engineering-backend-developer", "engineering-frontend-developer",
        "product-manager", "qa-engineer",
    ],
    "dashboard-improvement": [
        "ux-designer", "engineering-frontend-developer",
        "product-manager", "data-analyst",
    ],
    "category-optimization": [
        "marketing-seo-specialist", "ux-designer", "product-manager",
    ],
    "performance-optimization": [
        "engineering-performance-optimizer", "engineering-backend-developer",
    ],
    "monetization-strategy": [
        "product-manager", "engineering-backend-developer",
        "marketing-seo-specialist",
    ],
}

_ROLE_MAP: dict[str, str] = {
    "marketing-seo-specialist":         "implementer",
    "engineering-backend-developer":    "implementer",
    "engineering-frontend-developer":   "implementer",
    "engineering-performance-optimizer":"implementer",
    "product-manager":                  "reviewer",
    "qa-engineer":                      "validator",
    "data-analyst":                     "reviewer",
    "ux-designer":                      "reviewer",
}


def create_session(
    plan_id: str,
    work_item_id: str,
    project: str,
    mission: str,
    task_type: str,
) -> CollaborativeDeliverySession:
    agents = _MISSION_AGENTS.get(mission, _MISSION_AGENTS["feature-development"])
    roles  = {a: _ROLE_MAP.get(a, "implementer") for a in agents}

    contributions = []
    for agent in agents:
        seed  = f"{work_item_id}_{agent}_contribution"
        score = _sim_score(seed, 82.0, 18.0)
        contributions.append({
            "agent":    agent,
            "role":     roles[agent],
            "score":    score,
            "approved": score >= 70.0,
            "output":   f"{agent} completed delivery contribution (score: {score})",
        })

    consensus = round(
        sum(c["score"] for c in contributions) / len(contributions), 1
    ) if contributions else 85.0

    approved = consensus >= 75.0

    return CollaborativeDeliverySession(
        session_id     = f"cds_{plan_id}",
        plan_id        = plan_id,
        work_item_id   = work_item_id,
        project        = project,
        mission        = mission,
        agents_assigned= agents,
        roles          = roles,
        contributions  = contributions,
        review_status  = "approved" if approved else "rejected",
        consensus_score= consensus,
        approved       = approved,
    )

"""
task_distribution.py — Distributes execution tasks across the agent roster.

Each agent in a session is assigned a specific task description based on:
  • Their role (implementer / reviewer / validator)
  • The mission type
  • The proposal being processed

Ensures reviewer/validator separation is maintained during distribution.
"""

from __future__ import annotations

from typing import Any

from .models import ROLE_IMPLEMENTER, ROLE_REVIEWER, ROLE_VALIDATOR, ROLE_ORCHESTRATOR, ROLE_QA
from .agent_roles import build_role_map, get_mission, build_agent_role


# ---------------------------------------------------------------------------
# Task templates per (role, mission_type)
# ---------------------------------------------------------------------------

_IMPLEMENTER_TASKS: dict[str, str] = {
    "seo-growth":          "Implement SEO metadata improvements and structured data enhancements",
    "dashboard-improvement": "Implement dashboard layout changes and analytics widget integrations",
    "category-optimization": "Implement game category restructuring and navigation improvements",
    "security-review":     "Implement security hardening patches and input validation",
    "landing-page-update": "Implement landing page copy updates and conversion optimizations",
    "portfolio-analytics": "Implement portfolio analytics components and data pipeline",
    "watchlist-feature":   "Implement watchlist configuration and real-time alert system",
    "manifest-optimization": "Implement PWA manifest enhancements and offline caching",
    "metadata-update":     "Implement metadata, OG tags, and JSON-LD structured data",
    "widget-development":  "Implement analytics widget components and data integrations",
    "growth-campaign":     "Implement growth campaign assets and tracking infrastructure",
    "financial-reporting": "Implement financial report generation and visualization",
    "_default":            "Implement the assigned collaborative task",
}

_REVIEWER_TASKS: dict[str, str] = {
    "seo-growth":          "Review SEO implementation for correctness, coverage, and best practices",
    "dashboard-improvement": "Review dashboard changes for UX quality and data accuracy",
    "category-optimization": "Review category structure for discoverability and user journey alignment",
    "security-review":     "Review security patches for completeness and no regression",
    "landing-page-update": "Review landing page changes for brand alignment and conversion impact",
    "portfolio-analytics": "Review analytics implementation for data integrity and performance",
    "watchlist-feature":   "Review watchlist feature for functional correctness and edge cases",
    "manifest-optimization": "Review manifest changes for spec compliance and browser compatibility",
    "metadata-update":     "Review metadata for schema validity and SEO correctness",
    "widget-development":  "Review widget code for performance, accessibility, and reliability",
    "growth-campaign":     "Review campaign strategy for ROI potential and risk",
    "financial-reporting": "Review financial report accuracy and compliance",
    "_default":            "Review the implementation for quality and correctness",
}

_VALIDATOR_TASKS: dict[str, str] = {
    "seo-growth":          "Independently validate SEO impact metrics and performance benchmarks",
    "dashboard-improvement": "Independently validate dashboard performance and load-time benchmarks",
    "category-optimization": "Independently validate category changes against real user behaviour data",
    "security-review":     "Independently validate security posture using penetration test scenarios",
    "landing-page-update": "Independently validate page speed, accessibility, and conversion metrics",
    "portfolio-analytics": "Independently validate analytics accuracy against known portfolio data",
    "watchlist-feature":   "Independently validate alert accuracy and latency under load",
    "manifest-optimization": "Independently validate PWA install flow and offline behaviour",
    "metadata-update":     "Independently validate structured data using schema.org validators",
    "widget-development":  "Independently validate widget rendering, data accuracy, and edge cases",
    "growth-campaign":     "Independently validate campaign targeting and attribution logic",
    "financial-reporting": "Independently validate report calculations against source data",
    "_default":            "Independently validate the deliverable against acceptance criteria",
}

_ORCHESTRATOR_TASKS: dict[str, str] = {
    "_default": "Coordinate the collaboration session, resolve conflicts, and ensure timely completion",
}


def _get_task(templates: dict[str, str], mission: str) -> str:
    return templates.get(mission.lower(), templates["_default"])


# ---------------------------------------------------------------------------
# TaskDistributor
# ---------------------------------------------------------------------------

class TaskDistributor:
    """
    Produces a task assignment plan for each agent in a collaboration session.

    Returns a list of TaskAssignment dicts:
      {agent_name, role, task, mission, proposal_id}
    """

    def distribute(
        self,
        mission: str,
        proposal_id: str = "",
        proposal_title: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        """
        Build the full task distribution plan for a mission.

        Returns:
          {
            "mission": str,
            "implementers": [str, ...],
            "reviewers":    [str, ...],
            "validators":   [str, ...],
            "agent_roles":  {agent: role, ...},
            "task_assignments": [{agent, role, task}, ...],
            "role_separation_valid": bool,
          }
        """
        m = get_mission(mission)

        implementers = m.get("implementers", [])
        reviewers    = m.get("reviewers", [])
        validators   = m.get("validators", [])
        orchestrator = m.get("orchestrator")

        role_map = build_role_map(implementers, reviewers, validators, orchestrator)

        # Build task assignments
        assignments: list[dict] = []

        for agent in implementers:
            assignments.append({
                "agent_name":  agent,
                "role":        ROLE_IMPLEMENTER,
                "task":        _get_task(_IMPLEMENTER_TASKS, mission),
                "mission":     mission,
                "proposal_id": proposal_id,
                "proposal_title": proposal_title or mission,
            })

        for agent in reviewers:
            if agent not in [a["agent_name"] for a in assignments]:   # enforce separation
                assignments.append({
                    "agent_name":  agent,
                    "role":        ROLE_REVIEWER,
                    "task":        _get_task(_REVIEWER_TASKS, mission),
                    "mission":     mission,
                    "proposal_id": proposal_id,
                    "proposal_title": proposal_title or mission,
                })

        for agent in validators:
            assigned = [a["agent_name"] for a in assignments]
            if agent not in assigned:                                   # enforce separation
                assignments.append({
                    "agent_name":  agent,
                    "role":        ROLE_VALIDATOR,
                    "task":        _get_task(_VALIDATOR_TASKS, mission),
                    "mission":     mission,
                    "proposal_id": proposal_id,
                    "proposal_title": proposal_title or mission,
                })

        if orchestrator:
            assignments.append({
                "agent_name":  orchestrator,
                "role":        ROLE_ORCHESTRATOR,
                "task":        _get_task(_ORCHESTRATOR_TASKS, mission),
                "mission":     mission,
                "proposal_id": proposal_id,
                "proposal_title": proposal_title or mission,
            })

        # Validate separation
        impl_set  = set(implementers)
        rev_set   = set(reviewers)
        val_set   = set(validators)
        valid = (
            not impl_set.intersection(rev_set) and
            not impl_set.intersection(val_set) and
            not rev_set.intersection(val_set)
        )

        return {
            "mission":              mission,
            "project_id":           project_id,
            "proposal_id":          proposal_id,
            "proposal_title":       proposal_title or mission,
            "implementers":         implementers,
            "reviewers":            reviewers,
            "validators":           validators,
            "orchestrator":         [orchestrator] if orchestrator else [],
            "all_agents":           [a["agent_name"] for a in assignments],
            "agent_roles":          role_map,
            "task_assignments":     assignments,
            "role_separation_valid": valid,
        }

    def validate_separation(
        self,
        implementers: list[str],
        reviewers: list[str],
        validators: list[str],
    ) -> tuple[bool, list[str]]:
        """Return (valid, list_of_violations)."""
        violations = []
        overlap_ir = set(implementers) & set(reviewers)
        overlap_iv = set(implementers) & set(validators)
        overlap_rv = set(reviewers) & set(validators)

        if overlap_ir:
            violations.append(f"Agents cannot be both implementer and reviewer: {sorted(overlap_ir)}")
        if overlap_iv:
            violations.append(f"Agents cannot be both implementer and validator: {sorted(overlap_iv)}")
        if overlap_rv:
            violations.append(f"Agents cannot be both reviewer and validator: {sorted(overlap_rv)}")

        return len(violations) == 0, violations


# Module-level singleton
_distributor = TaskDistributor()


def get_distributor() -> TaskDistributor:
    return _distributor

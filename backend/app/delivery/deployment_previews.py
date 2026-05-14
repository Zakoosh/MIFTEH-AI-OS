"""
deployment_previews.py — Generates deployment preview documents.

Previews describe exactly what will change before any change is applied.
"""

from __future__ import annotations

from typing import Any

from .models import DeploymentPreview


# ---------------------------------------------------------------------------
# File and page templates per task type
# ---------------------------------------------------------------------------

_AFFECTED: dict[str, dict[str, list[str]]] = {
    "seo_campaign": {
        "files": [
            "src/pages/[category]/index.tsx",
            "src/components/SEOHead.tsx",
            "public/sitemap.xml",
            "src/data/structured-data.json",
        ],
        "pages": ["/games/[category]", "/", "/sitemap.xml"],
    },
    "feature": {
        "files": [
            "src/features/[feature]/index.tsx",
            "src/api/[feature].ts",
            "src/store/[feature]Slice.ts",
            "tests/[feature].test.ts",
        ],
        "pages": ["/app/[feature]", "/api/[feature]"],
    },
    "implementation": {
        "files": [
            "backend/app/[service]/service.py",
            "backend/app/api/[service].py",
            "backend/requirements.txt",
            "infra/docker-compose.yml",
        ],
        "pages": ["/api/[service]", "/health"],
    },
    "dashboard": {
        "files": [
            "src/components/Dashboard/[widget].tsx",
            "src/api/dashboard.ts",
            "src/styles/dashboard.css",
        ],
        "pages": ["/dashboard", "/app"],
    },
    "widget": {
        "files": [
            "src/components/widgets/[widget].tsx",
            "src/api/widgets/[widget].ts",
        ],
        "pages": ["/dashboard", "/app/portfolio"],
    },
    "watchlist": {
        "files": [
            "src/features/watchlist/index.tsx",
            "src/api/watchlist.ts",
            "backend/app/api/watchlist.py",
        ],
        "pages": ["/app/watchlist"],
    },
    "analytics": {
        "files": [
            "src/features/analytics/[chart].tsx",
            "backend/app/analytics/compute.py",
            "src/api/analytics.ts",
        ],
        "pages": ["/app/analytics", "/app/portfolio/attribution"],
    },
    "ux": {
        "files": [
            "src/components/[component]/index.tsx",
            "src/styles/[component].css",
            "src/tokens/colors.ts",
        ],
        "pages": ["/", "/app/*"],
    },
    "monetization": {
        "files": [
            "src/features/billing/Checkout.tsx",
            "backend/app/billing/stripe_service.py",
            "src/api/billing.ts",
        ],
        "pages": ["/pricing", "/checkout", "/app/subscription"],
    },
    "campaign":      {"files": ["public/meta/*.json", "src/pages/landing.tsx"], "pages": ["/", "/app-store"]},
    "optimization":  {"files": ["src/experiments/[test].ts", "src/components/Hero.tsx"], "pages": ["/", "/app"]},
    "content":       {"files": ["content/blog/[post].md", "public/sitemap.xml"], "pages": ["/blog/[post]"]},
    "roadmap":       {"files": ["docs/roadmap.md", "src/data/roadmap.json"], "pages": ["/roadmap"]},
}

_RISK: dict[str, str] = {
    "critical": "high",
    "high":     "medium",
    "medium":   "low",
    "low":      "minimal",
}

_ROLLBACK: dict[str, str] = {
    "seo_campaign":   "Revert metadata and sitemap; re-submit previous canonical sitemap.",
    "feature":        "Disable feature flag; roll back database migration if required.",
    "implementation": "Redeploy previous container image; restore configuration backup.",
    "dashboard":      "Re-deploy previous dashboard bundle; disable widget feature flag.",
    "widget":         "Disable widget via feature flag; no database changes required.",
    "watchlist":      "Restore previous watchlist schema; no user data deleted.",
    "analytics":      "Re-point analytics endpoint to previous compute version.",
    "ux":             "Redeploy previous CSS/JS bundle; no data changes.",
    "monetization":   "Cancel Stripe integration config; restore previous checkout flow.",
    "campaign":       "Restore previous App Store metadata via developer console.",
    "optimization":   "End experiment; restore control variant to 100% traffic.",
    "content":        "Unpublish post; restore previous sitemap.",
    "roadmap":        "No code changes — document-only rollback.",
}


def generate(exec_plan: Any) -> DeploymentPreview:
    """Generate a DeploymentPreview from a planning-layer ExecutionPlan."""
    task_type  = exec_plan.task_type
    templates  = _AFFECTED.get(task_type, _AFFECTED["feature"])
    risk_level = _RISK.get(exec_plan.priority, "low")

    affected_files = [
        f.replace("[category]", "survival-games")
         .replace("[feature]", task_type.replace("_", "-"))
         .replace("[service]", task_type.replace("_", "-"))
         .replace("[widget]", task_type.replace("_", "-"))
         .replace("[component]", task_type.replace("_", "-"))
         .replace("[chart]", "attribution")
         .replace("[test]", "hero-ab-test")
         .replace("[post]", "best-" + exec_plan.project + "-features")
        for f in templates["files"]
    ]

    affected_pages = [
        p.replace("[category]", "survival-games")
         .replace("[feature]", task_type.replace("_", "-"))
         .replace("[service]", task_type.replace("_", "-"))
         .replace("[widget]", task_type.replace("_", "-"))
         .replace("[post]", "best-" + exec_plan.project + "-features")
        for p in templates["pages"]
    ]

    changes = len(affected_files) * 12 + len(exec_plan.steps) * 8

    summary = (
        f"{len(affected_files)} files modified, {len(affected_pages)} pages affected. "
        f"Risk level: {risk_level}. Rollback strategy: available."
    )

    preview_content: dict[str, Any] = {
        "task_type":           task_type,
        "total_steps":         len(exec_plan.steps),
        "phases":              exec_plan.phases,
        "step_titles":         [s.get("title", "") for s in exec_plan.steps[:5]],
        "collaboration_mission": exec_plan.metadata.get("collaboration_mission", ""),
        "apply_proposal_type": exec_plan.metadata.get("apply_proposal_type", ""),
        "validation_required": exec_plan.validation_required,
        "tags":                exec_plan.tags,
    }

    return DeploymentPreview(
        preview_id         = f"pr_{exec_plan.work_item_id}",
        plan_id            = exec_plan.plan_id,
        work_item_id       = exec_plan.work_item_id,
        project            = exec_plan.project,
        title              = exec_plan.title,
        summary            = summary,
        affected_files     = affected_files,
        affected_pages     = affected_pages,
        estimated_changes  = changes,
        risk_level         = risk_level,
        rollback_strategy  = _ROLLBACK.get(task_type, "Redeploy previous version."),
        preview_content    = preview_content,
    )

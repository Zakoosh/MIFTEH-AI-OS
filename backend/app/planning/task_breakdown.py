"""
task_breakdown.py — Step-by-step task templates for each work item type.

Each task_type maps to an ordered list of step templates.  Templates
are materialised into ExecutionStep objects by bind_steps().
"""

from __future__ import annotations

from typing import Any

from .models import (
    ExecutionStep,
    PHASE_PREPARATION, PHASE_IMPLEMENTATION,
    PHASE_REVIEW, PHASE_DEPLOYMENT, PHASE_VALIDATION,
)


# ---------------------------------------------------------------------------
# Step template definition
# (title, description, phase, estimated_hours, agent_role, validation_required)
# ---------------------------------------------------------------------------

_T = tuple[str, str, str, float, str, bool]

_SEO_CAMPAIGN: list[_T] = [
    ("Keyword research & gap analysis",
     "Identify primary, secondary, and long-tail keywords; analyse competitor rankings.",
     PHASE_PREPARATION, 4.0, "marketing-seo-specialist", False),
    ("Create / update category landing page",
     "Build or refresh the target category page with optimised heading hierarchy and copy.",
     PHASE_IMPLEMENTATION, 6.0, "engineering-frontend-developer", False),
    ("Generate SEO metadata",
     "Write title tags, meta descriptions, Open Graph and Twitter Card tags for all target pages.",
     PHASE_IMPLEMENTATION, 2.0, "marketing-seo-specialist", False),
    ("Add JSON-LD structured data",
     "Implement GameApplication / Article / BreadcrumbList schema on all affected pages.",
     PHASE_IMPLEMENTATION, 3.0, "engineering-frontend-developer", True),
    ("Internal linking implementation",
     "Add contextual internal links from high-traffic pages to the new cluster hub.",
     PHASE_IMPLEMENTATION, 2.0, "engineering-frontend-developer", False),
    ("Submit sitemap update",
     "Regenerate XML sitemap, ping Google Search Console, verify indexation.",
     PHASE_DEPLOYMENT, 1.0, "marketing-seo-specialist", False),
    ("SEO audit & validation",
     "Run Lighthouse SEO audit; verify metadata, schema, and Core Web Vitals pass.",
     PHASE_VALIDATION, 2.0, "marketing-seo-specialist", True),
]

_FEATURE: list[_T] = [
    ("Technical specification",
     "Write feature spec: data models, API contract, edge cases, acceptance criteria.",
     PHASE_PREPARATION, 4.0, "product-manager", False),
    ("API contract design",
     "Define request/response schemas, error codes, auth requirements, and versioning.",
     PHASE_PREPARATION, 3.0, "engineering-backend-developer", False),
    ("Backend implementation",
     "Implement services, data layer, and REST/GraphQL endpoints per the spec.",
     PHASE_IMPLEMENTATION, 16.0, "engineering-backend-developer", False),
    ("Frontend implementation",
     "Build React/Next components, state management, and API integration.",
     PHASE_IMPLEMENTATION, 12.0, "engineering-frontend-developer", False),
    ("Unit & integration tests",
     "Achieve ≥80% branch coverage; add integration tests for critical paths.",
     PHASE_REVIEW, 6.0, "engineering-backend-developer", True),
    ("QA review",
     "Exploratory testing; regression pass; verify against acceptance criteria.",
     PHASE_REVIEW, 4.0, "qa-engineer", True),
    ("Staging deployment & smoke test",
     "Deploy to staging environment; run automated smoke suite.",
     PHASE_DEPLOYMENT, 2.0, "engineering-backend-developer", True),
    ("Production deployment",
     "Feature-flag rollout; monitor error rates and latency for 24 h post-deploy.",
     PHASE_DEPLOYMENT, 2.0, "engineering-backend-developer", True),
]

_IMPLEMENTATION: list[_T] = [
    ("Architecture review",
     "Review current architecture; identify integration points and risks.",
     PHASE_PREPARATION, 3.0, "engineering-backend-developer", False),
    ("Environment & dependency setup",
     "Configure infrastructure, install dependencies, set up CI pipeline.",
     PHASE_PREPARATION, 4.0, "engineering-backend-developer", False),
    ("Core implementation",
     "Implement primary functionality; write clean, testable code.",
     PHASE_IMPLEMENTATION, 14.0, "engineering-backend-developer", False),
    ("Integration & connectivity",
     "Wire up integrations with dependent systems; test boundaries.",
     PHASE_IMPLEMENTATION, 6.0, "engineering-backend-developer", False),
    ("Performance testing",
     "Load-test key paths; verify latency and throughput against SLOs.",
     PHASE_REVIEW, 4.0, "engineering-performance-optimizer", True),
    ("Security review",
     "Static analysis, dependency audit, input-validation review.",
     PHASE_REVIEW, 3.0, "engineering-backend-developer", True),
    ("Documentation",
     "Update API docs, runbook, and CHANGELOG.",
     PHASE_REVIEW, 2.0, "engineering-backend-developer", False),
    ("Production deployment",
     "Staged rollout with feature flag; post-deploy monitoring.",
     PHASE_DEPLOYMENT, 2.0, "engineering-backend-developer", True),
]

_UX: list[_T] = [
    ("User research & competitive analysis",
     "Interview users (or review existing research); audit competitor patterns.",
     PHASE_PREPARATION, 4.0, "ux-designer", False),
    ("Information architecture design",
     "Define IA: sitemaps, user flows, content hierarchy.",
     PHASE_PREPARATION, 3.0, "ux-designer", False),
    ("Wireframes",
     "Low-fidelity wireframes for all key screens; align with PM on scope.",
     PHASE_PREPARATION, 6.0, "ux-designer", False),
    ("High-fidelity mockups",
     "Produce pixel-perfect designs in Figma including responsive breakpoints.",
     PHASE_IMPLEMENTATION, 8.0, "ux-designer", False),
    ("Prototype testing",
     "Run 5-user usability test on interactive prototype; capture findings.",
     PHASE_REVIEW, 4.0, "ux-designer", True),
    ("Developer handoff",
     "Prepare design tokens, component specs, and interaction notes.",
     PHASE_IMPLEMENTATION, 2.0, "ux-designer", False),
    ("Frontend implementation",
     "Build components per design spec; handle responsive and a11y requirements.",
     PHASE_IMPLEMENTATION, 10.0, "engineering-frontend-developer", False),
    ("UX acceptance testing",
     "Verify implementation against designs; check a11y compliance (WCAG 2.1 AA).",
     PHASE_VALIDATION, 3.0, "ux-designer", True),
]

_DASHBOARD: list[_T] = [
    ("Dashboard UX wireframe",
     "Sketch layout, widget placement, and data hierarchy.",
     PHASE_PREPARATION, 3.0, "ux-designer", False),
    ("Component specification",
     "Define data contracts between dashboard widgets and backend APIs.",
     PHASE_PREPARATION, 2.0, "product-manager", False),
    ("Backend data API",
     "Implement or extend data endpoints that widgets consume.",
     PHASE_IMPLEMENTATION, 8.0, "engineering-backend-developer", False),
    ("Frontend component build",
     "Build dashboard layout, widget shell, and chart components.",
     PHASE_IMPLEMENTATION, 10.0, "engineering-frontend-developer", False),
    ("Responsive & cross-browser testing",
     "Verify layout on mobile, tablet, and desktop across major browsers.",
     PHASE_REVIEW, 3.0, "engineering-frontend-developer", True),
    ("Performance profiling",
     "Measure render time; optimise bundle size and lazy-loading.",
     PHASE_REVIEW, 2.0, "engineering-performance-optimizer", True),
    ("QA sign-off",
     "Full regression on dashboard; verify data accuracy.",
     PHASE_VALIDATION, 3.0, "qa-engineer", True),
]

_WIDGET: list[_T] = [
    ("Widget specification",
     "Define data source, refresh interval, state management, and visual spec.",
     PHASE_PREPARATION, 2.0, "product-manager", False),
    ("Backend data endpoint",
     "Implement the API endpoint(s) the widget consumes.",
     PHASE_IMPLEMENTATION, 5.0, "engineering-backend-developer", False),
    ("Widget component",
     "Build the React widget component with loading, error, and empty states.",
     PHASE_IMPLEMENTATION, 6.0, "engineering-frontend-developer", False),
    ("Responsive layout",
     "Ensure widget renders correctly across screen sizes.",
     PHASE_REVIEW, 2.0, "engineering-frontend-developer", False),
    ("Widget integration test",
     "Verify real data flow end-to-end; check refresh logic.",
     PHASE_VALIDATION, 2.0, "qa-engineer", True),
]

_WATCHLIST: list[_T] = [
    ("Watchlist data model",
     "Define schema: tickers, alerts, display settings, sharing metadata.",
     PHASE_PREPARATION, 2.0, "engineering-backend-developer", False),
    ("Backend CRUD & alert engine",
     "Implement create, read, update, delete + alert trigger service.",
     PHASE_IMPLEMENTATION, 8.0, "engineering-backend-developer", False),
    ("Frontend watchlist UI",
     "Build watchlist table, inline editing, and alert configuration UI.",
     PHASE_IMPLEMENTATION, 7.0, "engineering-frontend-developer", False),
    ("Push & email notifications",
     "Wire alert triggers to push notification and email delivery services.",
     PHASE_IMPLEMENTATION, 4.0, "engineering-backend-developer", False),
    ("Watchlist QA",
     "Test CRUD, alert firing, notification delivery, and edge cases.",
     PHASE_VALIDATION, 3.0, "qa-engineer", True),
]

_ANALYTICS: list[_T] = [
    ("Analytics requirements",
     "Define metrics, dimensions, data sources, and retention windows.",
     PHASE_PREPARATION, 3.0, "data-analyst", False),
    ("Data pipeline",
     "Build or extend ETL pipeline to ingest required raw data.",
     PHASE_IMPLEMENTATION, 10.0, "engineering-backend-developer", False),
    ("Analytics computation layer",
     "Implement aggregation, statistical calculations, and caching.",
     PHASE_IMPLEMENTATION, 8.0, "data-analyst", False),
    ("Visualisation layer",
     "Build chart components: time-series, waterfall, heatmap.",
     PHASE_IMPLEMENTATION, 6.0, "engineering-frontend-developer", False),
    ("Data accuracy validation",
     "Cross-validate computed results against source-of-truth data sets.",
     PHASE_VALIDATION, 4.0, "data-analyst", True),
]

_CAMPAIGN: list[_T] = [
    ("ASO / campaign audit",
     "Audit current metadata, screenshots, and conversion funnel.",
     PHASE_PREPARATION, 2.0, "marketing-seo-specialist", False),
    ("Copy & creative production",
     "Write optimised copy; produce new screenshots / video assets.",
     PHASE_IMPLEMENTATION, 6.0, "marketing-seo-specialist", False),
    ("Metadata update",
     "Push updated title, subtitle, keywords, and description to store listings.",
     PHASE_DEPLOYMENT, 1.0, "marketing-seo-specialist", False),
    ("Post-update monitoring",
     "Track impression, conversion, and install rate for 2 weeks post-update.",
     PHASE_VALIDATION, 2.0, "marketing-seo-specialist", True),
]

_OPTIMIZATION: list[_T] = [
    ("Baseline measurement",
     "Capture current performance metrics as baseline.",
     PHASE_PREPARATION, 2.0, "data-analyst", False),
    ("A/B test setup",
     "Configure experiment: variants, traffic split, success metric, duration.",
     PHASE_IMPLEMENTATION, 3.0, "product-manager", False),
    ("Variant implementation",
     "Build experiment variants per spec.",
     PHASE_IMPLEMENTATION, 6.0, "engineering-frontend-developer", False),
    ("Statistical analysis",
     "Analyse results at statistical significance (p<0.05); decide winner.",
     PHASE_VALIDATION, 3.0, "data-analyst", True),
    ("Winner rollout",
     "Deploy winning variant to 100% of traffic; archive experiment.",
     PHASE_DEPLOYMENT, 1.0, "engineering-frontend-developer", False),
]

_MONETIZATION: list[_T] = [
    ("Revenue model design",
     "Define pricing tiers, feature gates, and billing integration.",
     PHASE_PREPARATION, 4.0, "product-manager", False),
    ("Payment integration",
     "Integrate Stripe or equivalent; implement subscription lifecycle.",
     PHASE_IMPLEMENTATION, 10.0, "engineering-backend-developer", False),
    ("Paywall UI",
     "Build upgrade prompts, plan comparison page, and checkout flow.",
     PHASE_IMPLEMENTATION, 8.0, "engineering-frontend-developer", False),
    ("Billing QA",
     "Test payment flows, cancellation, refunds, and edge cases in Stripe test mode.",
     PHASE_REVIEW, 4.0, "qa-engineer", True),
    ("Revenue tracking",
     "Wire analytics events for trial starts, conversions, and churn.",
     PHASE_VALIDATION, 2.0, "data-analyst", True),
]

_CONTENT: list[_T] = [
    ("Content brief",
     "Define topic, target keyword, audience, and desired outcome.",
     PHASE_PREPARATION, 1.0, "marketing-seo-specialist", False),
    ("Draft writing",
     "Produce first draft with SEO structure (H1/H2, internal links).",
     PHASE_IMPLEMENTATION, 4.0, "content-writer", False),
    ("Editorial review",
     "Review for accuracy, tone, and SEO compliance.",
     PHASE_REVIEW, 2.0, "marketing-seo-specialist", True),
    ("Publish & index",
     "Publish, add to sitemap, submit to Search Console.",
     PHASE_DEPLOYMENT, 1.0, "marketing-seo-specialist", False),
]

_ROADMAP: list[_T] = [
    ("Roadmap prioritisation",
     "Score items by impact / effort; align with OKRs.",
     PHASE_PREPARATION, 3.0, "product-manager", False),
    ("Dependency mapping",
     "Identify cross-team dependencies and sequencing constraints.",
     PHASE_PREPARATION, 2.0, "product-manager", False),
    ("Milestone definition",
     "Define delivery milestones with measurable success criteria.",
     PHASE_PREPARATION, 2.0, "product-manager", False),
    ("Kick-off & briefing",
     "Communicate roadmap to engineering and stakeholders.",
     PHASE_IMPLEMENTATION, 1.0, "product-manager", False),
    ("Progress review",
     "Weekly checkpoint: track against milestones; adjust scope if needed.",
     PHASE_REVIEW, 2.0, "product-manager", True),
]

_STEP_MAP: dict[str, list[_T]] = {
    "seo_campaign":    _SEO_CAMPAIGN,
    "feature":         _FEATURE,
    "implementation":  _IMPLEMENTATION,
    "ux":              _UX,
    "dashboard":       _DASHBOARD,
    "monetization":    _MONETIZATION,
    "campaign":        _CAMPAIGN,
    "optimization":    _OPTIMIZATION,
    "content":         _CONTENT,
    "roadmap":         _ROADMAP,
    "watchlist":       _WATCHLIST,
    "widget":          _WIDGET,
    "analytics":       _ANALYTICS,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_step_templates(task_type: str) -> list[_T]:
    return _STEP_MAP.get(task_type, _FEATURE)


def bind_steps(plan_id: str, work_item_id: str, task_type: str) -> list[ExecutionStep]:
    """Materialise step templates into ExecutionStep objects."""
    templates = get_step_templates(task_type)
    steps: list[ExecutionStep] = []
    for i, (title, desc, phase, hours, role, val) in enumerate(templates, start=1):
        steps.append(ExecutionStep(
            step_id              = f"step_{work_item_id}_{i:02d}",
            plan_id              = plan_id,
            sequence             = i,
            title                = title,
            description          = desc,
            phase                = phase,
            estimated_hours      = hours,
            assigned_agent_role  = role,
            step_dependencies    = [f"step_{work_item_id}_{i-1:02d}"] if i > 1 else [],
            validation_required  = val,
        ))
    return steps


def has_validation_step(task_type: str) -> bool:
    return any(t[5] for t in get_step_templates(task_type))


def step_count(task_type: str) -> int:
    return len(get_step_templates(task_type))


def total_hours(task_type: str) -> float:
    return sum(t[3] for t in get_step_templates(task_type))


def step_titles(task_type: str) -> list[str]:
    return [t[0] for t in get_step_templates(task_type)]

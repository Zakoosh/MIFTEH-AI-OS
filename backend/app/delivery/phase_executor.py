"""
phase_executor.py — Executes individual delivery phases step by step.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import (
    DeliveryStep, DeliveryPhase,
    PHASE_COMPLETED, PHASE_FAILED,
    _sim_success, _now,
)

# Simulated step outputs keyed by task type (cycling through outputs)
_OUTPUTS: dict[str, list[str]] = {
    "seo_campaign": [
        "47 target keywords identified; 3 competitor gaps found",
        "Category landing page created with optimised H1/H2 structure",
        "SEO metadata generated: title 54 chars, description 147 chars",
        "JSON-LD structured data validated with schema.org validator",
        "12 internal links added to high-traffic parent pages",
        "Sitemap regenerated (156 URLs); pinged Search Console",
        "Lighthouse SEO score: 98/100; all checks green",
    ],
    "feature": [
        "Feature specification reviewed and approved by PM",
        "API contract defined: 4 endpoints, OpenAPI spec updated",
        "Backend services implemented: 3 services, 12 endpoints",
        "Frontend components built: 5 components, responsive",
        "Unit test coverage: 84% branch coverage achieved",
        "QA review complete: 0 critical, 2 minor issues resolved",
        "Staging deployment succeeded; smoke tests passed",
        "Production deployment via feature flag; monitoring active",
    ],
    "implementation": [
        "Architecture review completed; integration points identified",
        "Environment configured; CI pipeline updated",
        "Core implementation complete: 2 services, 8 modules",
        "Integration layer wired up; boundary tests passing",
        "Load test: 600 RPS, p99 < 280ms, error rate 0.01%",
        "Security audit: 0 critical, 1 low finding resolved",
        "Documentation updated in API reference and runbook",
        "Production deployment; post-deploy monitoring active for 24 h",
    ],
    "dashboard": [
        "Dashboard UX wireframe reviewed and signed off",
        "Component data contracts defined and documented",
        "Backend data API implemented: 3 endpoints",
        "Dashboard components built with responsive layout",
        "Cross-browser testing passed on Chrome, Firefox, Safari",
        "Performance profile: FCP 0.8 s, LCP 1.4 s",
        "QA sign-off complete; data accuracy verified",
    ],
    "widget": [
        "Widget specification approved",
        "Backend data endpoint implemented",
        "Widget component built with loading/error/empty states",
        "Responsive layout verified on 375–1440 px",
        "Integration test: real data end-to-end verified",
    ],
    "watchlist": [
        "Watchlist data schema defined",
        "CRUD API + alert trigger service implemented",
        "Watchlist UI built with inline editing",
        "Push and email notifications wired and tested",
        "QA: CRUD, alerts, and notifications verified",
    ],
    "analytics": [
        "Analytics requirements and metrics defined",
        "ETL pipeline extended for new data sources",
        "Aggregation and computation layer implemented",
        "Chart components built: time-series, waterfall",
        "Data accuracy validated against source of truth",
    ],
    "ux": [
        "User research review completed",
        "IA and user flows documented",
        "Wireframes reviewed and approved",
        "High-fidelity mockups produced in Figma",
        "Prototype usability test: 5/5 task success rate",
        "Developer handoff package prepared",
        "Implementation complete; a11y audit passed (WCAG 2.1 AA)",
        "UX acceptance testing passed by designer",
    ],
    "monetization": [
        "Revenue model and pricing tiers finalised",
        "Stripe subscription integration implemented",
        "Paywall UI and checkout flow built",
        "Billing QA: test-mode checkout, cancellation, refund verified",
        "Revenue tracking events wired and validated",
    ],
}
_DEFAULT_OUTPUT = [
    "Task completed successfully",
    "Validation passed",
    "Implementation finished",
    "Review approved",
    "Deployment confirmed",
]


def _step_output(task_type: str, idx: int, success: bool) -> str:
    outputs = _OUTPUTS.get(task_type, _DEFAULT_OUTPUT)
    if success:
        return outputs[idx % len(outputs)]
    return f"Step failed: unexpected error during execution (simulated)"


def execute_phase(
    phase_name: str,
    steps: list[dict[str, Any]],
    plan_id: str,
    run_id: str,
    task_type: str,
    phase_number: int = 1,
) -> DeliveryPhase:
    """Execute all steps belonging to a single phase and return a DeliveryPhase."""
    if not steps:
        return DeliveryPhase(
            phase_id       = f"ph_{plan_id}_{phase_name}",
            plan_id        = plan_id,
            run_id         = run_id,
            phase_name     = phase_name,
            phase_number   = phase_number,
            steps          = [],
            total_steps    = 0,
            completed_steps= 0,
            failed_steps   = 0,
            status         = PHASE_COMPLETED,
            validation_result = {},
            duration_seconds  = 0.0,
            rollback_available= True,
        )

    executed: list[dict] = []
    completed = 0
    failed    = 0

    for i, raw_step in enumerate(steps):
        seed    = f"{plan_id}_{phase_name}_{raw_step.get('step_id', i)}"
        success = _sim_success(seed, 0.96)

        ds = DeliveryStep(
            step_id             = raw_step.get("step_id", f"step_{plan_id}_{i}"),
            plan_id             = plan_id,
            run_id              = run_id,
            sequence            = raw_step.get("sequence", i + 1),
            title               = raw_step.get("title", ""),
            phase               = phase_name,
            estimated_hours     = raw_step.get("estimated_hours", 4.0),
            actual_hours        = raw_step.get("estimated_hours", 4.0),
            assigned_agent_role = raw_step.get("assigned_agent_role", ""),
            status              = PHASE_COMPLETED if success else PHASE_FAILED,
            validation_required = raw_step.get("validation_required", False),
            output              = _step_output(task_type, i, success),
            error               = "" if success else "Execution error (simulated)",
            simulated           = True,
        )
        executed.append(ds.to_dict())
        if success:
            completed += 1
        else:
            failed += 1

    overall = PHASE_COMPLETED if failed == 0 else (
        PHASE_FAILED if failed > len(steps) // 2 else PHASE_COMPLETED
    )

    return DeliveryPhase(
        phase_id          = f"ph_{plan_id}_{phase_name}",
        plan_id           = plan_id,
        run_id            = run_id,
        phase_name        = phase_name,
        phase_number      = phase_number,
        steps             = executed,
        total_steps       = len(steps),
        completed_steps   = completed,
        failed_steps      = failed,
        status            = overall,
        validation_result = {},      # filled in by validation_runner after this phase
        duration_seconds  = sum(s.get("estimated_hours", 4.0) for s in steps) * 0.1,
        rollback_available= True,
    )

"""
validation_runner.py — Executes validation checkpoints between phases.
"""

from __future__ import annotations

from datetime import datetime

from .models import ValidationCheckpoint, VALIDATION_PASSED, VALIDATION_FAILED, _sim_success


# Validation check sets per (task_type, phase)
_CHECKS: dict[str, dict[str, list[tuple[str, bool]]]] = {
    # (check_text, blocking)
    "seo_campaign": {
        "preparation":    [("Keyword research complete", True), ("Target pages identified", True)],
        "implementation": [("Meta tags present on all pages", True), ("JSON-LD schema valid", True),
                           ("Internal links added", False)],
        "deployment":     [("Sitemap submitted", True), ("Search Console indexation requested", False)],
        "validation":     [("Lighthouse SEO ≥ 90", True), ("No crawl errors", True), ("CWV pass", False)],
    },
    "feature": {
        "preparation":    [("Spec approved by PM", True), ("API contract reviewed", True)],
        "implementation": [("Backend tests passing", True), ("Frontend builds without error", True),
                           ("ESLint clean", False)],
        "review":         [("Unit test coverage ≥ 80%", True), ("QA sign-off", True),
                           ("Security scan clean", True)],
        "deployment":     [("Staging smoke tests pass", True), ("Feature flag active", True)],
        "validation":     [("Production monitoring clean", True), ("No regression alerts", True)],
    },
    "implementation": {
        "preparation":    [("Architecture reviewed", True)],
        "implementation": [("All services healthy", True), ("No build warnings", False)],
        "review":         [("Load test SLOs met", True), ("Security audit passed", True)],
        "deployment":     [("Rollback tested and confirmed", True), ("Post-deploy monitoring active", True)],
        "validation":     [("All integration tests pass", True), ("Error rate < 0.1%", True)],
    },
    "dashboard": {
        "implementation": [("Data accuracy verified", True), ("Responsive layout", True)],
        "review":         [("Performance budget met", True), ("Accessibility audit", False)],
        "validation":     [("QA sign-off", True), ("Browser regression", True)],
    },
    "widget": {
        "implementation": [("Widget renders with real data", True), ("Error state handled", True)],
        "validation":     [("End-to-end data flow verified", True)],
    },
    "watchlist": {
        "implementation": [("CRUD operations tested", True), ("Alerts fire within 30 s", True)],
        "validation":     [("No duplicate alerts", True), ("Push delivery confirmed", True)],
    },
    "analytics": {
        "implementation": [("Computation accuracy validated", True)],
        "validation":     [("Historical data unchanged", True), ("Query time < 500 ms", True)],
    },
    "ux": {
        "implementation": [("Design fidelity ≥ 95%", True), ("A11y: 0 critical violations", True)],
        "validation":     [("Cross-browser regression", True)],
    },
    "monetization": {
        "implementation": [("Stripe test mode checkout passes", True)],
        "review":         [("Payment security review passed", True)],
        "validation":     [("No free users affected", True), ("Revenue events firing", True)],
    },
}

_DEFAULT_CHECKS = {
    "implementation": [("Implementation complete", True)],
    "validation":     [("Acceptance criteria met", True)],
}


def run_validation(
    plan_id: str,
    run_id: str,
    phase: str,
    phase_number: int,
    task_type: str,
    work_item_id: str,
) -> ValidationCheckpoint:
    """Run all validation checks for the given phase and return a checkpoint."""
    type_checks = _CHECKS.get(task_type, _DEFAULT_CHECKS)
    checks      = type_checks.get(phase, [("Phase exit criteria met", True)])

    details: list[dict] = []
    passed_count  = 0
    failed_count  = 0
    blocking_fail = 0

    for check_text, blocking in checks:
        seed    = f"{work_item_id}_{phase}_{check_text[:20]}"
        success = _sim_success(seed, 0.94 if blocking else 0.97)

        details.append({
            "check":    check_text,
            "blocking": blocking,
            "passed":   success,
            "message":  "Pass" if success else f"FAIL: {check_text}",
        })
        if success:
            passed_count += 1
        else:
            failed_count += 1
            if blocking:
                blocking_fail += 1

    result = VALIDATION_PASSED if blocking_fail == 0 else VALIDATION_FAILED

    return ValidationCheckpoint(
        checkpoint_id    = f"ck_{plan_id}_{phase}",
        plan_id          = plan_id,
        run_id           = run_id,
        phase            = phase,
        phase_number     = phase_number,
        checks_run       = len(checks),
        checks_passed    = passed_count,
        checks_failed    = failed_count,
        blocking_failures= blocking_fail,
        result           = result,
        details          = details,
        duration_seconds = len(checks) * 0.2,
    )

"""
delivery_health.py — Delivery health scoring and health report generation.
"""

from __future__ import annotations

from typing import Any

from . import delivery_memory as mem
from .models import (
    DeliveryHealthReport, DeliveryRun,
    DELIVERY_COMPLETED, DELIVERY_FAILED,
    HEALTH_GOOD, HEALTH_CAUTION, HEALTH_CRITICAL,
    VALIDATION_PASSED,
)


def score_run(run: DeliveryRun) -> float:
    """Compute a 0-100 health score for a single delivery run."""
    score = 100.0
    total = max(run.total_steps, 1)

    # Failed steps: −3 each
    failed_steps = run.total_steps - run.completed_steps
    score -= failed_steps * (3.0 * total / max(total, 1))

    # Recovery actions: −8 each
    score -= len(run.recovery_actions) * 8.0

    # Validation failures: −10 if overall not passed
    if not run.validation_passed:
        score -= 10.0

    # Incomplete run: −20
    if run.status not in (DELIVERY_COMPLETED,):
        score -= 20.0

    return round(max(0.0, min(100.0, score)), 1)


def _health_label(score: float) -> str:
    if score >= 80:
        return HEALTH_GOOD
    if score >= 60:
        return HEALTH_CAUTION
    return HEALTH_CRITICAL


def compute_health_report(project: str = "all") -> DeliveryHealthReport:
    """Build a DeliveryHealthReport from stored runs."""
    all_runs = mem.list_runs()
    if project != "all":
        all_runs = [r for r in all_runs if r.get("project") == project]

    completed = [r for r in all_runs if r.get("status") == DELIVERY_COMPLETED]
    failed    = [r for r in all_runs if r.get("status") == DELIVERY_FAILED]
    active    = [r for r in all_runs if r.get("status") == "running"]

    scores = [r.get("health_score", 100.0) for r in all_runs]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 95.0

    # Phase completion rates from all runs
    phase_counts: dict[str, list[float]] = {}
    for r in all_runs:
        for ph in r.get("phases", []):
            name = ph.get("phase_name", "")
            total = ph.get("total_steps", 0)
            done  = ph.get("completed_steps", 0)
            rate  = (done / total * 100) if total else 100.0
            phase_counts.setdefault(name, []).append(rate)

    phase_rates = {
        ph: round(sum(rates) / len(rates), 1)
        for ph, rates in phase_counts.items()
    }

    # Validation pass rate
    all_cp   = mem.list_checkpoints()
    if project != "all":
        all_cp = [c for c in all_cp if c.get("plan_id", "").endswith(project.replace("yallaplays", "yp").replace("fionera", "fi"))]
    passed_cp   = sum(1 for c in all_cp if c.get("result") == VALIDATION_PASSED)
    val_rate    = round(passed_cp / len(all_cp) * 100, 1) if all_cp else 100.0

    # Recovery and rollback
    all_rec      = mem.list_recovery()
    rollback_rec = [r for r in all_rec if r.get("action") == "rollback"]
    rb_rate      = round(len(rollback_rec) / max(len(all_runs), 1) * 100, 1)

    # Blocked items (failed runs)
    blocked = [r.get("plan_id", "") for r in failed][:5]

    # Insights
    insights: list[str] = []
    if len(all_runs) == 0:
        insights.append("No delivery runs recorded yet. Execute plans to begin tracking.")
    else:
        if avg_score >= 90:
            insights.append(f"Delivery health excellent: avg score {avg_score}/100.")
        elif avg_score < 70:
            insights.append(f"Delivery health needs attention: avg score {avg_score}/100.")
        if len(failed) > 0:
            insights.append(f"{len(failed)} failed run(s) — review recovery logs.")
        if val_rate < 90:
            insights.append(f"Validation pass rate {val_rate}% — investigate failing checkpoints.")
        if rb_rate > 20:
            insights.append(f"High rollback rate {rb_rate}% — check risk gates.")
        if not insights:
            insights.append("All systems nominal. Delivery pipeline healthy.")

    return DeliveryHealthReport(
        report_id           = f"hr_{project}",
        project             = project,
        total_plans         = len(all_runs),
        total_runs          = len(all_runs),
        active_runs         = len(active),
        completed_runs      = len(completed),
        failed_runs         = len(failed),
        avg_health_score    = avg_score,
        overall_health      = _health_label(avg_score),
        phase_completion_rates = phase_rates,
        validation_pass_rate= val_rate,
        rollback_rate       = rb_rate,
        recovery_count      = len(all_rec),
        insights            = insights,
        top_blocked_items   = blocked,
    )

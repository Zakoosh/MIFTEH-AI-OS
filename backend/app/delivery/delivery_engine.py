"""
delivery_engine.py — Main orchestrator for the Delivery Execution Layer.

Converts ExecutionPlans (from the Planning Layer) into full DeliveryRuns,
executing phases, validation checkpoints, collaborative sessions, and
deployment previews — all in a controlled, auditable, rollback-aware manner.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import delivery_memory as mem
from .models import (
    DeliveryPlan, DeliveryRun,
    DELIVERY_COMPLETED, DELIVERY_FAILED, DELIVERY_PENDING,
    PHASE_ORDER, _sim_score, _now,
)
from .phase_executor import execute_phase
from .checkpoint_manager import get_checkpoint_manager
from .deployment_previews import generate as generate_preview
from .collaborative_delivery import create_session
from .recovery_manager import recover
from .delivery_health import score_run, compute_health_report
from .delivery_health import DeliveryHealthReport


class DeliveryEngine:
    """
    Orchestrates the full delivery pipeline for work items.
    Always dry_run=True by default — no live deployment.
    """

    def __init__(self) -> None:
        self._cm = get_checkpoint_manager()

    # ── Execute ───────────────────────────────────────────────────────────────

    def execute_plan(
        self,
        plan_id: str,
        dry_run: bool = True,
        triggered_by: str = "autonomous",
        force: bool = False,
    ) -> DeliveryRun:
        # Return cached run unless forced
        if not force:
            cached = mem.get_run_for_plan(plan_id)
            if cached:
                return DeliveryRun(**{
                    k: cached[k] for k in DeliveryRun.__dataclass_fields__
                    if k in cached
                })

        # Load ExecutionPlan from planning layer
        from app.planning.execution_planner import get_planner
        planner     = get_planner()
        all_plans   = planner.plan_all("all")
        exec_plan   = next((p for p in all_plans if p.plan_id == plan_id), None)

        if exec_plan is None:
            raise ValueError(f"Plan '{plan_id}' not found in planning layer")

        work_item_id = exec_plan.work_item_id
        run_id       = f"run_{plan_id}"

        # --- Deployment preview ---
        preview = generate_preview(exec_plan)
        mem.save_preview(preview.to_dict())

        # --- Collaborative delivery session ---
        mission = exec_plan.metadata.get("collaboration_mission", "feature-development")
        collab  = create_session(
            plan_id, work_item_id, exec_plan.project, mission, exec_plan.task_type
        )

        # --- Audit: run started ---
        mem.save_audit({
            "audit_id":  f"aud_{plan_id}_start",
            "plan_id":   plan_id,
            "run_id":    run_id,
            "action":    "run_started",
            "actor":     triggered_by,
            "status":    "running",
            "phase":     "",
            "details":   f"Delivery run initiated (dry_run={dry_run})",
            "timestamp": _now(),
        })

        # --- Phase execution ---
        # Group steps by phase and execute in canonical order
        steps_by_phase: dict[str, list[dict]] = {}
        for s in exec_plan.steps:
            ph = s.get("phase", "implementation")
            steps_by_phase.setdefault(ph, []).append(s)

        phases_to_run = [ph for ph in PHASE_ORDER if ph in steps_by_phase or ph in exec_plan.phases]

        executed_phases: list[dict]     = []
        checkpoints:     list[dict]     = []
        recovery_actions: list[dict]    = []
        phases_completed: list[str]     = []
        total_steps    = len(exec_plan.steps)
        completed_steps = 0
        overall_valid   = True
        final_phase     = ""

        for ph_num, phase_name in enumerate(phases_to_run, start=1):
            ph_steps = steps_by_phase.get(phase_name, [])
            if not ph_steps:
                continue

            final_phase = phase_name

            # Execute phase
            phase_result = execute_phase(
                phase_name, ph_steps, plan_id, run_id,
                exec_plan.task_type, ph_num,
            )

            # Validation checkpoint
            cp = self._cm.run_and_save(
                plan_id, run_id, phase_name, ph_num,
                exec_plan.task_type, work_item_id,
            )

            # Attach checkpoint to phase
            phase_result.validation_result = cp.to_dict()
            executed_phases.append(phase_result.to_dict())
            checkpoints.append(cp.to_dict())

            completed_steps += phase_result.completed_steps
            phases_completed.append(phase_name)

            # Recovery if checkpoint failed
            if not self._cm.passed(cp):
                rec = recover(plan_id, run_id, phase_name, "validation_failed")
                recovery_actions.append(rec.to_dict())
                mem.save_audit({
                    "audit_id":  f"aud_{plan_id}_{phase_name}_recovery",
                    "plan_id":   plan_id, "run_id": run_id,
                    "action":    "recovery",
                    "actor":     "delivery-engine",
                    "status":    "recovered" if rec.success else "failed",
                    "phase":     phase_name,
                    "details":   rec.action_details,
                    "timestamp": _now(),
                })
                if not rec.success:
                    overall_valid = False
                    break

            mem.save_audit({
                "audit_id":  f"aud_{plan_id}_{phase_name}_done",
                "plan_id":   plan_id, "run_id": run_id,
                "action":    "phase_completed",
                "actor":     "delivery-engine",
                "status":    "completed",
                "phase":     phase_name,
                "details":   f"{phase_result.completed_steps}/{phase_result.total_steps} steps passed",
                "timestamp": _now(),
            })

        phases_remaining = [
            ph for ph in PHASE_ORDER
            if ph in steps_by_phase and ph not in phases_completed
        ]

        run = DeliveryRun(
            run_id                     = run_id,
            plan_id                    = plan_id,
            work_item_id               = work_item_id,
            project                    = exec_plan.project,
            title                      = exec_plan.title,
            triggered_by               = triggered_by,
            dry_run                    = dry_run,
            simulated                  = True,
            current_phase              = final_phase,
            phases_completed           = phases_completed,
            phases_remaining           = phases_remaining,
            completed_steps            = completed_steps,
            total_steps                = total_steps,
            remaining_steps            = max(0, total_steps - completed_steps),
            validation_passed          = overall_valid,
            rollback_ready             = True,
            deployment_preview_generated = True,
            recovery_actions           = recovery_actions,
            phases                     = executed_phases,
            checkpoints                = checkpoints,
            collaborative_session_id   = collab.session_id,
            status                     = DELIVERY_COMPLETED if overall_valid else DELIVERY_FAILED,
            error                      = "" if overall_valid else "Recovery failed — see recovery_actions",
        )

        # Compute and attach health score
        run.health_score = score_run(run)

        mem.save_run(run.to_dict())
        mem.save_audit({
            "audit_id":  f"aud_{plan_id}_end",
            "plan_id":   plan_id, "run_id": run_id,
            "action":    "run_completed",
            "actor":     triggered_by,
            "status":    run.status,
            "phase":     final_phase,
            "details":   f"health_score={run.health_score}  validation_passed={overall_valid}",
            "timestamp": _now(),
        })

        return run

    # ── Plans ─────────────────────────────────────────────────────────────────

    def list_delivery_plans(self, project: str = "all") -> list[DeliveryPlan]:
        from app.planning.execution_planner import get_planner
        exec_plans = get_planner().plan_all(project)

        plans: list[DeliveryPlan] = []
        for ep in exec_plans:
            run = mem.get_run_for_plan(ep.plan_id)
            plans.append(DeliveryPlan(
                plan_id               = ep.plan_id,
                work_item_id          = ep.work_item_id,
                project               = ep.project,
                title                 = ep.title,
                description           = ep.description,
                task_type             = ep.task_type,
                priority              = ep.priority,
                phases                = ep.phases,
                total_steps           = len(ep.steps),
                total_estimated_hours = ep.estimated_hours,
                validation_required   = ep.validation_required,
                rollback_available    = True,
                dependencies          = ep.dependencies,
                source_quarter        = ep.source_quarter,
                latest_run_id         = run.get("run_id", "") if run else "",
                total_runs            = 1 if run else 0,
                status                = run.get("status", DELIVERY_PENDING) if run else DELIVERY_PENDING,
            ))
        return plans

    # ── Phase summary ──────────────────────────────────────────────────────────

    def get_phases_summary(self, project: str = "all") -> list[dict[str, Any]]:
        """Return phase execution summaries from stored runs."""
        all_runs = mem.list_runs()
        if project != "all":
            all_runs = [r for r in all_runs if r.get("project") == project]

        summaries: list[dict] = []
        for run in all_runs:
            for ph in run.get("phases", []):
                summaries.append({
                    "plan_id":        run.get("plan_id"),
                    "run_id":         run.get("run_id"),
                    "project":        run.get("project"),
                    "plan_title":     run.get("title"),
                    "phase_name":     ph.get("phase_name"),
                    "phase_number":   ph.get("phase_number"),
                    "status":         ph.get("status"),
                    "total_steps":    ph.get("total_steps"),
                    "completed_steps":ph.get("completed_steps"),
                    "failed_steps":   ph.get("failed_steps"),
                    "validation":     ph.get("validation_result", {}).get("result"),
                    "rollback_available": ph.get("rollback_available"),
                })
        return summaries

    # ── Health ────────────────────────────────────────────────────────────────

    def get_health(self, project: str = "all") -> DeliveryHealthReport:
        return compute_health_report(project)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        from app.planning.execution_planner import get_planner
        all_plans = get_planner().plan_all("all")
        all_runs  = mem.list_runs()
        health    = compute_health_report("all")

        return {
            "status":          "operational",
            "layer":           "Autonomous Delivery Execution Layer",
            "dashboard_route": "yallaplays.com/admin/os",
            "total_plans":     len(all_plans),
            "total_runs":      len(all_runs),
            "overall_health":  health.overall_health,
            "avg_health_score":health.avg_health_score,
            "projects_supported": ["yallaplays", "fionera"],
        }

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_analytics(self) -> dict[str, Any]:
        all_runs = mem.list_runs()
        health   = compute_health_report("all")

        by_project: dict[str, int] = {}
        by_status:  dict[str, int] = {}
        by_task_type: dict[str, int] = {}

        for r in all_runs:
            p  = r.get("project", "unknown")
            st = r.get("status",  "unknown")
            by_project[p]  = by_project.get(p, 0) + 1
            by_status[st]  = by_status.get(st, 0) + 1

        total_rec = len(mem.list_recovery())
        total_cp  = len(mem.list_checkpoints())

        return {
            "total_runs":            len(all_runs),
            "by_project":            by_project,
            "by_status":             by_status,
            "avg_health_score":      health.avg_health_score,
            "overall_health":        health.overall_health,
            "total_checkpoints":     total_cp,
            "validation_pass_rate":  health.validation_pass_rate,
            "total_recovery_actions":total_rec,
            "rollback_rate":         health.rollback_rate,
            "phase_completion_rates":health.phase_completion_rates,
            "insights":              health.insights,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: DeliveryEngine | None = None


def get_engine() -> DeliveryEngine:
    global _instance
    if _instance is None:
        _instance = DeliveryEngine()
    return _instance

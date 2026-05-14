"""
execution_planner.py — Orchestrates the full planning pipeline.

Converts WorkItems into ExecutionPlans, then generates dependency graphs,
milestones, rollout plans, validation sequences, effort estimates,
and delivery checkpoints.
"""

from __future__ import annotations

from typing import Any

from .models import ExecutionPlan, PlanningAnalytics
from .task_breakdown import bind_steps, has_validation_step, total_hours, step_count
from .dependency_graph import build_graph
from .milestone_builder import build_milestones, get_milestone_for_item
from .execution_sequences import compute_execution_order, phase_label_for
from .validation_steps import build_validation_sequence
from .rollout_plans import build_all_rollouts, build_rollout_plan
from .effort_estimator import estimate_all, total_effort_days
from .delivery_tracking import build_delivery_report


class ExecutionPlanner:
    """
    Main planning orchestrator.  All methods are stateless — inputs come from
    the Work Generation Layer and outputs are returned as plain objects.
    """

    # ── Single item ──────────────────────────────────────────────────────────

    def plan_work_item(self, item: Any) -> ExecutionPlan:
        plan_id   = f"plan_{item.item_id}"
        steps     = bind_steps(plan_id, item.item_id, item.task_type)
        total_h   = round(total_hours(item.task_type), 1)
        ms_ids    = get_milestone_for_item(item.item_id)
        val_req   = has_validation_step(item.task_type)

        phases_used = sorted({s.phase for s in steps})

        return ExecutionPlan(
            plan_id               = plan_id,
            work_item_id          = item.item_id,
            project               = item.project,
            task_type             = item.task_type,
            title                 = item.title,
            description           = item.description,
            steps                 = [s.to_dict() for s in steps],
            estimated_days        = item.estimated_days,
            estimated_hours       = total_h,
            phases                = phases_used,
            priority              = item.priority,
            dependencies          = list(item.dependencies or []),
            milestone_ids         = ms_ids,
            validation_required   = val_req,
            validation_sequence_id= f"vs_{item.item_id}",
            rollout_plan_id       = f"ro_{item.project}_q3_2026",
            tags                  = list(item.tags or []),
            source_quarter        = item.quarter,
            metadata              = {
                "collaboration_mission": item.collaboration_mission,
                "apply_proposal_type":  item.apply_proposal_type,
                "roi_estimate":         item.roi_estimate,
            },
        )

    # ── All items for a project ──────────────────────────────────────────────

    def plan_all(self, project: str = "all") -> list[ExecutionPlan]:
        items = self._load_items(project)
        return [self.plan_work_item(i) for i in items]

    # ── Dependency graph ─────────────────────────────────────────────────────

    def get_dependency_graph(self, project: str = "all"):
        items = self._load_items(project)
        return build_graph(items, project)

    # ── Milestones ───────────────────────────────────────────────────────────

    def get_milestones(self, project: str = "all"):
        items = self._load_items(project)
        return build_milestones(items, project)

    # ── Rollout plans ────────────────────────────────────────────────────────

    def get_rollout_plans(self, project: str = "all"):
        from app.workgen.yallaplays_workgen import get_yallaplays_work_items
        from app.workgen.fionera_workgen import get_fionera_work_items

        yp = get_yallaplays_work_items()
        fi = get_fionera_work_items()

        if project == "yallaplays":
            return [build_rollout_plan(yp, "yallaplays", "Q3-2026"),
                    build_rollout_plan(
                        [i for i in yp if i.quarter == "Q4-2026"],
                        "yallaplays", "Q4-2026",
                    )] if any(i.quarter == "Q4-2026" for i in yp) else \
                   [build_rollout_plan(yp, "yallaplays", "Q3-2026")]

        if project == "fionera":
            return [build_rollout_plan(fi, "fionera", "Q3-2026"),
                    build_rollout_plan(
                        [i for i in fi if i.quarter == "Q4-2026"],
                        "fionera", "Q4-2026",
                    )] if any(i.quarter == "Q4-2026" for i in fi) else \
                   [build_rollout_plan(fi, "fionera", "Q3-2026")]

        return build_all_rollouts(yp, fi)

    # ── Validation sequences ─────────────────────────────────────────────────

    def get_validation_sequences(self, project: str = "all"):
        items = self._load_items(project)
        seqs = []
        for item in items:
            plan_id = f"plan_{item.item_id}"
            seqs.append(build_validation_sequence(
                plan_id, item.item_id, item.project, item.task_type, item.title
            ))
        return seqs

    # ── Effort estimates ─────────────────────────────────────────────────────

    def get_effort_estimates(self, project: str = "all"):
        return estimate_all(self._load_items(project))

    # ── Delivery tracking ────────────────────────────────────────────────────

    def get_delivery_report(self, project: str = "all"):
        plans = self.plan_all(project)
        return build_delivery_report(project, plans)

    # ── Analytics ────────────────────────────────────────────────────────────

    def get_analytics(self) -> PlanningAnalytics:
        items    = self._load_items("all")
        plans    = [self.plan_work_item(i) for i in items]
        ms       = build_milestones(items)
        rollouts = self.get_rollout_plans()
        graph    = build_graph(items, "all")

        steps_total = sum(len(p.steps) for p in plans)
        avg_steps   = round(steps_total / len(plans), 1) if plans else 0.0

        by_project: dict[str, int] = {}
        by_type:    dict[str, int] = {}
        by_prio:    dict[str, int] = {}
        for i in items:
            by_project[i.project]   = by_project.get(i.project, 0) + 1
            by_type[i.task_type]    = by_type.get(i.task_type, 0) + 1
            by_prio[i.priority]     = by_prio.get(i.priority, 0) + 1

        top_effort = sorted(items, key=lambda i: i.estimated_days, reverse=True)[:5]

        return PlanningAnalytics(
            total_plans               = len(plans),
            total_milestones          = len(ms),
            total_rollouts            = len(rollouts),
            total_validation_sequences= len(plans),
            total_effort_days         = total_effort_days(items),
            avg_steps_per_plan        = avg_steps,
            by_project                = by_project,
            by_task_type              = by_type,
            by_priority               = by_prio,
            critical_path_items       = graph.critical_path,
            top_effort_items          = [i.item_id for i in top_effort],
        )

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        analytics = self.get_analytics()
        return {
            "status":  "operational",
            "layer":   "Autonomous Execution Planning Layer",
            "dashboard_route": "yallaplays.com/admin/os",
            "analytics": analytics.to_dict(),
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    @staticmethod
    def _load_items(project: str) -> list[Any]:
        from app.workgen.yallaplays_workgen import get_yallaplays_work_items
        from app.workgen.fionera_workgen import get_fionera_work_items

        if project == "yallaplays":
            return get_yallaplays_work_items()
        if project == "fionera":
            return get_fionera_work_items()
        return get_yallaplays_work_items() + get_fionera_work_items()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_instance: ExecutionPlanner | None = None


def get_planner() -> ExecutionPlanner:
    global _instance
    if _instance is None:
        _instance = ExecutionPlanner()
    return _instance

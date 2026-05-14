"""
rollout_plans.py — Generates phased rollout plans per project and quarter.
"""

from __future__ import annotations

from typing import Any

from .models import RolloutPlan
from .execution_sequences import group_items_into_bands


def build_rollout_plan(
    items: list[Any],
    project: str,
    quarter: str = "Q3-2026",
) -> RolloutPlan:
    rollout_id = f"ro_{project}_{quarter.replace('-', '_').lower()}"

    phases = group_items_into_bands(items, project, quarter, rollout_id)

    total_days = (
        max((p.start_offset_days + p.duration_days for p in phases), default=0)
    )

    return RolloutPlan(
        rollout_id       = rollout_id,
        project          = project,
        quarter          = quarter,
        title            = f"{project.title()} {quarter} Rollout Plan",
        description      = (
            f"Phased {len(phases)}-phase rollout for {len(items)} work items "
            f"across {project} in {quarter}."
        ),
        phases           = [p.to_dict() for p in phases],
        total_duration_days = total_days,
        work_item_ids    = [i.item_id for i in items],
        total_work_items = len(items),
    )


def build_all_rollouts(
    yp_items: list[Any],
    fi_items: list[Any],
) -> list[RolloutPlan]:
    plans: list[RolloutPlan] = []

    # Q3-2026
    q3_yp = [i for i in yp_items if i.quarter in ("Q3-2026", "")]
    q3_fi = [i for i in fi_items if i.quarter in ("Q3-2026", "")]
    if q3_yp:
        plans.append(build_rollout_plan(q3_yp, "yallaplays", "Q3-2026"))
    if q3_fi:
        plans.append(build_rollout_plan(q3_fi, "fionera", "Q3-2026"))

    # Q4-2026
    q4_yp = [i for i in yp_items if i.quarter == "Q4-2026"]
    q4_fi = [i for i in fi_items if i.quarter == "Q4-2026"]
    if q4_yp:
        plans.append(build_rollout_plan(q4_yp, "yallaplays", "Q4-2026"))
    if q4_fi:
        plans.append(build_rollout_plan(q4_fi, "fionera", "Q4-2026"))

    return plans

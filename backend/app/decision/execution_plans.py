from app.decision.models import ExecutionPlan, MissionDecision
from app.decision.strategy import effort_label
from app.missions.planner import resolve_mission


def _plan_id(project_id: str, mission_id: str) -> str:
    return f"{project_id}_{mission_id}_decision_plan"


def _expected_outputs(project_id: str, mission_id: str) -> list[str]:
    mission = resolve_mission(project_id, mission_id)
    if mission is None:
        return []

    return mission.get("expected_output", [])


def build_execution_plan(decision: MissionDecision) -> ExecutionPlan:
    automation_candidate = (
        not decision.blocked
        and decision.automation_readiness >= 70
        and decision.decision_score >= 65
    )

    steps = [
        "Review latest intelligence signals and project priorities",
        "Confirm workspace and git state before execution",
        "Run the recommended mission through the Mission Engine",
        "Save structured reports and update mission history",
        "Review generated recommendations before any code changes",
    ]

    if automation_candidate:
        steps.append("Consider interval scheduling after one successful manual run")
    else:
        steps.append("Keep execution manual until constraints and readiness improve")

    return ExecutionPlan(
        plan_id=_plan_id(decision.project_id, decision.mission_id),
        project_id=decision.project_id,
        mission_id=decision.mission_id,
        priority=decision.priority,
        recommended_agents=decision.recommended_agents,
        estimated_effort=effort_label(len(decision.recommended_agents)),
        estimated_impact=decision.impact_score,
        automation_candidate=automation_candidate,
        cooldown_minutes=60 if decision.priority in {"critical", "high"} else 180,
        steps=steps,
        expected_outputs=_expected_outputs(decision.project_id, decision.mission_id),
        constraints=decision.constraints,
    )


def build_execution_plans(decisions: list[MissionDecision]) -> list[ExecutionPlan]:
    return [build_execution_plan(decision) for decision in decisions]

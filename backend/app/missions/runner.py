from datetime import datetime

from app.missions.models import MissionRequest, MissionResult, AgentResult
from app.missions.planner import build_execution_plan
from app.missions.dispatcher import dispatch_agent
from app.missions.memory import save_mission_result, load_mission_result, list_mission_history
from app.reports.generator import generate_reports_from_mission


def execute_mission(request: MissionRequest) -> dict:
    plan = build_execution_plan(
        project_id=request.project_id,
        mission_id=request.mission_id,
        agent_limit=request.agent_limit,
    )

    if "error" in plan:
        return plan

    started_at = datetime.now().isoformat()

    agent_results: list[AgentResult] = []

    for agent in plan["agents"]:
        result = dispatch_agent(
            agent=agent,
            mission_title=plan["title"],
            mission_id=plan["mission_id"],
            project_name=plan["project_name"],
            goal=plan["goal"],
            expected_output=plan["expected_output"],
        )
        agent_results.append(result)

    completed_count = sum(1 for r in agent_results if r.status in ("completed", "offline_completed"))
    failed_count = sum(1 for r in agent_results if r.status == "failed")

    all_success = all(r.success for r in agent_results)
    status = "completed" if all_success else "completed_with_failures"

    mission_result = MissionResult(
        mission_id=plan["mission_id"],
        project_id=request.project_id,
        mission_title=plan["title"],
        status=status,
        agents_total=len(agent_results),
        agents_completed=completed_count,
        agents_failed=failed_count,
        agent_results=agent_results,
        started_at=started_at,
        completed_at=datetime.now().isoformat(),
    )

    execution_id = save_mission_result(mission_result)

    structured_reports = generate_reports_from_mission(
        agent_results=agent_results,
        mission_id=plan["mission_id"],
        project_id=request.project_id,
    )
    report_ids = [r.report_id for r in structured_reports]

    return {
        "execution_id": execution_id,
        "structured_report_ids": report_ids,
        **mission_result.model_dump(),
    }


def get_mission_execution(execution_id: str) -> dict:
    data = load_mission_result(execution_id)

    if data is None:
        return {"error": f"Mission execution '{execution_id}' not found"}

    return data


def get_mission_history() -> dict:
    summary = list_mission_history()
    return summary.model_dump()

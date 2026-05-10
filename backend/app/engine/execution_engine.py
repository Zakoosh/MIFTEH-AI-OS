from app.brain.agent_matcher import match_agents_for_project
from app.engine.prompt_builder import build_agent_prompt
from app.engine.agent_runner import run_agent
from app.engine.memory_engine import save_agent_report


def execute_single_agent(project_id: str):

    matched = match_agents_for_project(project_id)

    if "error" in matched:
        return matched

    first_agent = matched["matched_agents"][0]

    prompt_data = build_agent_prompt(project_id, first_agent)

    result = run_agent(prompt_data["prompt"])

    saved = save_agent_report(
        project_id,
        first_agent["name"],
        result
    )

    return {
        "status": "completed" if result["success"] else "offline_completed",
        "project": matched["project"],
        "agent": first_agent["name"],
        "division": first_agent["division"],
        "mode": result["mode"],
        "saved_report": saved
    }


def execute_all_project_agents(project_id: str, limit: int = 3):

    matched = match_agents_for_project(project_id)

    if "error" in matched:
        return matched

    results = []

    selected_agents = matched["matched_agents"][:limit]

    for agent in selected_agents:
        prompt_data = build_agent_prompt(project_id, agent)
        result = run_agent(prompt_data["prompt"])

        saved = save_agent_report(
            project_id,
            agent["name"],
            result
        )

        results.append({
            "agent": agent["name"],
            "division": agent["division"],
            "mode": result["mode"],
            "success": result["success"],
            "report_file": f"{project_id}_{agent['name']}.json"
        })

    return {
        "status": "completed",
        "project": matched["project"],
        "project_id": project_id,
        "executed_agents": len(results),
        "results": results
    }

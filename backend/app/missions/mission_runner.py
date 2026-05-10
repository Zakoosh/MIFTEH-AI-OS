from app.missions.mission_registry import get_project_missions
from app.engine.agent_loader import load_agent_file
from app.brain.context_builder import build_project_context
from app.engine.agent_runner import run_agent
from app.engine.memory_engine import save_agent_report


def get_mission(project_id: str, mission_id: str):
    missions_data = get_project_missions(project_id)

    if "error" in missions_data:
        return missions_data

    for mission in missions_data["active_missions"]:
        if mission["id"] == mission_id:
            return mission

    return {
        "error": "Mission not found"
    }


def build_mission_prompt(project_id: str, mission: dict, agent_path: str):
    agent = load_agent_file(agent_path)
    context = build_project_context(project_id)

    if "error" in agent:
        return agent

    return f'''
You are running inside MIFTEH AI OS.

=== ORIGINAL AGENCY AGENT ===
{agent["content"]}

=== PROJECT CONTEXT ===
{context}

=== MISSION ===
Mission ID: {mission["id"]}
Mission Title: {mission["title"]}

Expected Output:
{mission["output"]}

Your job:
- Work only within this mission
- Produce practical actions for the project
- Give exact files likely to change
- Give implementation-ready tasks
- Do not be generic
- Think like an autonomous project improvement agent
'''


def run_project_mission(project_id: str, mission_id: str):
    mission = get_mission(project_id, mission_id)

    if "error" in mission:
        return mission

    results = []

    for agent_path in mission["agents"]:
        prompt = build_mission_prompt(project_id, mission, agent_path)

        result = run_agent(prompt)

        agent_name = agent_path.split("/")[-1].replace(".md", "")

        saved = save_agent_report(
            project_id,
            f"{mission_id}_{agent_name}",
            result
        )

        results.append({
            "mission_id": mission_id,
            "agent": agent_name,
            "agent_path": agent_path,
            "mode": result["mode"],
            "success": result["success"],
            "report_file": saved["file"]
        })

    return {
        "status": "mission_completed",
        "project_id": project_id,
        "mission_id": mission_id,
        "mission_title": mission["title"],
        "agents_executed": len(results),
        "results": results
    }

from typing import Optional

from app.missions.mission_registry import MISSIONS
from app.agents.registry import get_agent, list_registered_agents
from app.agents.models import AgentMetadata


def resolve_mission(project_id: str, mission_id: str) -> Optional[dict]:
    project_data = MISSIONS.get(project_id)
    if project_data is None:
        return None

    for mission in project_data.get("active_missions", []):
        if mission["id"] == mission_id:
            return {
                "project_id": project_id,
                "project_name": project_data["project"],
                "goal": project_data["goal"],
                "mission_id": mission["id"],
                "title": mission["title"],
                "agent_paths": mission["agents"],
                "expected_output": mission["output"],
            }

    return None


def list_available_missions() -> list[dict]:
    result = []
    for project_id, project_data in MISSIONS.items():
        for mission in project_data.get("active_missions", []):
            result.append({
                "project_id": project_id,
                "project_name": project_data["project"],
                "mission_id": mission["id"],
                "title": mission["title"],
                "agent_count": len(mission["agents"]),
            })
    return result


def match_agents_for_mission(agent_paths: list[str]) -> list[AgentMetadata]:
    matched: list[AgentMetadata] = []

    for agent_path in agent_paths:
        agent_name = agent_path.split("/")[-1].replace(".md", "")
        metadata = get_agent(agent_name)

        if metadata is not None:
            matched.append(metadata)
        else:
            matched.append(AgentMetadata(
                name=agent_name,
                role="Unknown",
                source_path=agent_path,
            ))

    return matched


def build_execution_plan(project_id: str, mission_id: str, agent_limit: int = 0) -> dict:
    mission = resolve_mission(project_id, mission_id)

    if mission is None:
        return {"error": f"Mission '{mission_id}' not found for project '{project_id}'"}

    agents = match_agents_for_mission(mission["agent_paths"])

    if agent_limit > 0:
        agents = agents[:agent_limit]

    return {
        "project_id": project_id,
        "project_name": mission["project_name"],
        "mission_id": mission_id,
        "title": mission["title"],
        "goal": mission["goal"],
        "expected_output": mission["expected_output"],
        "agents": agents,
        "agent_count": len(agents),
    }

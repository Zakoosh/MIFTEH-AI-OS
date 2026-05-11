from app.projects.schemas import get_preferred_agents
from app.agents.registry import find_agents_by_project_type, list_registered_agents
from app.agents.models import AgentMetadata
from app.missions.mission_registry import MISSIONS


def map_agents_for_project(project_id: str, project_type: str) -> list[str]:
    preferred_names = get_preferred_agents(project_type)

    registry_agents = find_agents_by_project_type(project_type)
    registry_names = {a.name for a in registry_agents}

    matched: list[str] = []

    for name in preferred_names:
        if name in registry_names:
            matched.append(name)

    for agent in registry_agents:
        if agent.name not in matched:
            matched.append(agent.name)

    return matched


def map_missions_for_project(project_id: str) -> list[str]:
    project_data = MISSIONS.get(project_id)
    if project_data is None:
        return []

    return [
        mission["id"]
        for mission in project_data.get("active_missions", [])
    ]


def get_project_agents_detail(project_id: str, project_type: str) -> list[dict]:
    agent_names = map_agents_for_project(project_id, project_type)

    from app.agents.registry import get_agent

    details: list[dict] = []
    for name in agent_names:
        metadata = get_agent(name)
        if metadata is not None:
            details.append(metadata.model_dump())
        else:
            details.append({"name": name, "status": "not_in_registry"})

    return details


def get_project_missions_detail(project_id: str) -> list[dict]:
    project_data = MISSIONS.get(project_id)
    if project_data is None:
        return []

    return [
        {
            "mission_id": mission["id"],
            "title": mission["title"],
            "agent_count": len(mission["agents"]),
            "expected_output": mission["output"],
        }
        for mission in project_data.get("active_missions", [])
    ]

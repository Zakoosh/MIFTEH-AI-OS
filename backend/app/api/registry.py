from fastapi import APIRouter, Query
from typing import Optional

from app.agents.registry import (
    list_registered_agents,
    get_agent,
    get_agent_with_content,
    find_agents_by_division,
    find_agents_by_project_type,
    refresh_registry,
    registry_status,
)

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/agents")
def list_agents():
    return list_registered_agents()


@router.get("/agents/status")
def get_status():
    return registry_status()


@router.get("/agents/refresh")
def refresh():
    return refresh_registry()


@router.get("/agents/by-division")
def agents_by_division(division: str = Query(...)):
    agents = find_agents_by_division(division)
    return {
        "division": division,
        "count": len(agents),
        "agents": [a.model_dump() for a in agents],
    }


@router.get("/agents/by-project-type")
def agents_by_project_type(project_type: str = Query(...)):
    agents = find_agents_by_project_type(project_type)
    return {
        "project_type": project_type,
        "count": len(agents),
        "agents": [a.model_dump() for a in agents],
    }


@router.get("/agents/{agent_name}")
def get_single_agent(agent_name: str, include_content: Optional[bool] = Query(False)):
    if include_content:
        entry = get_agent_with_content(agent_name)
        return entry.model_dump()

    metadata = get_agent(agent_name)
    if metadata is None:
        return {"error": f"Agent '{agent_name}' not found in registry"}
    return metadata.model_dump()

from typing import Optional

from app.agents.models import AgentMetadata, AgentRegistryEntry, AgentRegistrySummary
from app.agents.agency_bridge import discover_agents, read_agent_file, get_agency_path, agency_available


_registry: dict[str, AgentMetadata] = {}


def refresh_registry() -> AgentRegistrySummary:
    _registry.clear()

    agents = discover_agents()

    for agent in agents:
        _registry[agent.name] = agent

    return build_summary()


def build_summary() -> AgentRegistrySummary:
    agents = list(_registry.values())

    divisions: dict[str, int] = {}
    for agent in agents:
        divisions[agent.division] = divisions.get(agent.division, 0) + 1

    return AgentRegistrySummary(
        total_agents=len(agents),
        divisions=divisions,
        agents=agents,
        source=str(get_agency_path()),
    )


def list_registered_agents() -> AgentRegistrySummary:
    if not _registry:
        return refresh_registry()
    return build_summary()


def get_agent(name: str) -> Optional[AgentMetadata]:
    if not _registry:
        refresh_registry()
    return _registry.get(name)


def get_agent_with_content(name: str) -> AgentRegistryEntry:
    metadata = get_agent(name)

    if metadata is None:
        return AgentRegistryEntry(
            agent=AgentMetadata(name=name),
            loaded=False,
            error=f"Agent '{name}' not found in registry",
        )

    content = read_agent_file(metadata.source_path)

    if content is None:
        return AgentRegistryEntry(
            agent=metadata,
            loaded=False,
            error=f"Could not read agent file: {metadata.source_path}",
        )

    return AgentRegistryEntry(
        agent=metadata,
        content=content,
        loaded=True,
    )


def find_agents_by_division(division: str) -> list[AgentMetadata]:
    if not _registry:
        refresh_registry()
    return [a for a in _registry.values() if a.division == division]


def find_agents_by_project_type(project_type: str) -> list[AgentMetadata]:
    if not _registry:
        refresh_registry()
    return [a for a in _registry.values() if project_type in a.project_compatibility]


def registry_status() -> dict:
    return {
        "available": agency_available(),
        "source": str(get_agency_path()),
        "registered_count": len(_registry),
    }

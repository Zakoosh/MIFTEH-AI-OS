from pathlib import Path

AGENCY_AGENTS_PATH = Path(r"D:\Projects\agency-agents-main")

ALLOWED_AGENT_EXTENSIONS = {
    ".md"
}


def list_agency_agents():
    agents = []

    if not AGENCY_AGENTS_PATH.exists():
        return {
            "error": "agency-agents-main folder not found",
            "path": str(AGENCY_AGENTS_PATH)
        }

    for file in AGENCY_AGENTS_PATH.rglob("*"):
        if not file.is_file():
            continue

        if file.suffix not in ALLOWED_AGENT_EXTENSIONS:
            continue

        relative_path = file.relative_to(AGENCY_AGENTS_PATH)
        parts = relative_path.parts

        if len(parts) < 2:
            continue

        division = parts[0]

        agents.append({
            "name": file.stem,
            "division": division,
            "path": str(relative_path).replace("\\", "/"),
            "size": file.stat().st_size
        })

    divisions = {}

    for agent in agents:
        division = agent["division"]
        divisions[division] = divisions.get(division, 0) + 1

    return {
        "source": str(AGENCY_AGENTS_PATH),
        "total_agents": len(agents),
        "divisions": divisions,
        "agents": agents
    }


def load_agency_agent(agent_path: str):
    full_path = AGENCY_AGENTS_PATH / agent_path

    if not full_path.exists():
        return {
            "error": "Agent not found",
            "agent_path": agent_path
        }

    content = full_path.read_text(encoding="utf-8", errors="ignore")

    return {
        "agent_path": agent_path,
        "content": content
    }

import os
from pathlib import Path
from typing import Optional

from app.agents.models import AgentMetadata
from app.agents.loader import load_agent_metadata, ALLOWED_EXTENSIONS

_DEFAULT_AGENCY_PATH = Path(__file__).resolve().parent.parent.parent.parent / "agency-agents-main"

AGENCY_PATH: Path = Path(os.environ.get("AGENCY_AGENTS_PATH", str(_DEFAULT_AGENCY_PATH)))


def get_agency_path() -> Path:
    return AGENCY_PATH


def agency_available() -> bool:
    return AGENCY_PATH.is_dir()


def discover_agents() -> list[AgentMetadata]:
    if not agency_available():
        return []

    agents: list[AgentMetadata] = []

    for file_path in AGENCY_PATH.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix not in ALLOWED_EXTENSIONS:
            continue

        metadata = load_agent_metadata(file_path, AGENCY_PATH)
        if metadata is not None:
            agents.append(metadata)

    return agents


def read_agent_file(agent_source_path: str) -> Optional[str]:
    full_path = AGENCY_PATH / agent_source_path

    if not full_path.is_file():
        return None

    try:
        return full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

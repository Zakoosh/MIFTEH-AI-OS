from pydantic import BaseModel, Field
from typing import Optional


class AgentMetadata(BaseModel):
    name: str
    role: str = ""
    division: str = ""
    capabilities: list[str] = Field(default_factory=list)
    project_compatibility: list[str] = Field(default_factory=list)
    source_path: str = ""
    file_size: int = 0


class AgentRegistryEntry(BaseModel):
    agent: AgentMetadata
    content: Optional[str] = None
    loaded: bool = False
    error: Optional[str] = None


class AgentRegistrySummary(BaseModel):
    total_agents: int = 0
    divisions: dict[str, int] = Field(default_factory=dict)
    agents: list[AgentMetadata] = Field(default_factory=list)
    source: str = ""

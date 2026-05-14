from pathlib import Path
from typing import Optional

from app.agents.models import AgentMetadata, AgentRegistryEntry

ALLOWED_EXTENSIONS = {".md"}

ROLE_KEYWORDS = {
    "designer": "Design",
    "developer": "Engineering",
    "architect": "Architecture",
    "manager": "Management",
    "analyst": "Analysis",
    "researcher": "Research",
    "engineer": "Engineering",
    "reviewer": "Review",
    "specialist": "Specialist",
    "creator": "Content",
    "hacker": "Growth",
    "reporter": "Reporting",
    "optimizer": "Optimization",
    "benchmarker": "Testing",
    "checker": "Testing",
    "orchestrator": "Orchestration",
    "injector": "Design",
    "producer": "Management",
}

PROJECT_TYPE_DIVISION_MAP = {
    "game-development": ["game-platform"],
    "finance": ["investment-platform"],
    "engineering": ["game-platform", "investment-platform"],
    "design": ["game-platform", "investment-platform"],
    "marketing": ["game-platform", "investment-platform"],
    "product": ["game-platform", "investment-platform"],
    "testing": ["game-platform", "investment-platform"],
    "support": ["game-platform", "investment-platform"],
    "specialized": ["game-platform", "investment-platform"],
}


def _infer_role(agent_name: str) -> str:
    name_lower = agent_name.lower()
    for keyword, role in ROLE_KEYWORDS.items():
        if keyword in name_lower:
            return role
    return "General"


def _infer_capabilities(agent_name: str, division: str) -> list[str]:
    capabilities = [division]
    name_lower = agent_name.lower()

    capability_keywords = {
        "frontend": "frontend-development",
        "backend": "backend-development",
        "security": "security-analysis",
        "performance": "performance-optimization",
        "seo": "seo-optimization",
        "growth": "growth-strategy",
        "content": "content-creation",
        "game": "game-development",
        "level": "level-design",
        "narrative": "narrative-design",
        "finance": "financial-analysis",
        "investment": "investment-research",
        "fpa": "financial-planning",
        "analytics": "data-analytics",
        "ux": "ux-design",
        "ui": "ui-design",
        "code-review": "code-review",
        "orchestrat": "agent-orchestration",
        "whimsy": "creative-design",
    }

    for keyword, capability in capability_keywords.items():
        if keyword in name_lower:
            capabilities.append(capability)

    return capabilities


def _infer_project_compatibility(division: str) -> list[str]:
    return PROJECT_TYPE_DIVISION_MAP.get(division, [])


def load_agent_metadata(file_path: Path, base_path: Path) -> Optional[AgentMetadata]:
    if not file_path.is_file():
        return None

    if file_path.suffix not in ALLOWED_EXTENSIONS:
        return None

    try:
        relative = file_path.relative_to(base_path)
    except ValueError:
        return None

    parts = relative.parts
    if len(parts) < 2:
        return None

    division = parts[0]
    name = file_path.stem

    return AgentMetadata(
        name=name,
        role=_infer_role(name),
        division=division,
        capabilities=_infer_capabilities(name, division),
        project_compatibility=_infer_project_compatibility(division),
        source_path=str(relative).replace("\\", "/"),
        file_size=file_path.stat().st_size,
    )


def load_agent_content(file_path: Path) -> AgentRegistryEntry:
    if not file_path.is_file():
        return AgentRegistryEntry(
            agent=AgentMetadata(name="unknown"),
            loaded=False,
            error=f"File not found: {file_path}",
        )

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        name = file_path.stem

        return AgentRegistryEntry(
            agent=AgentMetadata(name=name),
            content=content,
            loaded=True,
        )
    except Exception as exc:
        return AgentRegistryEntry(
            agent=AgentMetadata(name=file_path.stem),
            loaded=False,
            error=str(exc),
        )

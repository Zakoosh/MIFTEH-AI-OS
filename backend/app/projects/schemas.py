PROJECT_TYPES = {
    "ai-platform",
    "game-platform",
    "investment-platform",
    "agent-library",
}

PROJECT_AGENT_RULES: dict[str, list[str]] = {
    "ai-platform": [
        "product-manager",
        "engineering-frontend-developer",
        "engineering-backend-architect",
        "design-ui-designer",
        "design-ux-architect",
        "support-analytics-reporter",
        "testing-performance-benchmarker",
        "testing-reality-checker",
        "agents-orchestrator",
    ],
    "game-platform": [
        "game-designer",
        "level-designer",
        "narrative-designer",
        "engineering-frontend-developer",
        "engineering-code-reviewer",
        "marketing-seo-specialist",
        "marketing-growth-hacker",
        "marketing-content-creator",
        "testing-performance-benchmarker",
        "testing-reality-checker",
    ],
    "investment-platform": [
        "finance-investment-researcher",
        "finance-financial-analyst",
        "finance-fpa-analyst",
        "product-manager",
        "engineering-frontend-developer",
        "engineering-backend-architect",
        "engineering-security-engineer",
        "engineering-code-reviewer",
        "testing-performance-benchmarker",
        "support-analytics-reporter",
    ],
    "agent-library": [
        "agents-orchestrator",
        "product-manager",
        "engineering-code-reviewer",
    ],
}

DEFAULT_PROJECTS: dict[str, dict] = {
    "mifteh": {
        "name": "MIFTEH-AI-OS",
        "directory": "MIFTEH-AI-OS",
        "type": "ai-platform",
    },
    "agency-agents": {
        "name": "agency-agents-main",
        "directory": "agency-agents-main",
        "type": "agent-library",
    },
    "yallaplays": {
        "name": "YallaPlays",
        "directory": "YallaPlays",
        "type": "game-platform",
    },
    "fionera": {
        "name": "Fionera",
        "directory": "Fionera",
        "type": "investment-platform",
    },
}


def get_preferred_agents(project_type: str) -> list[str]:
    return PROJECT_AGENT_RULES.get(project_type, [])


def is_valid_project_type(project_type: str) -> bool:
    return project_type in PROJECT_TYPES

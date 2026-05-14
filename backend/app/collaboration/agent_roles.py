"""
agent_roles.py — Agent role classification and capability mapping.

Enforces the structural separation:
  Implementers  ≠ Reviewers ≠ Validators

Role assignment is derived from the agent's naming pattern, then
verified against the session roster to prevent role cross-contamination.
"""

from __future__ import annotations

from .models import AgentRole, ROLE_IMPLEMENTER, ROLE_REVIEWER, ROLE_VALIDATOR, ROLE_ORCHESTRATOR, ROLE_QA


# ---------------------------------------------------------------------------
# Mission definitions — agent rosters per collaboration type
# ---------------------------------------------------------------------------

COLLABORATION_MISSIONS: dict[str, dict] = {
    "seo-growth": {
        "description": "SEO growth and visibility improvement for game platforms",
        "project_type": "game-platform",
        "implementers": ["marketing-seo-specialist", "engineering-frontend-developer"],
        "reviewers":    ["engineering-code-reviewer"],
        "validators":   ["testing-performance-benchmarker"],
        "orchestrator": None,
    },
    "dashboard-improvement": {
        "description": "Investment dashboard analytics and UX improvement",
        "project_type": "investment-platform",
        "implementers": ["engineering-frontend-developer"],
        "reviewers":    ["product-manager", "engineering-code-reviewer"],
        "validators":   ["testing-performance-benchmarker"],
        "orchestrator": None,
    },
    "category-optimization": {
        "description": "Game category structure and discoverability optimization",
        "project_type": "game-platform",
        "implementers": ["marketing-seo-specialist", "marketing-growth-hacker"],
        "reviewers":    ["product-manager"],
        "validators":   ["testing-reality-checker", "testing-performance-benchmarker"],
        "orchestrator": None,
    },
    "security-review": {
        "description": "Security audit and code quality review",
        "project_type": "investment-platform",
        "implementers": ["engineering-backend-architect"],
        "reviewers":    ["engineering-code-reviewer"],
        "validators":   ["engineering-security-engineer", "testing-reality-checker"],
        "orchestrator": None,
    },
    "landing-page-update": {
        "description": "Landing page content and conversion optimization",
        "project_type": "game-platform",
        "implementers": ["engineering-frontend-developer", "marketing-seo-specialist"],
        "reviewers":    ["marketing-growth-hacker"],
        "validators":   ["testing-performance-benchmarker"],
        "orchestrator": None,
    },
    "portfolio-analytics": {
        "description": "Portfolio analytics and investment performance tracking",
        "project_type": "investment-platform",
        "implementers": ["finance-investment-researcher", "engineering-frontend-developer"],
        "reviewers":    ["finance-financial-analyst"],
        "validators":   ["testing-performance-benchmarker", "testing-reality-checker"],
        "orchestrator": None,
    },
    "watchlist-feature": {
        "description": "Watchlist configuration and alert system",
        "project_type": "investment-platform",
        "implementers": ["engineering-frontend-developer", "finance-fpa-analyst"],
        "reviewers":    ["product-manager", "engineering-code-reviewer"],
        "validators":   ["testing-performance-benchmarker"],
        "orchestrator": None,
    },
    "manifest-optimization": {
        "description": "PWA manifest and progressive web app optimization",
        "project_type": "game-platform",
        "implementers": ["engineering-frontend-developer"],
        "reviewers":    ["marketing-seo-specialist"],
        "validators":   ["testing-performance-benchmarker"],
        "orchestrator": None,
    },
    "metadata-update": {
        "description": "Page metadata, schema markup, and structured data",
        "project_type": "any",
        "implementers": ["marketing-seo-specialist", "engineering-frontend-developer"],
        "reviewers":    ["engineering-code-reviewer"],
        "validators":   ["testing-reality-checker"],
        "orchestrator": None,
    },
    "widget-development": {
        "description": "Analytics widget development and integration",
        "project_type": "investment-platform",
        "implementers": ["engineering-frontend-developer", "finance-financial-analyst"],
        "reviewers":    ["product-manager"],
        "validators":   ["testing-performance-benchmarker", "engineering-code-reviewer"],
        "orchestrator": None,
    },
    "growth-campaign": {
        "description": "Growth marketing campaign planning and execution",
        "project_type": "game-platform",
        "implementers": ["marketing-growth-hacker", "marketing-seo-specialist"],
        "reviewers":    ["marketing-app-store-optimizer"],
        "validators":   ["testing-reality-checker"],
        "orchestrator": None,
    },
    "financial-reporting": {
        "description": "Financial reporting and analytics improvement",
        "project_type": "investment-platform",
        "implementers": ["finance-fpa-analyst", "support-analytics-reporter"],
        "reviewers":    ["finance-financial-analyst"],
        "validators":   ["testing-reality-checker"],
        "orchestrator": None,
    },
}

# Fallback mission for unrecognized names
_DEFAULT_MISSION = {
    "description": "General collaborative review",
    "project_type": "any",
    "implementers": ["engineering-frontend-developer"],
    "reviewers":    ["engineering-code-reviewer"],
    "validators":   ["testing-performance-benchmarker"],
    "orchestrator": None,
}

# ---------------------------------------------------------------------------
# Role classification from agent name
# ---------------------------------------------------------------------------

# Suffix/prefix patterns → role mapping (checked in order)
_ROLE_PATTERNS: list[tuple[str, str]] = [
    ("orchestrator",          ROLE_ORCHESTRATOR),
    ("code-reviewer",         ROLE_REVIEWER),
    ("security-engineer",     ROLE_VALIDATOR),
    ("reality-checker",       ROLE_VALIDATOR),
    ("performance-benchmarker", ROLE_QA),
    ("product-manager",       ROLE_REVIEWER),
    ("studio-producer",       ROLE_REVIEWER),
    ("fpa-analyst",           ROLE_REVIEWER),
]

# Agent capabilities by division
_DIVISION_CAPABILITIES: dict[str, list[str]] = {
    "marketing": ["seo", "growth", "content", "campaigns", "app-store-optimization"],
    "engineering": ["code", "architecture", "frontend", "backend", "security", "review"],
    "finance": ["investment-analysis", "financial-modeling", "risk-assessment", "reporting"],
    "testing": ["performance", "quality-assurance", "reality-checking", "benchmarking"],
    "product": ["product-strategy", "roadmap", "stakeholder-management", "prioritization"],
    "design": ["ui", "ux", "visual-design", "prototyping"],
    "support": ["analytics", "reporting", "customer-insights"],
    "game": ["game-design", "level-design", "narrative", "mechanics"],
    "specialized": ["orchestration", "coordination", "meta-analysis"],
    "project-management": ["planning", "delivery", "team-coordination"],
}


def classify_agent_role(agent_name: str) -> str:
    """Determine the collaboration role from the agent's name."""
    lower = agent_name.lower()
    for pattern, role in _ROLE_PATTERNS:
        if pattern in lower:
            return role
    return ROLE_IMPLEMENTER


def parse_agent_division(agent_name: str) -> tuple[str, str]:
    """Return (division, specialty) from an agent name like 'marketing-seo-specialist'."""
    parts = agent_name.split("-", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return agent_name, agent_name


def build_agent_role(agent_name: str, override_role: str = "") -> AgentRole:
    """Construct a full AgentRole for an agent."""
    division, specialty = parse_agent_division(agent_name)
    role = override_role if override_role else classify_agent_role(agent_name)
    capabilities = _DIVISION_CAPABILITIES.get(division, ["general"])
    return AgentRole(
        agent_name=agent_name,
        role=role,
        division=division,
        specialty=specialty,
        capabilities=capabilities,
    )


def build_role_map(
    implementers: list[str],
    reviewers: list[str],
    validators: list[str],
    orchestrator: str | None = None,
) -> dict[str, str]:
    """Build a flat agent_name → role mapping, enforcing separation."""
    mapping: dict[str, str] = {}
    for a in implementers:
        mapping[a] = ROLE_IMPLEMENTER
    for a in reviewers:
        if a not in mapping:                    # reviewer cannot also be implementer
            mapping[a] = ROLE_REVIEWER
    for a in validators:
        if a not in mapping:                    # validator cannot be implementer or reviewer
            mapping[a] = ROLE_VALIDATOR
    if orchestrator and orchestrator not in mapping:
        mapping[orchestrator] = ROLE_ORCHESTRATOR
    return mapping


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_mission(mission_name: str) -> dict:
    """Return the mission definition, falling back to the default."""
    return COLLABORATION_MISSIONS.get(mission_name.lower(), _DEFAULT_MISSION)


def get_all_missions() -> dict[str, dict]:
    return COLLABORATION_MISSIONS


def list_mission_names() -> list[str]:
    return sorted(COLLABORATION_MISSIONS.keys())


def get_agents_for_mission(mission_name: str) -> dict[str, list[str]]:
    """Return {implementers, reviewers, validators} for a mission."""
    m = get_mission(mission_name)
    return {
        "implementers": m.get("implementers", []),
        "reviewers":    m.get("reviewers", []),
        "validators":   m.get("validators", []),
        "orchestrator": [m["orchestrator"]] if m.get("orchestrator") else [],
    }


def get_all_agents_for_mission(mission_name: str) -> list[str]:
    """Flat list of all agents (all roles) for a mission."""
    m = get_mission(mission_name)
    agents: list[str] = []
    agents.extend(m.get("implementers", []))
    agents.extend(m.get("reviewers", []))
    agents.extend(m.get("validators", []))
    if m.get("orchestrator"):
        agents.append(m["orchestrator"])
    return agents

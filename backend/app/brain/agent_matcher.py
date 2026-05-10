from app.core.projects import PROJECTS
from app.services.agency_indexer import list_agency_agents


PROJECT_AGENT_RULES = {
    "game-platform": [
        "game-designer",
        "level-designer",
        "narrative-designer",
        "technical-artist",
        "engineering-frontend-developer",
        "engineering-code-reviewer",
        "engineering-software-architect",
        "marketing-seo-specialist",
        "marketing-growth-hacker",
        "marketing-app-store-optimizer",
        "testing-performance-benchmarker",
        "testing-reality-checker",
        "project-management-studio-producer"
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
        "testing-reality-checker",
        "support-analytics-reporter",
        "marketing-growth-hacker"
    ]
}


def match_agents_for_project(project_id: str):

    if project_id not in PROJECTS:
        return {
            "error": "Project not found"
        }

    project = PROJECTS[project_id]
    project_type = project["type"]

    agency_data = list_agency_agents()

    if "error" in agency_data:
        return agency_data

    all_agents = agency_data["agents"]
    preferred_names = PROJECT_AGENT_RULES.get(project_type, [])

    matched_agents = []

    for preferred_name in preferred_names:
        for agent in all_agents:
            if agent["name"] == preferred_name:
                matched_agents.append(agent)

    return {
        "project": project["name"],
        "project_id": project_id,
        "type": project_type,
        "matched_agents_count": len(matched_agents),
        "matched_agents": matched_agents,
        "workflow": [
            {
                "step": 1,
                "name": "Discovery",
                "agents": matched_agents[:3]
            },
            {
                "step": 2,
                "name": "Architecture",
                "agents": matched_agents[3:6]
            },
            {
                "step": 3,
                "name": "Build Review",
                "agents": matched_agents[6:9]
            },
            {
                "step": 4,
                "name": "Growth & QA",
                "agents": matched_agents[9:]
            }
        ]
    }

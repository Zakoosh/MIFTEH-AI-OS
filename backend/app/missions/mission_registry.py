MISSIONS = {
    "mifteh": {
        "project": "MIFTEH AI OS",
        "goal": "Build, monitor, and continuously improve the central AI operating dashboard.",
        "active_missions": [
            {
                "id": "build-dashboard",
                "title": "Build MIFTEH AI OS monitoring dashboard",
                "agents": [
                    "product/product-manager.md",
                    "design/design-ui-designer.md",
                    "design/design-ux-architect.md",
                    "engineering/engineering-frontend-developer.md",
                    "support/support-analytics-reporter.md",
                    "specialized/agents-orchestrator.md"
                ],
                "output": [
                    "dashboard structure",
                    "UI layout",
                    "agent activity panels",
                    "project status widgets",
                    "reports viewer",
                    "error monitoring",
                    "mission control interface"
                ]
            },
            {
                "id": "improve-dashboard",
                "title": "Continuously improve dashboard design, content, commands, monitoring, and analytics",
                "agents": [
                    "product/product-manager.md",
                    "design/design-ui-designer.md",
                    "design/design-ux-architect.md",
                    "design/design-whimsy-injector.md",
                    "engineering/engineering-frontend-developer.md",
                    "support/support-analytics-reporter.md",
                    "testing/testing-reality-checker.md",
                    "testing/testing-performance-benchmarker.md",
                    "specialized/agents-orchestrator.md"
                ],
                "output": [
                    "UI/UX improvements",
                    "dashboard content improvements",
                    "monitoring widgets",
                    "agent status panels",
                    "mission control improvements",
                    "error and quota visibility",
                    "performance recommendations",
                    "implementation-ready frontend tasks"
                ]
            }
        ]
    },

    "yallaplays": {
        "project": "YallaPlays",
        "goal": "Continuously grow and improve the HTML5 game platform.",
        "active_missions": [
            {
                "id": "create-new-games",
                "title": "Create and add new games",
                "agents": [
                    "game-development/game-designer.md",
                    "game-development/level-designer.md",
                    "engineering/engineering-frontend-developer.md",
                    "testing/testing-reality-checker.md"
                ],
                "output": [
                    "new game idea",
                    "game specification",
                    "HTML/JS implementation plan",
                    "SEO game page metadata",
                    "QA checklist"
                ]
            },
            {
                "id": "seo-growth",
                "title": "Improve SEO and organic traffic",
                "agents": [
                    "marketing/marketing-seo-specialist.md",
                    "marketing/marketing-growth-hacker.md",
                    "marketing/marketing-content-creator.md"
                ],
                "output": [
                    "SEO issues",
                    "metadata improvements",
                    "new keyword opportunities",
                    "internal linking plan"
                ]
            },
            {
                "id": "performance-qa",
                "title": "Improve speed and quality",
                "agents": [
                    "testing/testing-performance-benchmarker.md",
                    "engineering/engineering-code-reviewer.md"
                ],
                "output": [
                    "performance bottlenecks",
                    "code cleanup tasks",
                    "priority fixes"
                ]
            }
        ]
    },

    "fionera": {
        "project": "Fionera",
        "goal": "Continuously improve the finance dashboard and investment tools.",
        "active_missions": [
            {
                "id": "finance-intelligence",
                "title": "Improve finance intelligence",
                "agents": [
                    "finance/finance-investment-researcher.md",
                    "finance/finance-financial-analyst.md",
                    "finance/finance-fpa-analyst.md"
                ],
                "output": [
                    "portfolio insights",
                    "market data improvements",
                    "risk analysis features",
                    "watchlist enhancements"
                ]
            },
            {
                "id": "dashboard-product",
                "title": "Improve dashboard product experience",
                "agents": [
                    "product/product-manager.md",
                    "design/design-ui-designer.md",
                    "engineering/engineering-frontend-developer.md"
                ],
                "output": [
                    "UX improvements",
                    "feature priorities",
                    "dashboard layout improvements",
                    "implementation tasks"
                ]
            },
            {
                "id": "security-cleanup",
                "title": "Clean security and API key risks",
                "agents": [
                    "engineering/engineering-security-engineer.md",
                    "engineering/engineering-code-reviewer.md"
                ],
                "output": [
                    "security issues",
                    "env migration plan",
                    "safe config structure"
                ]
            }
        ]
    },

    "mifteh-main-site": {
        "project": "MIFTEH Main Site",
        "goal": "Continuously improve the business platform for branding, conversion, SEO, analytics, automation, and scalability.",
        "active_missions": [
            {
                "id": "brand-conversion-growth",
                "title": "Improve branding, conversion, and business platform messaging",
                "agents": [
                    "product/product-manager.md",
                    "marketing/marketing-growth-hacker.md",
                    "marketing/marketing-content-creator.md",
                    "design/design-ux-architect.md"
                ],
                "output": [
                    "brand positioning opportunities",
                    "conversion funnel improvements",
                    "landing page messaging recommendations",
                    "analytics and measurement priorities"
                ]
            },
            {
                "id": "seo-visibility",
                "title": "Improve SEO visibility and organic acquisition",
                "agents": [
                    "marketing/marketing-seo-specialist.md",
                    "marketing/marketing-content-creator.md",
                    "engineering/engineering-frontend-developer.md"
                ],
                "output": [
                    "SEO audit findings",
                    "metadata and structured data opportunities",
                    "content expansion plan",
                    "technical SEO implementation tasks"
                ]
            },
            {
                "id": "site-performance-ux",
                "title": "Optimize site performance, UI/UX, and scalability",
                "agents": [
                    "testing/testing-performance-benchmarker.md",
                    "design/design-ui-designer.md",
                    "engineering/engineering-code-reviewer.md"
                ],
                "output": [
                    "performance bottlenecks",
                    "UI/UX improvements",
                    "scalability risks",
                    "implementation-ready optimization tasks"
                ]
            }
        ]
    }
}


def get_project_missions(project_id: str):
    if project_id not in MISSIONS:
        return {
            "error": "No missions found for this project"
        }

    return {
        "project_id": project_id,
        **MISSIONS[project_id]
    }


def list_all_missions():
    return {
        "projects_count": len(MISSIONS),
        "projects": MISSIONS
    }

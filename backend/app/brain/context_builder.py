from pathlib import Path
from app.core.projects import PROJECTS

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build"
}

IMPORTANT_EXTENSIONS = {
    ".html",
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".md",
    ".json",
    ".py"
}


def build_project_context(project_id: str):

    if project_id not in PROJECTS:
        return {
            "error": "Project not found"
        }

    project = PROJECTS[project_id]
    root = Path(project["path"]).resolve()

    docs = []
    scripts = []
    pages = []
    configs = []
    styles = []

    for file in root.rglob("*"):

        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if not file.is_file():
            continue

        if file.suffix not in IMPORTANT_EXTENSIONS:
            continue

        relative = str(file.relative_to(root))

        item = {
            "name": file.name,
            "path": relative,
            "size": file.stat().st_size,
            "extension": file.suffix
        }

        if file.suffix == ".md":
            docs.append(item)
        elif file.suffix in [".js", ".ts", ".tsx", ".py"]:
            scripts.append(item)
        elif file.suffix == ".html":
            pages.append(item)
        elif file.suffix in [".json"]:
            configs.append(item)
        elif file.suffix == ".css":
            styles.append(item)

    return {
        "project": project["name"],
        "project_id": project_id,
        "type": project["type"],
        "path": project["path"],
        "summary": {
            "docs_count": len(docs),
            "scripts_count": len(scripts),
            "pages_count": len(pages),
            "configs_count": len(configs),
            "styles_count": len(styles)
        },
        "docs": docs[:20],
        "scripts": scripts[:40],
        "pages": pages[:40],
        "configs": configs[:20],
        "styles": styles[:20],
        "initial_analysis": {
            "architecture_hint": "Static/frontend-heavy project with modular files.",
            "next_best_step": "Run AI architecture analysis after OpenAI quota is active.",
            "recommended_agents": [
                "Codebase Onboarding Engineer",
                "Software Architect",
                "Frontend Developer",
                "SEO Specialist"
            ]
        }
    }

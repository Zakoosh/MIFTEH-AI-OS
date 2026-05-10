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

LARGE_FILE_LIMIT = 100000


def generate_health_report(project_id: str):

    if project_id not in PROJECTS:
        return {
            "error": "Project not found"
        }

    project = PROJECTS[project_id]
    root = Path(project["path"]).resolve()

    total_files = 0
    large_files = []
    possible_secrets = []
    html_pages = []
    js_files = []
    docs = []
    config_files = []

    secret_keywords = [
        "API_KEY",
        "SECRET",
        "TOKEN",
        "PASSWORD",
        "SUPABASE_KEY",
        "OPENAI_API_KEY"
    ]

    for file in root.rglob("*"):

        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if not file.is_file():
            continue

        total_files += 1
        relative = str(file.relative_to(root))
        suffix = file.suffix.lower()
        size = file.stat().st_size

        if size > LARGE_FILE_LIMIT:
            large_files.append({
                "file": relative,
                "size": size
            })

        if suffix == ".html":
            html_pages.append(relative)

        if suffix in [".js", ".ts", ".tsx", ".py"]:
            js_files.append(relative)

        if suffix == ".md":
            docs.append(relative)

        if file.name.lower() in ["package.json", "tsconfig.json", "next.config.ts", ".env", ".env.example"]:
            config_files.append(relative)

        if suffix in [".js", ".ts", ".tsx", ".py", ".env", ".example", ".md"]:
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
                for keyword in secret_keywords:
                    if keyword in content:
                        possible_secrets.append({
                            "file": relative,
                            "keyword": keyword
                        })
            except Exception:
                pass

    score = 100

    if len(possible_secrets) > 0:
        score -= 30

    if len(large_files) > 5:
        score -= 10

    if len(docs) == 0:
        score -= 10

    if len(config_files) == 0:
        score -= 10

    score = max(score, 0)

    return {
        "project": project["name"],
        "project_id": project_id,
        "type": project["type"],
        "health_score": score,
        "summary": {
            "total_files": total_files,
            "html_pages": len(html_pages),
            "script_files": len(js_files),
            "docs": len(docs),
            "config_files": len(config_files),
            "large_files": len(large_files),
            "possible_secret_hits": len(possible_secrets)
        },
        "warnings": {
            "possible_secrets": possible_secrets[:20],
            "large_files": large_files[:20]
        },
        "recommendations": [
            "Move all keys and secrets to env files.",
            "Keep .env files ignored by Git.",
            "Split very large HTML or JS files into smaller modules.",
            "Add or improve README and setup docs.",
            "Use AI agents later for architecture analysis when quota is active."
        ]
    }

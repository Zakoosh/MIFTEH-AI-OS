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

SECRET_KEYWORDS = [
    "API_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "SUPABASE_KEY",
    "OPENAI_API_KEY",
    "TWELVE_API_KEY",
    "SUPABASE_URL"
]

ALLOWED_EXTENSIONS = {
    ".js",
    ".ts",
    ".tsx",
    ".py",
    ".env",
    ".example",
    ".md",
    ".json"
}


def scan_security_details(project_id: str):

    if project_id not in PROJECTS:
        return {
            "error": "Project not found"
        }

    project = PROJECTS[project_id]
    root = Path(project["path"]).resolve()

    findings = []

    for file in root.rglob("*"):

        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if not file.is_file():
            continue

        if file.suffix not in ALLOWED_EXTENSIONS:
            continue

        relative = str(file.relative_to(root))

        try:
            lines = file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for index, line in enumerate(lines, start=1):
            upper_line = line.upper()

            for keyword in SECRET_KEYWORDS:
                if keyword in upper_line:
                    clean_line = line.strip()

                    if len(clean_line) > 180:
                        clean_line = clean_line[:180] + "..."

                    findings.append({
                        "file": relative,
                        "line": index,
                        "keyword": keyword,
                        "preview": clean_line
                    })

    return {
        "project": project["name"],
        "project_id": project_id,
        "findings_count": len(findings),
        "findings": findings[:100],
        "recommendations": [
            "Move real private keys to local .env files.",
            "Keep only public-safe frontend keys in public config files.",
            "Replace hardcoded service keys with environment variables.",
            "Never commit .env files.",
            "Regenerate any key that was exposed publicly."
        ]
    }

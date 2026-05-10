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

ALLOWED_EXTENSIONS = {
    ".html",
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".md",
    ".json",
    ".py",
    ".txt"
}


def scan_project(project_id: str):

    if project_id not in PROJECTS:
        return None

    project = PROJECTS[project_id]
    path = Path(project["path"])

    files = []

    for file in path.rglob("*"):

        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if file.is_file():
            files.append({
                "name": file.name,
                "relative_path": str(file.relative_to(path)),
                "path": str(file),
                "suffix": file.suffix
            })

    extensions = {}

    for file in files:
        ext = file["suffix"] or "no_extension"
        extensions[ext] = extensions.get(ext, 0) + 1

    return {
        "project": project["name"],
        "type": project["type"],
        "path": project["path"],
        "files_count": len(files),
        "extensions": extensions,
        "sample_files": files[:30]
    }


def read_project_file(project_id: str, file_path: str):

    if project_id not in PROJECTS:
        return None

    project = PROJECTS[project_id]
    root_path = Path(project["path"]).resolve()
    target_file = (root_path / file_path).resolve()

    if not str(target_file).startswith(str(root_path)):
        return {
            "error": "Access denied"
        }

    if not target_file.exists() or not target_file.is_file():
        return {
            "error": "File not found"
        }

    if target_file.stat().st_size > 300000:
        return {
            "error": "File too large"
        }

    content = target_file.read_text(encoding="utf-8", errors="ignore")

    return {
        "project": project["name"],
        "file": file_path,
        "content": content
    }


def search_project(project_id: str, query: str):

    if project_id not in PROJECTS:
        return None

    project = PROJECTS[project_id]
    root_path = Path(project["path"]).resolve()

    results = []

    for file in root_path.rglob("*"):

        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if not file.is_file():
            continue

        if file.suffix not in ALLOWED_EXTENSIONS:
            continue

        if file.stat().st_size > 300000:
            continue

        content = file.read_text(encoding="utf-8", errors="ignore")

        if query.lower() in content.lower() or query.lower() in file.name.lower():
            results.append({
                "file": str(file.relative_to(root_path)),
                "name": file.name,
                "suffix": file.suffix,
                "preview": content[:500]
            })

    return {
        "project": project["name"],
        "query": query,
        "matches": len(results),
        "results": results[:25]
    }

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

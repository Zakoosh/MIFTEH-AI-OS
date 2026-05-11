from pathlib import Path

from app.core.projects import PROJECTS
from app.integration.models import RepositoryScan


WORKSPACE_ROOT = Path("/workspace").resolve()


def _safe_project_path(project_id: str) -> Path | None:
    project = PROJECTS.get(project_id)
    if not project:
        return None

    raw_path = Path(project.get("path", ""))
    if not raw_path.is_absolute():
        raw_path = WORKSPACE_ROOT / raw_path
    return raw_path


def read_repository(project_id: str, max_files: int = 2000) -> tuple[RepositoryScan, list[Path]]:
    project = PROJECTS.get(project_id, {"name": project_id, "path": "", "type": "unknown"})
    path = _safe_project_path(project_id)
    if path is None:
        return RepositoryScan(
            project_id=project_id,
            project_name=project.get("name", project_id),
            path="",
            error="Project is not registered",
        ), []

    scan = RepositoryScan(
        project_id=project_id,
        project_name=project.get("name", project_id),
        path=str(path),
    )

    try:
        if not path.exists() or not path.is_dir():
            scan.error = "Repository path is unavailable"
            return scan, []

        files: list[Path] = []
        directories = 0
        extensions: dict[str, int] = {}
        for item in path.rglob("*"):
            if any(part in {".git", "node_modules", "__pycache__", "dist", "build"} for part in item.parts):
                continue
            if item.is_dir():
                directories += 1
                continue
            if not item.is_file():
                continue
            files.append(item)
            suffix = item.suffix.lower() or "no_extension"
            extensions[suffix] = extensions.get(suffix, 0) + 1
            if len(files) >= max_files:
                break

        scan.available = True
        scan.files_scanned = len(files)
        scan.directories_scanned = directories
        scan.extensions = extensions
        return scan, files
    except OSError as exc:
        scan.error = str(exc)
        return scan, []

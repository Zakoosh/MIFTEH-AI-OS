import json
import os
from pathlib import Path
from typing import Optional

from app.projects.models import WorkspaceManifest, ProjectEntry

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_WORKSPACE = _BASE_DIR.parent

WORKSPACE_ROOT: Path = Path(
    os.environ.get("MIFTEH_WORKSPACE_ROOT", str(_DEFAULT_WORKSPACE))
)

MANIFEST_PATH = _BASE_DIR / "app" / "memory" / "workspace_manifest.json"


def get_workspace_root() -> Path:
    return WORKSPACE_ROOT


def project_path(directory_name: str) -> Path:
    return WORKSPACE_ROOT / directory_name


def project_exists(directory_name: str) -> bool:
    return project_path(directory_name).is_dir()


def load_manifest() -> Optional[WorkspaceManifest]:
    if not MANIFEST_PATH.is_file():
        return None

    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return WorkspaceManifest(**data)
    except Exception:
        return None


def save_manifest(manifest: WorkspaceManifest) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    MANIFEST_PATH.write_text(
        json.dumps(manifest.model_dump(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def list_workspace_directories() -> list[str]:
    if not WORKSPACE_ROOT.is_dir():
        return []

    return sorted(
        entry.name
        for entry in WORKSPACE_ROOT.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )

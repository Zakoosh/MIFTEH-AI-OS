"""Project registry accessor — single source of truth for all managed projects."""
import json
import os
from pathlib import Path
from typing import Optional

REGISTRY_PATH = Path(__file__).parents[2] / "targets" / "registry.json"


def load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def get_project(project_id: str) -> dict:
    reg = load_registry()
    for p in reg["projects"]:
        if p["id"] == project_id:
            return p
    raise KeyError(f"Project '{project_id}' not found in registry")


def get_all_active_projects() -> list[dict]:
    return [p for p in load_registry()["projects"] if p.get("active")]


def get_production_source(project_id: str) -> Path:
    """Return the absolute path to the production source directory."""
    p = get_project(project_id)
    repo_root = Path(__file__).parents[2]
    return repo_root / p["local_path"]


def get_domain(project_id: str) -> str:
    return get_project(project_id)["domain"]


def get_adsense_publisher(project_id: str) -> Optional[str]:
    p = get_project(project_id)
    return p.get("adsense", {}).get("publisher_id") or None


def get_preview_path(project_id: str) -> Optional[str]:
    p = get_project(project_id)
    return p.get("preview_path")

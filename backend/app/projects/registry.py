from typing import Optional

from app.projects.models import (
    ProjectEntry,
    ProjectSummary,
    WorkspaceManifest,
    WorkspaceStatus,
)
from app.projects.schemas import DEFAULT_PROJECTS
from app.projects.workspace import (
    get_workspace_root,
    project_path,
    project_exists,
    load_manifest,
    save_manifest,
)
from app.projects.repository_manager import get_repository_info
from app.projects.project_mapper import map_agents_for_project, map_missions_for_project


_projects: dict[str, ProjectEntry] = {}


def _build_project_entry(project_id: str, config: dict) -> ProjectEntry:
    directory = config["directory"]
    path = project_path(directory)
    available = project_exists(directory)

    repo_info = get_repository_info(path) if available else None

    project_type = config.get("type", "")
    linked_agents = map_agents_for_project(project_id, project_type) if available else []
    linked_missions = map_missions_for_project(project_id)

    from app.projects.models import RepositoryInfo

    return ProjectEntry(
        project_id=project_id,
        name=config["name"],
        local_path=str(path),
        project_type=project_type,
        available=available,
        repository=repo_info or RepositoryInfo(),
        linked_agents=linked_agents,
        linked_missions=linked_missions,
    )


def refresh_projects() -> dict[str, ProjectEntry]:
    _projects.clear()

    for project_id, config in DEFAULT_PROJECTS.items():
        entry = _build_project_entry(project_id, config)
        _projects[project_id] = entry

    manifest = WorkspaceManifest(
        workspace_root=str(get_workspace_root()),
        projects=list(_projects.values()),
    )
    save_manifest(manifest)

    return dict(_projects)


def list_projects() -> list[ProjectEntry]:
    if not _projects:
        refresh_projects()
    return list(_projects.values())


def get_project(project_id: str) -> Optional[ProjectEntry]:
    if not _projects:
        refresh_projects()
    return _projects.get(project_id)


def get_workspace_status() -> WorkspaceStatus:
    projects = list_projects()

    summaries = [
        ProjectSummary(
            project_id=p.project_id,
            name=p.name,
            project_type=p.project_type,
            available=p.available,
            agents_count=len(p.linked_agents),
            missions_count=len(p.linked_missions),
        )
        for p in projects
    ]

    available = sum(1 for p in projects if p.available)

    return WorkspaceStatus(
        workspace_root=str(get_workspace_root()),
        total_projects=len(projects),
        available_projects=available,
        unavailable_projects=len(projects) - available,
        projects=summaries,
    )

from pathlib import Path
import subprocess

from app.core.projects import PROJECTS
from app.git.models import GitCommandResult, RepositoryInfo
from app.git.safety import (
    GitSafetyError,
    WORKSPACE_ROOT,
    ensure_repository_path,
    is_protected_branch,
    resolve_under_workspace,
)


WORKSPACE_PROJECTS = {
    "workspace": {
        "name": "MIFTEH AI OS",
        "path": str(WORKSPACE_ROOT),
        "type": "workspace",
    },
    "mifteh": {
        "name": "MIFTEH AI OS",
        "path": str(WORKSPACE_ROOT),
        "type": "workspace",
    },
    "mifteh-ai-os": {
        "name": "MIFTEH AI OS",
        "path": str(WORKSPACE_ROOT),
        "type": "workspace",
    },
}


class GitRepository:
    def __init__(self, project_id: str, name: str, path: Path):
        self.project_id = project_id
        self.name = name
        self.path = path

    def run(self, args: list[str], timeout: int = 30) -> GitCommandResult:
        command = ["git", *args]

        try:
            completed = subprocess.run(
                command,
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return GitCommandResult(
                command=command,
                return_code=127,
                success=False,
                error="git executable was not found",
            )
        except subprocess.TimeoutExpired as exc:
            return GitCommandResult(
                command=command,
                return_code=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                success=False,
                error="git command timed out",
            )

        return GitCommandResult(
            command=command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            success=completed.returncode == 0,
            error=None if completed.returncode == 0 else completed.stderr.strip(),
        )

    def current_branch(self) -> str:
        result = self.run(["rev-parse", "--abbrev-ref", "HEAD"])
        if not result.success:
            raise GitSafetyError(result.error or "Unable to resolve current branch")
        return result.stdout.strip()

    def head_sha(self) -> str:
        result = self.run(["rev-parse", "HEAD"])
        if not result.success:
            return ""
        return result.stdout.strip()

    def info(self) -> RepositoryInfo:
        branch = self.current_branch()
        return RepositoryInfo(
            project_id=self.project_id,
            name=self.name,
            path=str(self.path),
            branch=branch,
            head_sha=self.head_sha(),
            protected_branch=is_protected_branch(branch),
        )


def _project_config(project_id: str) -> dict:
    if project_id in WORKSPACE_PROJECTS:
        return WORKSPACE_PROJECTS[project_id]

    project = PROJECTS.get(project_id)
    if project is None:
        raise GitSafetyError(f"Unknown project_id '{project_id}'")

    return project


def load_repository(project_id: str) -> GitRepository:
    project = _project_config(project_id)
    project_path = ensure_repository_path(Path(project["path"]))
    probe_repo = GitRepository(
        project_id=project_id,
        name=project.get("name", project_id),
        path=project_path,
    )

    probe = probe_repo.run(["rev-parse", "--show-toplevel"])
    if not probe.success:
        raise GitSafetyError(probe.error or "Path is not a git repository")

    root_path = resolve_under_workspace(Path(probe.stdout.strip()))
    return GitRepository(
        project_id=project_id,
        name=project.get("name", project_id),
        path=root_path,
    )

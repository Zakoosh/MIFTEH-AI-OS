from app.git.models import GitStatusFile, GitStatusResult
from app.git.repository import load_repository
from app.git.safety import GitSafetyError


def _parse_status_file(line: str) -> GitStatusFile:
    index_status = line[0:1].strip()
    worktree_status = line[1:2].strip()
    status = line[:2].strip()
    path = line[3:]

    if " -> " in path:
        path = path.split(" -> ", 1)[1]

    return GitStatusFile(
        path=path,
        status=status,
        index_status=index_status,
        worktree_status=worktree_status,
    )


def get_repository_status(project_id: str) -> GitStatusResult:
    try:
        repository = load_repository(project_id)
        status = repository.run(["status", "--porcelain=v1", "-b"])

        if not status.success:
            return GitStatusResult(
                success=False,
                project_id=project_id,
                error=status.error or "Unable to read repository status",
            )

        lines = [line for line in status.stdout.splitlines() if line]
        files = [
            _parse_status_file(line)
            for line in lines
            if not line.startswith("## ")
        ]
        info = repository.info()

        return GitStatusResult(
            success=True,
            project_id=project_id,
            repository=info,
            branch=info.branch,
            is_clean=len(files) == 0,
            files=files,
            raw_status=status.stdout,
        )
    except GitSafetyError as exc:
        return GitStatusResult(
            success=False,
            project_id=project_id,
            is_clean=False,
            error=str(exc),
        )

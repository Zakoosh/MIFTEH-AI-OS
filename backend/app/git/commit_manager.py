from app.git.models import GitCommitResult
from app.git.repository import load_repository
from app.git.safety import GitSafetyError, assert_branch_not_protected, resolve_repo_file


def create_commit(
    project_id: str,
    message: str,
    files: list[str] | None = None,
    stage_all: bool = False,
) -> GitCommitResult:
    safe_files = files or []

    try:
        clean_message = message.strip()
        if not clean_message:
            raise GitSafetyError("Commit message is required")

        repository = load_repository(project_id)
        branch = repository.current_branch()
        assert_branch_not_protected(branch, "commit")

        staged_files: list[str] = []

        if safe_files:
            staged_files = [
                resolve_repo_file(repository.path, file_path)
                for file_path in safe_files
            ]
            add_result = repository.run(["add", "--", *staged_files])

            if not add_result.success:
                return GitCommitResult(
                    success=False,
                    project_id=project_id,
                    repository=repository.info(),
                    branch=branch,
                    message=clean_message,
                    files=staged_files,
                    stage_all=stage_all,
                    error=add_result.error or "Unable to stage files",
                )
        elif stage_all:
            add_result = repository.run(["add", "--all"])

            if not add_result.success:
                return GitCommitResult(
                    success=False,
                    project_id=project_id,
                    repository=repository.info(),
                    branch=branch,
                    message=clean_message,
                    stage_all=stage_all,
                    error=add_result.error or "Unable to stage changes",
                )

        staged_diff = repository.run(["diff", "--cached", "--quiet"])
        if staged_diff.return_code == 0:
            return GitCommitResult(
                success=False,
                project_id=project_id,
                repository=repository.info(),
                branch=branch,
                message=clean_message,
                files=staged_files,
                stage_all=stage_all,
                error="No staged changes to commit",
            )

        if staged_diff.return_code not in (0, 1):
            return GitCommitResult(
                success=False,
                project_id=project_id,
                repository=repository.info(),
                branch=branch,
                message=clean_message,
                files=staged_files,
                stage_all=stage_all,
                error=staged_diff.error or "Unable to inspect staged changes",
            )

        commit = repository.run(["commit", "-m", clean_message], timeout=60)
        if not commit.success:
            return GitCommitResult(
                success=False,
                project_id=project_id,
                repository=repository.info(),
                branch=branch,
                message=clean_message,
                files=staged_files,
                stage_all=stage_all,
                error=commit.error or "Unable to create commit",
            )

        return GitCommitResult(
            success=True,
            project_id=project_id,
            repository=repository.info(),
            branch=branch,
            commit_sha=repository.head_sha(),
            message=clean_message,
            files=staged_files,
            stage_all=stage_all,
        )
    except GitSafetyError as exc:
        return GitCommitResult(
            success=False,
            project_id=project_id,
            message=message,
            files=safe_files,
            stage_all=stage_all,
            error=str(exc),
        )

from typing import Optional

from app.git.models import GitDiffResult
from app.git.repository import load_repository
from app.git.safety import GitSafetyError, validate_git_ref


def generate_diff(
    project_id: str,
    staged: bool = False,
    base_ref: Optional[str] = None,
) -> GitDiffResult:
    try:
        safe_base_ref = validate_git_ref(base_ref, "base_ref") if base_ref else None
        repository = load_repository(project_id)
        args = ["diff", "--no-ext-diff"]

        if staged:
            args.append("--cached")

        if safe_base_ref:
            args.append(safe_base_ref)

        args.append("--")
        diff = repository.run(args)

        if not diff.success:
            return GitDiffResult(
                success=False,
                project_id=project_id,
                staged=staged,
                base_ref=safe_base_ref,
                error=diff.error or "Unable to generate git diff",
            )

        return GitDiffResult(
            success=True,
            project_id=project_id,
            repository=repository.info(),
            staged=staged,
            base_ref=safe_base_ref,
            has_changes=bool(diff.stdout.strip()),
            diff=diff.stdout,
        )
    except GitSafetyError as exc:
        return GitDiffResult(
            success=False,
            project_id=project_id,
            staged=staged,
            base_ref=base_ref,
            error=str(exc),
        )

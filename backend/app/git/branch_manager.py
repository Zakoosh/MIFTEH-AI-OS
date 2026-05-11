from typing import Optional

from app.git.models import GitBranchResult
from app.git.repository import load_repository
from app.git.safety import GitSafetyError, validate_branch_name


def create_branch(
    project_id: str,
    branch_name: str,
    base_branch: Optional[str] = None,
    checkout: bool = True,
) -> GitBranchResult:
    try:
        safe_branch = validate_branch_name(branch_name)
        repository = load_repository(project_id)

        args = ["switch", "-c", safe_branch] if checkout else ["branch", safe_branch]

        if base_branch:
            args.append(base_branch.strip())

        result = repository.run(args)

        if not result.success:
            return GitBranchResult(
                success=False,
                project_id=project_id,
                branch_name=safe_branch,
                base_branch=base_branch,
                checked_out=False,
                error=result.error or "Unable to create branch",
            )

        return GitBranchResult(
            success=True,
            project_id=project_id,
            branch_name=safe_branch,
            base_branch=base_branch,
            checked_out=checkout,
            repository=repository.info(),
        )
    except GitSafetyError as exc:
        return GitBranchResult(
            success=False,
            project_id=project_id,
            branch_name=branch_name,
            base_branch=base_branch,
            checked_out=False,
            error=str(exc),
        )

from app.execution.models import ExecutionPreview, ValidationResult


def validate_preview(preview: ExecutionPreview) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not preview.items:
        errors.append("Preview generated no items")

    if preview.project_id not in {"yallaplays", "fionera"}:
        errors.append("Execution pipelines only support YallaPlays and Fionera")

    for item in preview.items:
        if item.get("deployment_allowed") is True:
            errors.append("Deployment is not allowed in controlled execution")
        if item.get("destructive") is True:
            errors.append("Destructive operations are not allowed")

    if len(preview.items) > 25:
        warnings.append("Large preview batch should be reviewed carefully before apply")

    return ValidationResult(
        pipeline=preview.pipeline,
        validated=not errors,
        ready_for_apply=not errors,
        errors=errors,
        warnings=warnings,
    )

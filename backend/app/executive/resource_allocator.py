from app.executive.models import ResourceAllocation, ResourceDistribution


PROJECT_BASELINE = {
    "mifteh-main-site": 28,
    "yallaplays": 24,
    "fionera": 18,
    "mifteh": 20,
}


def _project_score(project_strategy: object) -> tuple[int, list[str]]:
    score = PROJECT_BASELINE.get(project_strategy.project_id, 12)
    rationale = []
    alignment_score = project_strategy.business_alignment.alignment_score

    if project_strategy.project_id == "mifteh-main-site":
        score += 12
        rationale.append("Business-facing growth and conversion layer")

    if alignment_score >= 70:
        score += 8
        rationale.append("Strong business alignment")
    elif alignment_score < 55:
        score += 5
        rationale.append("Needs corrective executive attention")

    if project_strategy.opportunities:
        score += min(len(project_strategy.opportunities) * 3, 12)
        rationale.append("Active strategic opportunities")

    if project_strategy.risks:
        score += min(len(project_strategy.risks) * 2, 8)
        rationale.append("Risk reduction requires focus")

    return score, rationale or ["Maintain continuous optimization coverage"]


def allocate_resources(project_strategies: list) -> ResourceDistribution:
    raw_scores: dict[str, int] = {}
    rationales: dict[str, list[str]] = {}

    for project in project_strategies:
        score, rationale = _project_score(project)
        raw_scores[project.project_id] = max(score, 1)
        rationales[project.project_id] = rationale

    total = sum(raw_scores.values()) or 1
    distribution = {
        project_id: round(score / total * 100)
        for project_id, score in raw_scores.items()
    }

    drift = 100 - sum(distribution.values())
    if distribution:
        top_project = max(distribution, key=distribution.get)
        distribution[top_project] += drift

    allocations = [
        ResourceAllocation(
            project_id=project.project_id,
            project=project.project,
            allocation_percent=distribution.get(project.project_id, 0),
            rationale=rationales.get(project.project_id, []),
        )
        for project in project_strategies
    ]
    allocations.sort(key=lambda item: item.allocation_percent, reverse=True)

    return ResourceDistribution(resource_distribution=distribution, allocations=allocations)

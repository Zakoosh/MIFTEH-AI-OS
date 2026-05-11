from app.executive.models import ExecutiveRecommendation


def highest_priority_project(resource_distribution: dict[str, int], priorities: list) -> str:
    if resource_distribution:
        return max(resource_distribution, key=resource_distribution.get)

    priority_projects = [
        project
        for priority in priorities[:5]
        for project in priority.projects
        if project != "portfolio"
    ]

    if priority_projects:
        return priority_projects[0]

    return ""


def build_focus_recommendations(
    company_focus: str,
    highest_project: str,
    resource_distribution: dict[str, int],
    priorities: list,
) -> list[ExecutiveRecommendation]:
    recommendations: list[ExecutiveRecommendation] = []

    if highest_project == "mifteh-main-site":
        recommendations.append(ExecutiveRecommendation(
            executive_recommendation=(
                "Increase conversion and SEO investment for mifteh-main-site while using other projects as proof points."
            ),
            priority="high",
            expected_impact=88,
            projects=["mifteh-main-site", "mifteh", "yallaplays"],
            supporting_signals=["highest priority project", "business-facing acquisition layer"],
        ))

    if "yallaplays" in resource_distribution:
        recommendations.append(ExecutiveRecommendation(
            executive_recommendation=(
                "Increase SEO investment for YallaPlays while improving conversion funnels on mifteh-main-site."
            ),
            priority="high" if company_focus in {"growth", "SEO", "conversion"} else "medium",
            expected_impact=84,
            projects=["yallaplays", "mifteh-main-site"],
            supporting_signals=["consumer growth engine", "SEO opportunity"],
        ))

    recommendations.append(ExecutiveRecommendation(
        executive_recommendation=(
            "Use MIFTEH AI OS orchestration and memory layers to rebalance execution focus every strategy cycle."
        ),
        priority="medium",
        expected_impact=76,
        projects=["mifteh"],
        supporting_signals=[priority.priority for priority in priorities[:3]],
    ))

    recommendations.sort(key=lambda item: item.expected_impact, reverse=True)
    return recommendations

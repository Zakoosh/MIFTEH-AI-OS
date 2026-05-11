from app.integration.models import SafeApplyPreview


def build_yallaplays_previews(missing_categories: list[str], seo_gap_count: int) -> list[SafeApplyPreview]:
    previews = []
    if missing_categories:
        previews.append(SafeApplyPreview(
            project_id="yallaplays",
            title="Preview category expansion plan",
            target_files=["categories config", "navigation metadata"],
            notes=[f"Missing categories: {', '.join(missing_categories)}"],
        ))
    if seo_gap_count:
        previews.append(SafeApplyPreview(
            project_id="yallaplays",
            title="Preview SEO metadata improvements",
            target_files=["game pages", "category pages"],
            notes=[f"{seo_gap_count} SEO gaps detected"],
        ))
    return previews


def build_fionera_previews(missing_features: list[str]) -> list[SafeApplyPreview]:
    return [
        SafeApplyPreview(
            project_id="fionera",
            title=f"Preview feature proposal: {feature}",
            target_files=["dashboard components", "analytics modules"],
            notes=["No overwrite; generate implementation plan only"],
        )
        for feature in missing_features[:5]
    ]

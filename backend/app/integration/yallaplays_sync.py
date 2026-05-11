from app.integration.asset_tracker import track_assets
from app.integration.content_mapper import detect_yallaplays_content
from app.integration.models import YallaPlaysIntegration
from app.integration.repository_reader import read_repository
from app.integration.safe_apply import build_yallaplays_previews
from app.integration.seo_mapper import analyze_seo_gaps


EXPECTED_CATEGORIES = ["racing", "puzzle", "sports", "arcade", "adventure", "strategy", "survival", "idle"]


def sync_yallaplays(max_files: int = 2000) -> YallaPlaysIntegration:
    repository, files = read_repository("yallaplays", max_files=max_files)
    root = None
    if repository.available:
        from pathlib import Path
        root = Path(repository.path)

    content = detect_yallaplays_content(root, files) if root else {
        "games_detected": 0,
        "categories_detected": [],
        "content_paths": [],
    }
    missing_categories = [
        category for category in EXPECTED_CATEGORIES
        if category not in content["categories_detected"]
    ]
    seo_gaps = analyze_seo_gaps("yallaplays", files)
    assets = track_assets("yallaplays", files)
    metadata_gaps = []
    if content["games_detected"] and seo_gaps:
        metadata_gaps.append("Some game/category pages are missing title or description metadata")
    if not repository.available:
        metadata_gaps.append("Repository unavailable; metadata scan is limited")

    return YallaPlaysIntegration(
        repository=repository,
        games_detected=content["games_detected"],
        categories_detected=content["categories_detected"],
        missing_categories=missing_categories,
        seo_gaps=seo_gaps,
        metadata_gaps=metadata_gaps,
        assets=assets,
        apply_previews=build_yallaplays_previews(missing_categories, len(seo_gaps)),
    )

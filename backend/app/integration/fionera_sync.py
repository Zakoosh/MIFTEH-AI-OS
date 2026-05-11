from app.integration.asset_tracker import track_assets
from app.integration.content_mapper import detect_fionera_content
from app.integration.models import FioneraIntegration
from app.integration.repository_reader import read_repository
from app.integration.safe_apply import build_fionera_previews


EXPECTED_FEATURES = ["portfolio heatmap", "earnings calendar", "risk alerts", "watchlist scoring"]


def sync_fionera(max_files: int = 2000) -> FioneraIntegration:
    repository, files = read_repository("fionera", max_files=max_files)
    root = None
    if repository.available:
        from pathlib import Path
        root = Path(repository.path)

    content = detect_fionera_content(root, files) if root else {
        "watchlists_detected": 0,
        "dashboards_detected": 0,
        "analytics_components": [],
    }
    detected_text = " ".join(content.get("analytics_components", [])).lower()
    missing_features = [
        feature for feature in EXPECTED_FEATURES
        if feature.replace(" ", "-") not in detected_text and feature not in detected_text
    ]
    ux_gaps = []
    if content["watchlists_detected"] == 0:
        ux_gaps.append("Watchlist UX structure not detected")
    if content["dashboards_detected"] == 0:
        ux_gaps.append("Dashboard component structure not detected")
    if not repository.available:
        ux_gaps.append("Repository unavailable; finance UX scan is limited")

    return FioneraIntegration(
        repository=repository,
        watchlists_detected=content["watchlists_detected"],
        dashboards_detected=content["dashboards_detected"],
        missing_features=missing_features,
        analytics_components=content.get("analytics_components", []),
        ux_gaps=ux_gaps,
        assets=track_assets("fionera", files),
        apply_previews=build_fionera_previews(missing_features),
    )

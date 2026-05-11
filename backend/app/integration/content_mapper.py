from pathlib import Path

from app.integration.file_scanner import read_text_preview, relative_paths, text_files


GAME_KEYWORDS = {"game", "games", "play", "arcade", "racing", "puzzle", "sports", "adventure"}
WATCHLIST_KEYWORDS = {"watchlist", "portfolio", "symbol", "ticker", "market"}
DASHBOARD_KEYWORDS = {"dashboard", "chart", "analytics", "insight", "widget"}


def detect_yallaplays_content(root: Path, files: list[Path]) -> dict:
    paths = relative_paths(root, files)
    game_paths = [
        path for path in paths
        if any(keyword in path.lower() for keyword in GAME_KEYWORDS)
    ]
    categories = sorted({
        category for category in ["racing", "puzzle", "sports", "arcade", "adventure", "strategy"]
        if any(category in path.lower() for path in paths)
    })
    text_hits = 0
    for file_path in text_files(files[:300]):
        content = read_text_preview(file_path).lower()
        if "play" in content and "game" in content:
            text_hits += 1

    return {
        "games_detected": max(len(game_paths), text_hits),
        "categories_detected": categories,
        "content_paths": game_paths[:25],
    }


def detect_fionera_content(root: Path, files: list[Path]) -> dict:
    paths = relative_paths(root, files)
    watchlist_paths = [
        path for path in paths
        if any(keyword in path.lower() for keyword in WATCHLIST_KEYWORDS)
    ]
    dashboard_paths = [
        path for path in paths
        if any(keyword in path.lower() for keyword in DASHBOARD_KEYWORDS)
    ]
    analytics_components = sorted({
        label for label in ["charts", "watchlists", "portfolio", "market-data", "analytics", "insights"]
        if any(label.replace("-", "") in path.lower().replace("-", "") for path in paths)
    })
    return {
        "watchlists_detected": len(watchlist_paths),
        "dashboards_detected": len(dashboard_paths),
        "analytics_components": analytics_components,
        "watchlist_paths": watchlist_paths[:25],
        "dashboard_paths": dashboard_paths[:25],
    }

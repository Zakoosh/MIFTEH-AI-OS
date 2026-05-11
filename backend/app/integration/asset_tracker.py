from pathlib import Path

from app.integration.models import AssetSummary


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
SCRIPT_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx"}
STYLE_EXTENSIONS = {".css", ".scss", ".sass", ".less"}
DATA_EXTENSIONS = {".json", ".csv", ".yaml", ".yml"}


def track_assets(project_id: str, files: list[Path]) -> AssetSummary:
    large_assets: list[str] = []
    images = scripts = stylesheets = data_files = 0

    for file_path in files:
        suffix = file_path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            images += 1
        elif suffix in SCRIPT_EXTENSIONS:
            scripts += 1
        elif suffix in STYLE_EXTENSIONS:
            stylesheets += 1
        elif suffix in DATA_EXTENSIONS:
            data_files += 1

        try:
            if file_path.stat().st_size > 500000:
                large_assets.append(file_path.name)
        except OSError:
            continue

    return AssetSummary(
        project_id=project_id,
        images=images,
        scripts=scripts,
        stylesheets=stylesheets,
        data_files=data_files,
        large_assets=large_assets[:20],
    )

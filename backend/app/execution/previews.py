from app.execution.fionera_pipeline import run_fionera_market_cycle, run_fionera_watchlist_cycle
from app.execution.models import ExecutionPreview
from app.execution.validation import validate_preview
from app.execution.yallaplays_pipeline import (
    run_yallaplays_game_batch,
    run_yallaplays_mobile_cycle,
    run_yallaplays_seo_batch,
)


def build_preview(pipeline: str, limit: int = 5) -> ExecutionPreview | None:
    if pipeline == "yallaplays_game_batch":
        preview = run_yallaplays_game_batch(limit=limit)
    elif pipeline == "yallaplays_seo_batch":
        preview = run_yallaplays_seo_batch(limit=limit)
    elif pipeline == "yallaplays_mobile_cycle":
        preview = run_yallaplays_mobile_cycle()
    elif pipeline == "fionera_market_cycle":
        preview = run_fionera_market_cycle()
    elif pipeline == "fionera_watchlist_cycle":
        preview = run_fionera_watchlist_cycle()
    else:
        return None

    preview.validation = validate_preview(preview)
    return preview


def build_all_previews() -> list[ExecutionPreview]:
    return [
        preview for preview in [
            build_preview("yallaplays_game_batch"),
            build_preview("yallaplays_seo_batch", limit=25),
            build_preview("yallaplays_mobile_cycle"),
            build_preview("fionera_market_cycle"),
            build_preview("fionera_watchlist_cycle"),
        ]
        if preview is not None
    ]

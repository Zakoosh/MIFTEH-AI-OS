from app.execution.models import ExecutionPipeline


PIPELINES = {
    "yallaplays_game_batch": ExecutionPipeline(
        pipeline="yallaplays_game_batch",
        project_id="yallaplays",
        description="Generate game idea batches with metadata and implementation tasks.",
    ),
    "yallaplays_seo_batch": ExecutionPipeline(
        pipeline="yallaplays_seo_batch",
        project_id="yallaplays",
        description="Generate SEO metadata batches and category optimization previews.",
    ),
    "yallaplays_mobile_cycle": ExecutionPipeline(
        pipeline="yallaplays_mobile_cycle",
        project_id="yallaplays",
        description="Generate mobile UX optimization cycle recommendations.",
    ),
    "fionera_market_cycle": ExecutionPipeline(
        pipeline="fionera_market_cycle",
        project_id="fionera",
        description="Collect market signals and generate finance insight cycles.",
    ),
    "fionera_watchlist_cycle": ExecutionPipeline(
        pipeline="fionera_watchlist_cycle",
        project_id="fionera",
        description="Build watchlist and analytics improvement previews.",
    ),
}


def list_pipelines() -> list[ExecutionPipeline]:
    return list(PIPELINES.values())


def get_pipeline(name: str) -> ExecutionPipeline | None:
    return PIPELINES.get(name)

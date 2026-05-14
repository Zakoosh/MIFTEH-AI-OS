from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from ..operations.operation_engine import OperationEngine
from ..operations.production_runner import ProductionRunner, PREVIEWS_DIR, PR_OUTPUTS_DIR
from ..core.config import get_config
from ..operations.schemas import (
    GenerateRequest, GenerateResponse, OutputsListResponse,
    PreviewResponse, ApplyOutputRequest, ApplyOutputResponse, OperationsStatusResponse,
)

router = APIRouter(prefix="/operations", tags=["operations"])
engine = OperationEngine()
runner = ProductionRunner()


@router.get("/status", response_model=OperationsStatusResponse)
async def get_status():
    return OperationsStatusResponse(**engine.get_status())


@router.get("/outputs", response_model=OutputsListResponse)
async def list_outputs(
    project: str | None = Query(None),
    output_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    outputs = engine._memory.get_outputs(project=project, output_type=output_type, status=status, limit=limit)
    by_project: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for o in outputs:
        by_project[o.get("project", "unknown")] = by_project.get(o.get("project", "unknown"), 0) + 1
        by_type[o.get("output_type", "unknown")] = by_type.get(o.get("output_type", "unknown"), 0) + 1
        by_status[o.get("status", "unknown")] = by_status.get(o.get("status", "unknown"), 0) + 1
    pending = len([o for o in outputs if o.get("status") in ("generated", "previewed")])
    return OutputsListResponse(outputs=outputs, total=len(outputs), by_project=by_project, by_type=by_type, by_status=by_status, pending_apply=pending)


@router.post("/generate", response_model=GenerateResponse)
async def generate_output(request: GenerateRequest):
    project = request.project.value if hasattr(request.project, "value") else request.project
    output_type = request.output_type.value if hasattr(request.output_type, "value") else request.output_type
    result = await engine.generate(
        project=project,
        output_type=output_type,
        topic=request.topic,
        use_ai=request.use_ai,
        count=request.count,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Generation failed"))
    return GenerateResponse(
        success=True,
        outputs=result.get("outputs", []),
        batch_id=result.get("batch_id"),
        preview_ids=result.get("preview_ids", []),
        message=result.get("message", "Generated"),
        total_generated=result.get("total_generated", 0),
        cost_usd=result.get("cost_usd", 0.0),
    )


@router.post("/generate-all/{project}")
async def generate_all(project: str, use_ai: bool = Query(False)):
    if project not in ("yallaplays", "fionera"):
        raise HTTPException(status_code=400, detail=f"Unknown project: {project}")
    result = await engine.generate_all_for_project(project=project, use_ai=use_ai)
    return result


@router.get("/preview/{output_id}")
async def get_preview(output_id: str, format: str = Query("json")):
    preview_data = engine.get_preview(output_id)
    if not preview_data:
        raise HTTPException(status_code=404, detail=f"Output {output_id} not found")
    if format == "html":
        return HTMLResponse(content=preview_data.get("html", ""), status_code=200)
    return preview_data


@router.post("/apply", response_model=ApplyOutputResponse)
async def apply_output(request: ApplyOutputRequest):
    result = engine.apply_output(
        output_id=request.output_id,
        dry_run=request.dry_run,
        notes=request.notes,
    )
    if not result.get("success") and not request.dry_run:
        raise HTTPException(status_code=400, detail=result.get("error", "Apply failed"))
    return ApplyOutputResponse(
        success=result.get("success", False) or result.get("all_valid", False),
        output_id=request.output_id,
        apply_id=result.get("apply_id"),
        dry_run=request.dry_run,
        message=result.get("note", "Dry-run validation complete" if request.dry_run else "Applied"),
        rollback_id=result.get("rollback_id"),
    )


@router.get("/analytics")
async def get_analytics(project: str | None = Query(None)):
    analytics = engine._memory.get_analytics(project)
    return {"project": project or "all", **analytics}


@router.get("/yallaplays/outputs")
async def yallaplays_outputs(output_type: str | None = Query(None)):
    outputs = engine._memory.get_outputs(project="yallaplays", output_type=output_type)
    return {"project": "yallaplays", "outputs": outputs, "total": len(outputs)}


@router.get("/fionera/outputs")
async def fionera_outputs(output_type: str | None = Query(None)):
    outputs = engine._memory.get_outputs(project="fionera", output_type=output_type)
    return {"project": "fionera", "outputs": outputs, "total": len(outputs)}


@router.post("/run-production-cycle")
async def run_production_cycle(background_tasks: BackgroundTasks):
    """Run a full production generation cycle for both projects."""
    background_tasks.add_task(_run_cycle_background)
    return {
        "status": "started",
        "message": "Production cycle started in background",
        "dashboard": "https://yallaplays.com/admin/os",
        "monitor_at": "/operations/production-report",
    }


async def _run_cycle_background():
    await runner.run_full_production_cycle()


@router.post("/run-campaign/{project}")
async def run_campaign(project: str):
    """Run a full generation campaign for a specific project immediately."""
    if project not in ("yallaplays", "fionera"):
        raise HTTPException(status_code=400, detail=f"Unknown project: {project}")
    if project == "yallaplays":
        result = await runner.run_yallaplays_campaign()
    else:
        result = await runner.run_fionera_campaign()
    return result


@router.get("/production-report")
async def get_production_report():
    """Get the latest production cycle report."""
    report = runner.get_latest_report()
    if not report:
        return {"status": "no_report", "message": "No production cycle has been run yet. POST /operations/run-production-cycle"}
    return report


@router.get("/html-previews")
async def list_html_previews():
    """List all generated HTML preview files."""
    previews = runner.list_html_previews()
    return {"previews": previews, "total": len(previews), "preview_dir": str(PREVIEWS_DIR)}


@router.get("/preview-files/{filename}")
async def serve_preview_file(filename: str):
    """Serve a generated HTML preview file."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = PREVIEWS_DIR / filename
    if not path.exists() or path.suffix != ".html":
        raise HTTPException(status_code=404, detail="Preview file not found")
    return HTMLResponse(content=path.read_text(), status_code=200)


@router.get("/pr-outputs")
async def list_pr_outputs():
    """List all PR-ready output files."""
    outputs = runner.list_pr_outputs()
    return {"pr_outputs": outputs, "total": len(outputs)}


@router.get("/pr-outputs/{filename}")
async def get_pr_output(filename: str):
    """Get a specific PR-ready output file."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = PR_OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="PR output not found")
    import json
    return json.loads(path.read_text())


@router.get("/provider-status")
async def get_provider_status():
    """Real-time AI provider activation status with live health probe."""
    cfg = get_config()
    from ..operations.content_generator import ContentGenerator
    gen = ContentGenerator()
    ai_health = await gen.generate("ping", max_tokens=5)
    if ai_health.get("success"):
        live_provider = ai_health.get("provider", "unknown")
        ai_status = "live"
    elif ai_health.get("error") == "rate_limited":
        live_provider = ai_health.get("provider", "unknown")
        ai_status = "rate_limited"
    else:
        live_provider = "none"
        ai_status = "unavailable"
    return {
        "dashboard_url": "https://yallaplays.com/admin/os",
        "providers": cfg.provider_summary(),
        "live_ai_status": ai_status,
        "live_provider": live_provider,
        "fallback_chain": ["openai", "gemini", "template"],
        "generation_mode": "ai" if ai_status == "live" else "template_fallback",
        "market_data": {
            "twelve_data": cfg.twelve_data_api_key != "",
            "alpha_vantage": cfg.alpha_vantage_key != "",
        },
        "cost_limits": {
            "daily_budget_usd": cfg.daily_budget_usd,
            "max_ops_per_hour": cfg.max_ops_per_hour,
        },
    }

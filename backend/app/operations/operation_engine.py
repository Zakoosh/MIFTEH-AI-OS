from __future__ import annotations
import asyncio
from datetime import datetime
from pathlib import Path
from .models import OperationalOutput, OperationalPreview, OperationBatch, OperationProject, OutputType, OutputStatus
from .operation_memory import OperationMemory
from .preview_generator import PreviewGenerator
from .apply_bridge import ApplyBridge
from .yallaplays.seo_generator import YallaPlaysSEOGenerator
from .yallaplays.category_pages import CategoryPageGenerator
from .yallaplays.metadata_patches import MetadataPatchGenerator
from .yallaplays.mobile_optimizer import MobileOptimizer
from .yallaplays.internal_linking import InternalLinkingGenerator
from .yallaplays.game_recommendations import GameRecommendationGenerator
from .fionera.finance_widgets import FinanceWidgetGenerator
from .fionera.market_insights import MarketInsightGenerator
from .fionera.watchlist_improvements import WatchlistImprovementGenerator
from .fionera.analytics_dashboard import AnalyticsDashboardGenerator
from .fionera.ux_proposals import UXProposalGenerator


GENERATOR_MAP: dict[str, dict] = {
    "yallaplays": {
        OutputType.seo_page: YallaPlaysSEOGenerator,
        OutputType.category_page: CategoryPageGenerator,
        OutputType.metadata_patch: MetadataPatchGenerator,
        OutputType.mobile_optimization: MobileOptimizer,
        OutputType.internal_linking: InternalLinkingGenerator,
        OutputType.game_recommendation: GameRecommendationGenerator,
    },
    "fionera": {
        OutputType.finance_widget: FinanceWidgetGenerator,
        OutputType.market_insight: MarketInsightGenerator,
        OutputType.watchlist_improvement: WatchlistImprovementGenerator,
        OutputType.analytics_dashboard: AnalyticsDashboardGenerator,
        OutputType.ux_proposal: UXProposalGenerator,
    },
}

METHOD_MAP: dict[str, str] = {
    OutputType.seo_page: "generate_seo_page",
    OutputType.category_page: "generate_category_page",
    OutputType.metadata_patch: "generate_metadata_patches",
    OutputType.mobile_optimization: "generate_mobile_optimizations",
    OutputType.internal_linking: "generate_internal_linking",
    OutputType.game_recommendation: "generate_recommendations",
    OutputType.finance_widget: "generate_widgets",
    OutputType.market_insight: "generate_market_insights",
    OutputType.watchlist_improvement: "generate_watchlist_improvements",
    OutputType.analytics_dashboard: "generate_dashboard_improvements",
    OutputType.ux_proposal: "generate_ux_proposals",
}


class OperationEngine:
    def __init__(self):
        Path(__file__).parent.parent / "memory" / "operations"
        self._memory = OperationMemory()
        self._previewer = PreviewGenerator()
        self._apply_bridge = ApplyBridge()

    def _get_generator(self, project: str, output_type: str) -> object | None:
        project_map = GENERATOR_MAP.get(project, {})
        for key, cls in project_map.items():
            if key == output_type or (hasattr(key, "value") and key.value == output_type):
                return cls()
        return None

    def _get_method(self, output_type: str) -> str:
        for key, method in METHOD_MAP.items():
            if key == output_type or (hasattr(key, "value") and key.value == output_type):
                return method
        return ""

    async def generate(self, project: str, output_type: str, topic: str = "", use_ai: bool = False, count: int = 1) -> dict:
        generator = self._get_generator(project, output_type)
        if not generator:
            return {"success": False, "error": f"No generator for {project}/{output_type}"}

        method_name = self._get_method(output_type)
        if not method_name:
            return {"success": False, "error": f"No method found for {output_type}"}

        method = getattr(generator, method_name, None)
        if not method:
            return {"success": False, "error": f"Method {method_name} not found on generator"}

        try:
            if output_type == "seo_page":
                category = topic or "Action Games"
                result = await method(category, use_ai=use_ai)
            elif output_type == "category_page":
                category_key = topic or "popular"
                result = await method(category_key, use_ai=use_ai)
            else:
                result = await method(use_ai=use_ai)

            if isinstance(result, tuple) and len(result) == 2:
                output, preview = result
                self._memory.save_output(output)
                self._memory.save_preview(preview)
                return {
                    "success": True,
                    "outputs": [output.model_dump()],
                    "preview_ids": [preview.id],
                    "total_generated": 1,
                    "cost_usd": output.cost_usd,
                    "message": f"Generated {output_type} for {project}",
                }
            return {"success": False, "error": "Generator returned unexpected format"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def generate_all_for_project(self, project: str, use_ai: bool = False) -> dict:
        project_map = GENERATOR_MAP.get(project, {})
        all_outputs = []
        all_previews = []
        total_cost = 0.0
        errors = []

        for output_type_enum in project_map.keys():
            output_type = output_type_enum.value if hasattr(output_type_enum, "value") else output_type_enum
            result = await self.generate(project=project, output_type=output_type, use_ai=use_ai)
            if result.get("success"):
                all_outputs.extend(result.get("outputs", []))
                all_previews.extend(result.get("preview_ids", []))
                total_cost += result.get("cost_usd", 0)
            else:
                errors.append(f"{output_type}: {result.get('error', 'unknown')}")

        batch = OperationBatch(
            project=OperationProject(project),
            output_type=OutputType.content_patch,
            outputs=[o["id"] for o in all_outputs],
            total_generated=len(all_outputs),
            total_applied=0,
            completed_at=datetime.utcnow(),
        )
        self._memory.save_batch(batch)

        return {
            "success": True,
            "batch_id": batch.id,
            "total_generated": len(all_outputs),
            "total_previews": len(all_previews),
            "total_cost_usd": round(total_cost, 6),
            "errors": errors,
            "outputs": all_outputs,
            "preview_ids": all_previews,
        }

    def get_status(self) -> dict:
        yp_analytics = self._memory.get_analytics("yallaplays")
        fi_analytics = self._memory.get_analytics("fionera")
        all_analytics = self._memory.get_analytics()
        all_outputs = self._memory.get_outputs(limit=1000)
        last_gen = sorted([o.get("created_at", "") for o in all_outputs], reverse=True)
        return {
            "status": "operational",
            "yallaplays": yp_analytics,
            "fionera": fi_analytics,
            "total_outputs": all_analytics["total_outputs"],
            "pending_apply": all_analytics["pending_count"],
            "last_generation": last_gen[0] if last_gen else None,
            "ai_active": bool(__import__("os").environ.get("OPENAI_API_KEY")),
        }

    def get_preview(self, output_id: str) -> dict | None:
        output = self._memory.get_output(output_id)
        preview = self._memory.get_preview_for_output(output_id)
        if not output or not preview:
            return None
        from .models import OperationalOutput as OO, OperationalPreview as OP
        out_obj = OO(**output)
        prev_obj = OP(**preview)
        return {
            "preview": preview,
            "output": output,
            "apply_ready": output.get("status") in ("generated", "previewed"),
            "estimated_impact": preview.get("estimated_impact", {}),
            "html": self._previewer.render_html_preview(out_obj, prev_obj),
        }

    def apply_output(self, output_id: str, dry_run: bool = True, notes: str = "") -> dict:
        output_dict = self._memory.get_output(output_id)
        if not output_dict:
            return {"success": False, "error": f"Output {output_id} not found"}
        from .models import OperationalOutput as OO
        output = OO(**output_dict)
        if dry_run:
            return self._apply_bridge.apply_dry_run(output)
        result = self._apply_bridge.apply_output(output, notes=notes)
        if result.get("success"):
            self._memory.update_output_status(output_id, "applied", {"apply_id": result.get("apply_id")})
        return result

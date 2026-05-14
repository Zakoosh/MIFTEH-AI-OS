from __future__ import annotations
import asyncio
from datetime import datetime
from pathlib import Path
import json
from .operation_engine import OperationEngine
from .preview_generator import PreviewGenerator
from .models import OperationalOutput, OperationalPreview
from ..core.config import get_config


PREVIEWS_DIR = Path(__file__).parent.parent / "memory" / "operations" / "previews"
PR_OUTPUTS_DIR = Path(__file__).parent.parent / "memory" / "operations" / "pr_outputs"
REPORTS_DIR = Path(__file__).parent.parent / "memory" / "operations" / "reports"


class ProductionRunner:
    """Runs real operational generation campaigns and saves HTML previews + PR outputs."""

    YALLAPLAYS_TASKS = [
        ("seo_page", "Action Games"),
        ("seo_page", "Sports Games"),
        ("seo_page", "Racing Games"),
        ("seo_page", "Puzzle Games"),
        ("seo_page", "Multiplayer Games"),
        ("seo_page", "Arabic Games"),
        ("category_page", "popular"),
        ("category_page", "trending"),
        ("category_page", "new"),
        ("category_page", "mobile"),
        ("metadata_patch", ""),
        ("mobile_optimization", ""),
        ("internal_linking", ""),
        ("game_recommendation", ""),
    ]

    FIONERA_TASKS = [
        ("finance_widget", ""),
        ("market_insight", ""),
        ("watchlist_improvement", ""),
        ("analytics_dashboard", ""),
        ("ux_proposal", ""),
    ]

    def __init__(self):
        self._engine = OperationEngine()
        self._previewer = PreviewGenerator()
        cfg = get_config()
        self._use_ai = cfg.openai_active or cfg.gemini_active
        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        PR_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    async def run_yallaplays_campaign(self) -> dict:
        return await self._run_campaign("yallaplays", self.YALLAPLAYS_TASKS)

    async def run_fionera_campaign(self) -> dict:
        return await self._run_campaign("fionera", self.FIONERA_TASKS)

    async def _run_campaign(self, project: str, tasks: list[tuple[str, str]]) -> dict:
        results = []
        errors = []
        total_cost = 0.0
        total_tokens = 0
        html_previews_saved = []
        pr_outputs_saved = []

        for output_type, topic in tasks:
            result = await self._engine.generate(
                project=project,
                output_type=output_type,
                topic=topic,
                use_ai=self._use_ai,
            )
            if not result.get("success"):
                errors.append(f"{output_type}/{topic or 'default'}: {result.get('error')}")
                continue

            for output_dict in result.get("outputs", []):
                results.append(output_dict)
                total_cost += output_dict.get("cost_usd", 0)
                total_tokens += output_dict.get("tokens_used", 0)

                preview_data = self._engine.get_preview(output_dict["id"])
                if preview_data:
                    html = preview_data.get("html", "")
                    if html:
                        fname = f"{project}_{output_type}_{output_dict['id'][:8]}.html"
                        fpath = PREVIEWS_DIR / fname
                        fpath.write_text(html)
                        html_previews_saved.append(str(fpath.name))

                pr_output = self._build_pr_output(output_dict, project)
                if pr_output:
                    fname = f"pr_{project}_{output_type}_{output_dict['id'][:8]}.json"
                    fpath = PR_OUTPUTS_DIR / fname
                    fpath.write_text(json.dumps(pr_output, indent=2, default=str))
                    pr_outputs_saved.append(str(fpath.name))

        report = {
            "project": project,
            "campaign_run_at": datetime.utcnow().isoformat(),
            "ai_used": self._use_ai,
            "total_outputs": len(results),
            "total_errors": len(errors),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "html_previews_saved": len(html_previews_saved),
            "pr_outputs_saved": len(pr_outputs_saved),
            "preview_files": html_previews_saved,
            "pr_files": pr_outputs_saved,
            "errors": errors,
            "outputs_summary": [
                {
                    "id": o["id"],
                    "type": o["output_type"],
                    "title": o["title"],
                    "status": o["status"],
                    "ai_generated": o["ai_generated"],
                    "cost_usd": o["cost_usd"],
                    "patch_files_count": len(o.get("patch_files", [])),
                }
                for o in results
            ],
        }
        report_path = REPORTS_DIR / f"campaign_{project}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report, indent=2, default=str))
        return report

    def _build_pr_output(self, output_dict: dict, project: str) -> dict:
        patch_files = output_dict.get("patch_files", [])
        if not patch_files:
            return {}
        output_type = output_dict.get("output_type", "")
        title = output_dict.get("title", "AI-Generated improvement")
        description = output_dict.get("description", "")
        return {
            "pr_ready": True,
            "output_id": output_dict["id"],
            "project": project,
            "output_type": output_type,
            "suggested_branch": f"ai/{output_type}/{output_dict['id'][:8]}",
            "suggested_title": f"[AI] {title}",
            "suggested_description": f"{description}\n\n**Generated by MIFTEH AI OS**\n- Dashboard: https://yallaplays.com/admin/os\n- Output ID: {output_dict['id']}\n- AI Generated: {output_dict.get('ai_generated', False)}\n- Risk Level: {output_dict.get('risk_level', 'low')}\n\n**Files Changed:**\n" + "\n".join(f"- `{p['file_path']}`" for p in patch_files),
            "files": [
                {
                    "path": p.get("file_path"),
                    "operation": p.get("operation", "create_or_update"),
                    "description": p.get("description", ""),
                    "content": p.get("content", ""),
                }
                for p in patch_files
            ],
            "total_files": len(patch_files),
            "safety": {
                "rollback_available": output_dict.get("rollback_available", True),
                "risk_level": output_dict.get("risk_level", "low"),
                "requires_review": True,
                "auto_merge": False,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def run_full_production_cycle(self) -> dict:
        yp_result = await self.run_yallaplays_campaign()
        fi_result = await self.run_fionera_campaign()
        summary = {
            "cycle_run_at": datetime.utcnow().isoformat(),
            "dashboard_url": "https://yallaplays.com/admin/os",
            "ai_active": self._use_ai,
            "yallaplays": {
                "outputs": yp_result["total_outputs"],
                "html_previews": yp_result["html_previews_saved"],
                "pr_outputs": yp_result["pr_outputs_saved"],
                "cost_usd": yp_result["total_cost_usd"],
                "tokens": yp_result["total_tokens"],
                "errors": yp_result["total_errors"],
            },
            "fionera": {
                "outputs": fi_result["total_outputs"],
                "html_previews": fi_result["html_previews_saved"],
                "pr_outputs": fi_result["pr_outputs_saved"],
                "cost_usd": fi_result["total_cost_usd"],
                "tokens": fi_result["total_tokens"],
                "errors": fi_result["total_errors"],
            },
            "totals": {
                "outputs": yp_result["total_outputs"] + fi_result["total_outputs"],
                "previews": yp_result["html_previews_saved"] + fi_result["html_previews_saved"],
                "pr_outputs": yp_result["pr_outputs_saved"] + fi_result["pr_outputs_saved"],
                "cost_usd": round(yp_result["total_cost_usd"] + fi_result["total_cost_usd"], 6),
            },
            "yallaplays_detail": yp_result,
            "fionera_detail": fi_result,
        }
        summary_path = REPORTS_DIR / f"full_cycle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        return summary

    def get_latest_report(self) -> dict | None:
        reports = sorted(REPORTS_DIR.glob("full_cycle_*.json"), reverse=True)
        if not reports:
            return None
        try:
            return json.loads(reports[0].read_text())
        except Exception:
            return None

    def list_html_previews(self) -> list[dict]:
        previews = []
        for f in sorted(PREVIEWS_DIR.glob("*.html"), reverse=True)[:50]:
            previews.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "url": f"/operations/preview-files/{f.name}",
            })
        return previews

    def list_pr_outputs(self) -> list[dict]:
        outputs = []
        for f in sorted(PR_OUTPUTS_DIR.glob("*.json"), reverse=True)[:50]:
            try:
                data = json.loads(f.read_text())
                outputs.append({
                    "filename": f.name,
                    "output_id": data.get("output_id", ""),
                    "project": data.get("project", ""),
                    "output_type": data.get("output_type", ""),
                    "suggested_branch": data.get("suggested_branch", ""),
                    "total_files": data.get("total_files", 0),
                    "pr_ready": data.get("pr_ready", False),
                })
            except Exception:
                pass
        return outputs

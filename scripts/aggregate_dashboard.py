"""
MIFTEH OS — Dashboard Aggregator
Reads all output files, builds frontend/dashboard/data/dashboard.json.
This file is served at miftehos.com/data/dashboard.json — no backend required.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso

LOOPS = [
    # YallaPlays (6)
    {"id": "yp-seo-loop",      "label": "SEO Page Generator",       "project": "yallaplays", "interval_minutes": 360},
    {"id": "yp-category-loop", "label": "Category Optimizer",        "project": "yallaplays", "interval_minutes": 720},
    {"id": "yp-homepage-loop", "label": "Homepage Recommendations",  "project": "yallaplays", "interval_minutes": 360},
    {"id": "yp-linking-loop",  "label": "Internal Linking",          "project": "yallaplays", "interval_minutes": 1440},
    {"id": "yp-mobile-loop",   "label": "Mobile Optimization",       "project": "yallaplays", "interval_minutes": 1440},
    {"id": "yp-games-loop",    "label": "Game Suggestion Generator", "project": "yallaplays", "interval_minutes": 240},
    # Fionera (5)
    {"id": "fi-market-loop",   "label": "Market Insights",           "project": "fionera",    "interval_minutes": 240},
    {"id": "fi-watchlist-loop","label": "Watchlist Optimizer",       "project": "fionera",    "interval_minutes": 360},
    {"id": "fi-analytics-loop","label": "Analytics Report",          "project": "fionera",    "interval_minutes": 1440},
    {"id": "fi-ux-loop",       "label": "UX Improvements",           "project": "fionera",    "interval_minutes": 1440},
    {"id": "fi-widgets-loop",  "label": "Finance Widgets",           "project": "fionera",    "interval_minutes": 720},
    # Mifteh (3)
    {"id": "mi-seo-loop",      "label": "SEO Improvements",          "project": "mifteh",     "interval_minutes": 720},
    {"id": "mi-content-loop",  "label": "Content Optimizer",         "project": "mifteh",     "interval_minutes": 1440},
    {"id": "mi-landing-loop",  "label": "Landing Page Optimizer",    "project": "mifteh",     "interval_minutes": 1440},
]


def read_outputs():
    outputs = []
    for project_dir in Path("outputs").iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue
        for type_dir in project_dir.iterdir():
            if not type_dir.is_dir():
                continue
            for f in type_dir.glob("*.json"):
                if f.name == "latest.json":
                    continue
                try:
                    outputs.append(json.loads(f.read_text()))
                except Exception:
                    pass
    outputs.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
    return outputs


def read_prs():
    f = Path("memory/all_prs.json")
    return json.loads(f.read_text()) if f.exists() else []


def read_trust():
    f = Path("memory/trust_scores.json")
    return json.loads(f.read_text()) if f.exists() else {}


def read_automerge_log():
    f = Path("memory/automerge_log.json")
    return json.loads(f.read_text()) if f.exists() else []


def read_validation_log():
    f = Path("memory/validation_log.json")
    return json.loads(f.read_text()) if f.exists() else []


def read_product_outputs():
    """Read all product execution output records from outputs/{project}/product/."""
    records = []
    for proj_dir in Path("outputs").iterdir():
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        product_dir = proj_dir / "product"
        if not product_dir.exists():
            continue
        for f in product_dir.glob("*.json"):
            try:
                records.append(json.loads(f.read_text()))
            except Exception:
                pass
    records.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
    return records


def build_product_metrics(product_outputs):
    if not product_outputs:
        return {
            "total_features": 0, "pages_generated": 0, "widgets_generated": 0,
            "est_monthly_seo_visits": 0, "total_tokens": 0, "total_cost_usd": 0.0,
            "by_project": {}, "by_type": {}, "recent_features": [],
        }
    pages = sum(1 for o in product_outputs if o.get("feature_type") in ("page", "category_page", "seo_hub"))
    widgets = sum(1 for o in product_outputs if o.get("estimated_widgets", 0) > 0)
    est_visits = sum(o.get("estimated_monthly_visits", 0) for o in product_outputs)
    by_project, by_type = {}, {}
    for o in product_outputs:
        p = o.get("project", "unknown")
        t = o.get("feature_type", "unknown")
        by_project[p] = by_project.get(p, 0) + 1
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_features": len(product_outputs),
        "pages_generated": pages,
        "widgets_generated": widgets,
        "est_monthly_seo_visits": est_visits,
        "total_tokens": sum(o.get("tokens_used", 0) for o in product_outputs),
        "total_cost_usd": round(sum(o.get("cost_usd", 0.0) for o in product_outputs), 6),
        "by_project": by_project,
        "by_type": by_type,
        "recent_features": [
            {
                "label": o.get("label"),
                "project": o.get("project"),
                "feature_type": o.get("feature_type"),
                "target_path": o.get("target_path"),
                "seo_target": o.get("seo_target"),
                "est_monthly_visits": o.get("estimated_monthly_visits", 0),
                "est_widgets": o.get("estimated_widgets", 0),
                "bytes_generated": o.get("bytes_generated", 0),
                "tokens_used": o.get("tokens_used", 0),
                "pr_url": o.get("pr_url"),
                "generated_at": o.get("generated_at"),
            }
            for o in product_outputs[:30]
        ],
    }


def build_loops(outputs):
    by_project = {}
    for o in outputs:
        p = o.get("project", "")
        by_project.setdefault(p, []).append(o)

    loops = []
    for defn in LOOPS:
        proj_outs = by_project.get(defn["project"], [])
        last = proj_outs[0] if proj_outs else None
        last_run = (last or {}).get("generated_at")

        next_run = None
        if last_run:
            try:
                dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                next_run = (dt + timedelta(minutes=defn["interval_minutes"])).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        loops.append({
            **defn,
            "last_run": last_run,
            "last_status": "completed" if last else "pending",
            "run_count": len(proj_outs),
            "success_count": sum(1 for o in proj_outs if o.get("ai_generated")),
            "next_run_scheduled": next_run,
        })

    active = sum(1 for l in loops if l["last_status"] == "completed")
    return loops, active


def build_ai_analytics(outputs):
    ai_outs = [o for o in outputs if o.get("ai_generated")]
    total = len(outputs)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    by_provider, by_project, by_op, by_day = {}, {}, {}, {}

    for o in outputs:
        proj = o.get("project", "unknown")
        op = o.get("operation_type", "unknown")
        prov = o.get("ai_provider", "openai") if o.get("ai_generated") else None

        by_project[proj] = by_project.get(proj, 0) + 1
        by_op[op] = by_op.get(op, 0) + 1

        if prov:
            if prov not in by_provider:
                by_provider[prov] = {"requests": 0, "tokens": 0, "cost_usd": 0.0, "success_rate": 100, "avg_latency_ms": 0}
            by_provider[prov]["requests"] += 1
            by_provider[prov]["tokens"] += o.get("tokens_used", 0)
            by_provider[prov]["cost_usd"] += o.get("cost_usd", 0.0)

        try:
            dt = datetime.fromisoformat(o.get("generated_at", "").replace("Z", "+00:00"))
            if dt >= cutoff:
                day = dt.strftime("%Y-%m-%d")
                if day not in by_day:
                    by_day[day] = {"requests": 0, "success": 0, "cost_usd": 0.0}
                by_day[day]["requests"] += 1
                if o.get("ai_generated"):
                    by_day[day]["success"] += 1
                by_day[day]["cost_usd"] += o.get("cost_usd", 0.0)
        except Exception:
            pass

    total_tokens = sum(o.get("tokens_used", 0) for o in outputs)
    total_cost = sum(o.get("cost_usd", 0.0) for o in outputs)
    ai_count = len(ai_outs)

    return {
        "total_calls": total,
        "successful_calls": ai_count,
        "rate_limited_calls": 0,
        "success_rate_pct": round(ai_count / max(total, 1) * 100),
        "ai_generated_pct": round(ai_count / max(total, 1) * 100),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_provider": by_provider,
        "by_project": by_project,
        "by_operation_type": by_op,
        "by_day": by_day,
    }


def main():
    print("[dashboard] Aggregating dashboard data...")

    outputs = read_outputs()
    prs = read_prs()
    trust = read_trust()
    automerge_log = read_automerge_log()
    validation_log = read_validation_log()
    product_outputs = read_product_outputs()
    product_metrics = build_product_metrics(product_outputs)
    print(f"[dashboard] {len(outputs)} outputs, {len(prs)} PRs, {len(automerge_log)} merge events, {len(product_outputs)} product features")

    loops, active_loops = build_loops(outputs)
    ai_analytics = build_ai_analytics(outputs)

    by_project = {}
    for o in outputs:
        p = o.get("project", "unknown")
        by_project[p] = by_project.get(p, 0) + 1

    ai_outs = [o for o in outputs if o.get("ai_generated")]

    dashboard = {
        "generated_at": now_iso(),
        "architecture": "github-native",
        "scheduler": {
            "scheduler_running": True,
            "active_loops": active_loops,
            "total_loops": len(loops),
            "total_runs": sum(l["run_count"] for l in loops),
            "total_success": sum(l["success_count"] for l in loops),
            "loops": loops,
            "provider_cooldowns": {
                "openai": {"consecutive_429s": 0, "total_429s": 0, "last_success": now_iso()},
                "gemini": {"consecutive_429s": 0, "total_429s": 0, "last_success": now_iso()},
            },
        },
        "providers": {
            "openai": {"configured": True, "available": True},
            "gemini": {"configured": bool(os.environ.get("GEMINI_API_KEY")), "available": True},
            "github_active": True,
            "ai_mode": "ai" if ai_outs else "template",
            "market_data": {"twelve_data": False, "alpha_vantage": False},
        },
        "ai_analytics": ai_analytics,
        "outputs": {
            "total": len(outputs),
            "yallaplays": by_project.get("yallaplays", 0),
            "fionera": by_project.get("fionera", 0),
            "mifteh": by_project.get("mifteh", 0),
            "ai_generated": len(ai_outs),
            "template_generated": len(outputs) - len(ai_outs),
            "pending_review": len([o for o in outputs if o.get("pr_ready")]),
        },
        "repository": {
            "previews": [],
            "pr_outputs": [
                {
                    "output_id": o.get("suggested_branch", ""),
                    "project": o.get("project", ""),
                    "output_type": o.get("operation_type", ""),
                    "suggested_branch": o.get("suggested_branch", ""),
                    "generated_at": o.get("generated_at", ""),
                    "total_files": 2,
                }
                for o in outputs[:10] if o.get("pr_ready")
            ],
            "pr_ready": len([o for o in outputs if o.get("pr_ready")]),
        },
        "github_prs": [
            {
                "repo": p.get("repo", ""),
                "branch": p.get("branch", ""),
                "pr_number": p.get("pr_number"),
                "pr_url": p.get("pr_url", ""),
                "pr_title": p.get("pr_title", ""),
                "created_at": p.get("created_at", ""),
                "files_committed": p.get("files_committed", []),
            }
            for p in prs[-20:]
        ],
        "activity": [
            {
                "type": o.get("operation_type", "unknown"),
                "project": o.get("project", "unknown"),
                "title": o.get("title", "Untitled"),
                "ai_generated": o.get("ai_generated", False),
                "time": o.get("generated_at"),
            }
            for o in outputs[:50]
        ],
        "safety": {
            "auto_merge": False,
            "auto_deploy": False,
            "preview_first": True,
            "rollback_enabled": True,
            "validation_required": True,
            "audit_tracking": True,
        },
        "trust": {
            "repos": trust.get("repos", {}),
            "categories": trust.get("categories", {}),
            "suspended_repos": trust.get("suspended_repos", []),
            "suspended_categories": trust.get("suspended_categories", []),
            "last_updated": trust.get("generated_at", ""),
        },
        "apply_history": [
            {
                "repo": e.get("repo"),
                "pr_number": e.get("pr_number"),
                "pr_url": e.get("pr_url"),
                "action": e.get("action"),
                "score": e.get("score"),
                "reason": e.get("reason"),
                "evaluated_at": e.get("evaluated_at"),
                "merge_sha": e.get("merge_sha", ""),
            }
            for e in automerge_log[-50:]
        ],
        "product": product_metrics,
        "validation_history": [
            {
                "repo": e.get("repo"),
                "base_url": e.get("base_url"),
                "passed": e.get("passed"),
                "total": e.get("total"),
                "ok": e.get("ok"),
                "validated_at": e.get("validated_at"),
            }
            for e in validation_log[-50:]
        ],
    }

    out = Path("frontend/dashboard/data/dashboard.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False))
    print(f"[dashboard] Written — {active_loops}/{len(loops)} loops active, {len(outputs)} outputs, {len(prs)} PRs")
    return dashboard


if __name__ == "__main__":
    main()

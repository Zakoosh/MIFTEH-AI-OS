"""
Continuous Mission Runner
Manages recurring autonomous missions: seo-growth, monetization-growth,
indexing-repair, game-expansion, ui-modernization.
Each mission is a sequenced pipeline of growth actions with gating and reporting.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

from scripts.intelligence.registry import get_project, get_all_active_projects
from scripts.intelligence.report_store import save, load_latest, REPORTS_ROOT

REPORT_TYPE = "missions"
MISSIONS_STATE_FILE = REPORTS_ROOT / "missions" / "active_missions.json"


# ──────────────────────────────────────────────────────────────────────────────
# Mission definitions
# ──────────────────────────────────────────────────────────────────────────────

MISSION_CATALOG = {

    "seo-growth": {
        "name": "SEO Growth Mission",
        "description": "Improve search visibility through technical SEO, content, and schema",
        "cadence": "weekly",
        "priority": "high",
        "steps": [
            {
                "id": "seo_audit",
                "name": "Full SEO Audit",
                "action": "analyze_seo",
                "gate": None,
                "description": "Run deep SEO analysis across all priority pages",
            },
            {
                "id": "indexing_check",
                "name": "Indexing Status Check",
                "action": "analyze_indexing",
                "gate": None,
                "description": "Verify sitemap freshness, orphan pages, and crawlability",
            },
            {
                "id": "keyword_analysis",
                "name": "Keyword Opportunity Analysis",
                "action": "analyze_traffic",
                "gate": None,
                "description": "Identify quick-win keywords and content gaps",
            },
            {
                "id": "content_plan",
                "name": "Content Expansion Plan",
                "action": "generate_content_plan",
                "gate": "keyword_analysis",
                "description": "Generate SEO page specs for top keyword opportunities",
            },
            {
                "id": "report",
                "name": "SEO Growth Report",
                "action": "generate_report",
                "gate": None,
                "description": "Compile and save SEO growth report",
            },
        ],
    },

    "monetization-growth": {
        "name": "Monetization Growth Mission",
        "description": "Maximize AdSense revenue through coverage, placement, and format optimization",
        "cadence": "weekly",
        "priority": "high",
        "steps": [
            {
                "id": "revenue_analysis",
                "name": "Revenue Intelligence Analysis",
                "action": "analyze_revenue",
                "gate": None,
                "description": "Analyze AdSense presence, coverage, RPM estimates",
            },
            {
                "id": "monetization_audit",
                "name": "Monetization Optimization Audit",
                "action": "optimize_monetization",
                "gate": None,
                "description": "Check CLS, ad density, placement quality, policy compliance",
            },
            {
                "id": "ab_test_setup",
                "name": "A/B Tests Setup",
                "action": "run_ab_tests",
                "gate": None,
                "description": "Create/update A/B tests for ad placements and CTAs",
            },
            {
                "id": "report",
                "name": "Monetization Growth Report",
                "action": "generate_report",
                "gate": None,
                "description": "Compile monetization recommendations and revenue forecasts",
            },
        ],
    },

    "indexing-repair": {
        "name": "Indexing Repair Mission",
        "description": "Fix indexing issues: orphan pages, noindex, broken links, sitemap staleness",
        "cadence": "daily",
        "priority": "high",
        "steps": [
            {
                "id": "indexing_analysis",
                "name": "Deep Indexing Analysis",
                "action": "analyze_indexing",
                "gate": None,
                "description": "Check all pages for indexability, noindex, and crawl issues",
            },
            {
                "id": "live_validation",
                "name": "Live Production Validation",
                "action": "validate_live",
                "gate": None,
                "description": "Verify all routes are live and returning 200",
            },
            {
                "id": "sitemap_validation",
                "name": "Sitemap Freshness Check",
                "action": "validate_sitemap",
                "gate": None,
                "description": "Verify sitemap.xml is fresh, complete, and submitted",
            },
            {
                "id": "report",
                "name": "Indexing Repair Report",
                "action": "generate_report",
                "gate": None,
                "description": "Generate actionable repair plan",
            },
        ],
    },

    "game-expansion": {
        "name": "Game Expansion Mission",
        "description": "Automatically generate new HTML5 games with SEO pages and monetization",
        "cadence": "monthly",
        "priority": "medium",
        "steps": [
            {
                "id": "gap_analysis",
                "name": "Game Category Gap Analysis",
                "action": "analyze_traffic",
                "gate": None,
                "description": "Identify game categories with search demand but no content",
            },
            {
                "id": "game_generation",
                "name": "Generate New Games",
                "action": "generate_games",
                "gate": None,
                "description": "Create HTML5 games, thumbnails, and metadata",
            },
            {
                "id": "landing_pages",
                "name": "Generate Game Landing Pages",
                "action": "generate_content_plan",
                "gate": "game_generation",
                "description": "Create SEO-optimized landing pages for all new games",
            },
            {
                "id": "report",
                "name": "Game Expansion Report",
                "action": "generate_report",
                "gate": None,
                "description": "Document new games, pages, and expected SEO impact",
            },
        ],
    },

    "ui-modernization": {
        "name": "UI Modernization Mission",
        "description": "Continuously test and improve UI for conversion and engagement",
        "cadence": "monthly",
        "priority": "medium",
        "steps": [
            {
                "id": "ab_analysis",
                "name": "A/B Test Results Analysis",
                "action": "run_ab_tests",
                "gate": None,
                "description": "Analyze all active A/B tests for statistical significance",
            },
            {
                "id": "performance_check",
                "name": "Performance & CLS Check",
                "action": "optimize_monetization",
                "gate": None,
                "description": "Check Core Web Vitals and layout stability",
            },
            {
                "id": "content_audit",
                "name": "Content Quality Audit",
                "action": "analyze_seo",
                "gate": None,
                "description": "Check page quality scores and SERP appearance",
            },
            {
                "id": "report",
                "name": "UI Modernization Report",
                "action": "generate_report",
                "gate": None,
                "description": "Compile UI improvement recommendations with priority order",
            },
        ],
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Mission state management
# ──────────────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    MISSIONS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MISSIONS_STATE_FILE.exists():
        try:
            return json.loads(MISSIONS_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    MISSIONS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MISSIONS_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ──────────────────────────────────────────────────────────────────────────────
# Step executors
# ──────────────────────────────────────────────────────────────────────────────

def _execute_step(action: str, project_id: str) -> dict:
    """Execute a mission step by action name. Returns result dict."""
    try:
        if action == "analyze_seo":
            from scripts.intelligence.seo_engine import analyze_project
            r = analyze_project(project_id)
            return {"ok": True, "score": r.get("overall_seo_score"), "issues": r.get("total_issues")}

        elif action == "analyze_indexing":
            from scripts.growth.indexing_intelligence import analyze_project
            r = analyze_project(project_id)
            return {"ok": True, "score": r.get("indexing_score"), "orphans": r.get("orphans", {}).get("orphan_count", 0)}

        elif action == "analyze_revenue":
            from scripts.growth.revenue_intelligence import analyze_project
            r = analyze_project(project_id)
            return {"ok": True, "score": r.get("scoring", {}).get("monetization_score"), "coverage": r.get("adsense", {}).get("coverage_pct")}

        elif action == "optimize_monetization":
            from scripts.growth.monetization_optimizer import optimize_project
            r = optimize_project(project_id)
            return {"ok": True, "score": r.get("optimization_score"), "critical": r.get("critical_issues")}

        elif action == "analyze_traffic":
            from scripts.growth.traffic_intelligence import analyze_project
            r = analyze_project(project_id)
            return {"ok": True, "serp_score": r.get("serp", {}).get("avg_serp_score"), "quick_wins": len(r.get("keyword_opportunities", {}).get("quick_wins", []))}

        elif action == "validate_live":
            from scripts.intelligence.live_validator import validate_project
            r = validate_project(project_id)
            return {"ok": r.get("overall_ok"), "health_score": r.get("health_score")}

        elif action == "validate_sitemap":
            from scripts.growth.indexing_intelligence import analyze_sitemap
            p = get_project(project_id)
            r = analyze_sitemap(p["domain"])
            return {"ok": r.get("ok"), "url_count": r.get("total_urls"), "freshness_days": r.get("freshness_days")}

        elif action == "generate_content_plan":
            from scripts.growth.content_engine import generate_content_plan
            r = generate_content_plan(project_id)
            return {"ok": True, "pages": r.get("plan_summary", {}).get("total_pages_to_create", 0)}

        elif action == "generate_games":
            from scripts.growth.game_factory import generate_batch
            from scripts.intelligence.registry import get_adsense_publisher
            pub = get_adsense_publisher(project_id) or "ca-pub-1206965892808259"
            r = generate_batch(project_id, publisher_id=pub)
            return {"ok": True, "generated": r.get("generated"), "errors": r.get("errors")}

        elif action == "run_ab_tests":
            from scripts.growth.ab_testing import run_full_suite
            r = run_full_suite(project_id)
            return {"ok": True, "tests": r.get("tests_run"), "top_uplift": r.get("top_opportunity", [None, 0])[1] if r.get("top_opportunity") else 0}

        elif action == "generate_report":
            return {"ok": True, "note": "Report step — data collected by prior steps"}

        else:
            return {"ok": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Mission execution
# ──────────────────────────────────────────────────────────────────────────────

def run_mission(mission_id: str, project_id: str, force: bool = False) -> dict:
    """Execute a mission for a project. Returns the mission result."""
    mission_config = MISSION_CATALOG.get(mission_id)
    if not mission_config:
        return {"ok": False, "error": f"Unknown mission: {mission_id}. Available: {list(MISSION_CATALOG)}"}

    state = _load_state()
    state_key = f"{project_id}:{mission_id}"

    # Check if mission ran recently (skip if same-day, unless forced)
    last_run = state.get(state_key, {}).get("last_run")
    if not force and last_run:
        try:
            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            cadence_hours = {"daily": 20, "weekly": 160, "monthly": 700}.get(mission_config["cadence"], 20)
            if age_hours < cadence_hours:
                return {
                    "ok": True,
                    "skipped": True,
                    "reason": f"Mission ran {age_hours:.1f}h ago (cadence: {mission_config['cadence']})",
                    "last_run": last_run,
                }
        except Exception:
            pass

    start_time = datetime.now(timezone.utc)
    step_results = []
    completed_steps = set()
    failed = False

    print(f"\n[MISSION] {mission_config['name']} → project: {project_id}")

    for step in mission_config["steps"]:
        step_id = step["id"]
        action = step["action"]
        gate = step.get("gate")

        # Check gate
        if gate and gate not in completed_steps:
            step_results.append({
                "step_id": step_id,
                "name": step["name"],
                "status": "skipped",
                "reason": f"Gate '{gate}' not completed",
            })
            continue

        print(f"  [{step_id}] {step['name']}...")
        step_start = time.time()
        result = _execute_step(action, project_id)
        elapsed = round(time.time() - step_start, 1)

        entry = {
            "step_id": step_id,
            "name": step["name"],
            "action": action,
            "status": "passed" if result.get("ok") else "failed",
            "elapsed_seconds": elapsed,
            "result": result,
        }
        step_results.append(entry)

        if result.get("ok"):
            completed_steps.add(step_id)
            print(f"    ✓ {elapsed}s — {json.dumps({k: v for k, v in result.items() if k != 'ok'})}")
        else:
            failed = True
            print(f"    ✗ {result.get('error', 'failed')}")

    elapsed_total = round((datetime.now(timezone.utc) - start_time).total_seconds(), 1)

    mission_result = {
        "mission_id": mission_id,
        "project_id": project_id,
        "name": mission_config["name"],
        "status": "failed" if failed else "completed",
        "started_at": start_time.isoformat(),
        "elapsed_seconds": elapsed_total,
        "steps_total": len(mission_config["steps"]),
        "steps_passed": len(completed_steps),
        "steps": step_results,
    }

    # Update state
    state[state_key] = {
        "last_run": start_time.isoformat(),
        "last_status": mission_result["status"],
        "steps_passed": len(completed_steps),
    }
    _save_state(state)

    save(REPORT_TYPE, project_id, mission_result)
    return mission_result


def run_all_missions(project_id: str, mission_ids: Optional[list] = None, force: bool = False) -> dict:
    """Run all (or selected) missions for a project."""
    ids = mission_ids or list(MISSION_CATALOG.keys())
    results = {}

    for mid in ids:
        print(f"\n{'═'*50}")
        result = run_mission(mid, project_id, force=force)
        results[mid] = result

    summary = {
        "project_id": project_id,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "missions_run": len(results),
        "missions_completed": sum(1 for r in results.values() if r.get("status") == "completed"),
        "missions_failed": sum(1 for r in results.values() if r.get("status") == "failed"),
        "missions_skipped": sum(1 for r in results.values() if r.get("skipped")),
        "results": results,
    }
    save(REPORT_TYPE, project_id, summary)
    return summary


def list_missions() -> dict:
    """List all available missions with their configs."""
    return {
        mid: {
            "name": m["name"],
            "description": m["description"],
            "cadence": m["cadence"],
            "priority": m["priority"],
            "steps": len(m["steps"]),
        }
        for mid, m in MISSION_CATALOG.items()
    }


def mission_status(project_id: str) -> dict:
    """Show current mission status for a project."""
    state = _load_state()
    now = datetime.now(timezone.utc)
    status = {}

    for mid, config in MISSION_CATALOG.items():
        state_key = f"{project_id}:{mid}"
        entry = state.get(state_key, {})
        last_run = entry.get("last_run")
        age_hours = None
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                age_hours = round((now - last_dt).total_seconds() / 3600, 1)
            except Exception:
                pass

        cadence_hours = {"daily": 24, "weekly": 168, "monthly": 720}.get(config["cadence"], 24)
        due = age_hours is None or age_hours >= cadence_hours

        status[mid] = {
            "name": config["name"],
            "cadence": config["cadence"],
            "last_run": last_run,
            "age_hours": age_hours,
            "last_status": entry.get("last_status"),
            "due_now": due,
        }

    return status


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m scripts.growth.mission_runner <project_id> [mission_id] [--force]")
        print("\nAvailable missions:")
        for mid, m in list_missions().items():
            print(f"  {mid:25} {m['cadence']:10} {m['description']}")
        sys.exit(0)

    pid = args[0]
    force = "--force" in args
    mission = next((a for a in args[1:] if not a.startswith("--")), None)

    if mission == "status":
        print(json.dumps(mission_status(pid), indent=2))
    elif mission:
        r = run_mission(mission, pid, force=force)
        print(json.dumps({k: v for k, v in r.items() if k != "steps"}, indent=2))
    else:
        r = run_all_missions(pid, force=force)
        print(json.dumps({k: v for k, v in r.items() if k != "results"}, indent=2))

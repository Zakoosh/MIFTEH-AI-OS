"""
MIFTEH OS — Execution Priority Engine
Scores every decision in the autonomous queue using multi-factor analysis,
reorders the queue, and applies execution mode configuration.

Execution Modes:
  safe         — review-heavy, low-risk, trust ≥85, QA ≥75
  balanced     — standard automation with review, trust ≥70, QA ≥60
  aggressive   — fast deployment, high automation, trust ≥50, QA ≥50
  experimental — A/B testing + rapid iteration, trust ≥40, QA ≥45
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso  # noqa: F401 — ai_client also available for future AI calls

MEMORY_DIR = Path("memory")

# Factor weights — must sum to 1.0
SCORE_WEIGHTS = {
    "roi":                    0.25,
    "seo_impact":             0.20,
    "revenue_impact":         0.20,
    "ux_impact":              0.10,
    "implementation_ease":    0.10,  # inverse of complexity
    "deployment_safety":      0.05,  # inverse of risk
    "confidence":             0.05,
    "historical_success":     0.05,
}

EXECUTION_MODES = {
    "safe": {
        "trust_threshold": 85,
        "qa_gate": 75,
        "max_missions_per_cycle": 2,
        "draft_prs_only": True,
        "description": "Review-heavy, low-risk execution",
        "auto_merge_threshold": 95,
    },
    "balanced": {
        "trust_threshold": 70,
        "qa_gate": 60,
        "max_missions_per_cycle": 3,
        "draft_prs_only": False,
        "description": "Standard automation with review gates",
        "auto_merge_threshold": 90,
    },
    "aggressive": {
        "trust_threshold": 50,
        "qa_gate": 50,
        "max_missions_per_cycle": 5,
        "draft_prs_only": False,
        "description": "Fast deployment with high automation",
        "auto_merge_threshold": 80,
    },
    "experimental": {
        "trust_threshold": 40,
        "qa_gate": 45,
        "max_missions_per_cycle": 8,
        "draft_prs_only": False,
        "description": "A/B testing and rapid experimentation",
        "auto_merge_threshold": 75,
    },
}

FEATURE_TYPE_SEO_SCORES = {
    "seo_page": 90, "seo_hub": 85, "category_page": 75,
    "optimization": 60, "content": 55, "widget": 30,
}

FEATURE_TYPE_EASE_SCORES = {
    "widget": 85, "content": 80, "optimization": 75,
    "seo_page": 65, "category_page": 60, "seo_hub": 55,
}

SOURCE_CONFIDENCE = {
    "manual": 92, "analytics_intelligence": 85, "strategy_engine": 82,
    "roadmap": 78, "swarm": 72, "market_intelligence": 65, "experiment": 60,
}

REPO_MAP = {
    "yallaplays": "Zakoosh/Yallaplays",
    "fionera": "Zakoosh/fionera",
    "mifteh": "Zakoosh/mifteh-main-site",
}


def load_intelligence() -> dict:
    sources = {}
    for name, path in [
        ("revenue", "memory/revenue_report.json"),
        ("trust", "memory/trust_scores.json"),
        ("memory_summary", "memory/memory_summary.json"),
    ]:
        f = Path(path)
        if f.exists():
            try:
                sources[name] = json.loads(f.read_text())
            except Exception:
                pass
    return sources


def score_decision(decision: dict, intel: dict) -> dict:
    project = decision.get("project", "")
    feature_type = decision.get("type", decision.get("feature_type", "page"))

    # ROI — based on average portfolio ROI for this project
    proj_revenue = intel.get("revenue", {}).get("projects", {}).get(project, {})
    avg_roi = proj_revenue.get("portfolio_roi", 10)
    roi_score = min(100.0, (avg_roi / 40) * 100)

    # SEO impact
    seo_score = float(FEATURE_TYPE_SEO_SCORES.get(feature_type, 50))

    # Revenue impact — normalize $1000/mo = 100
    total_value = proj_revenue.get("total_estimated_value_usd", 0)
    revenue_score = min(100.0, total_value / 10)

    # UX impact
    ux_score = 70.0 if feature_type in ("page", "seo_page", "seo_hub", "category_page") else 40.0

    # Implementation ease (inverse of complexity)
    ease_score = float(FEATURE_TYPE_EASE_SCORES.get(feature_type, 60))

    # Deployment safety (inverse of risk) — based on trust score
    trust_repos = intel.get("trust", {}).get("repos", {})
    repo = REPO_MAP.get(project, "")
    trust_val = trust_repos.get(repo, {}).get("score", 50) if trust_repos else 50
    safety_score = float(trust_val)

    # Confidence from decision source
    source = decision.get("source", "")
    confidence_score = float(SOURCE_CONFIDENCE.get(source, 60))

    # Historical success rate
    mem = intel.get("memory_summary", {})
    hist_score = float(mem.get("success_rate_pct", 50))

    composite = (
        roi_score        * SCORE_WEIGHTS["roi"] +
        seo_score        * SCORE_WEIGHTS["seo_impact"] +
        revenue_score    * SCORE_WEIGHTS["revenue_impact"] +
        ux_score         * SCORE_WEIGHTS["ux_impact"] +
        ease_score       * SCORE_WEIGHTS["implementation_ease"] +
        safety_score     * SCORE_WEIGHTS["deployment_safety"] +
        confidence_score * SCORE_WEIGHTS["confidence"] +
        hist_score       * SCORE_WEIGHTS["historical_success"]
    )

    return {
        **decision,
        "priority_score": round(composite, 1),
        "score_breakdown": {
            "roi":                  round(roi_score, 1),
            "seo_impact":           round(seo_score, 1),
            "revenue_impact":       round(revenue_score, 1),
            "ux_impact":            round(ux_score, 1),
            "implementation_ease":  round(ease_score, 1),
            "deployment_safety":    round(safety_score, 1),
            "confidence":           round(confidence_score, 1),
            "historical_success":   round(hist_score, 1),
        },
    }


def reorder_queue(mode: str = "balanced") -> dict:
    mode_config = EXECUTION_MODES.get(mode, EXECUTION_MODES["balanced"])

    intel_file = Path("memory/analytics_intelligence.json")
    intel_data = {}
    if intel_file.exists():
        try:
            intel_data = json.loads(intel_file.read_text())
        except Exception:
            pass

    decisions = intel_data.get("autonomous_decisions", [])
    intel = load_intelligence()

    scored = [score_decision(d, intel) for d in decisions]
    scored.sort(key=lambda x: x["priority_score"], reverse=True)

    intel_data["autonomous_decisions"] = scored
    intel_data["execution_mode"] = mode
    intel_data["priority_updated_at"] = now_iso()
    intel_file.write_text(json.dumps(intel_data, indent=2))

    return {
        "generated_at": now_iso(),
        "execution_mode": mode,
        "mode_config": mode_config,
        "total_decisions": len(scored),
        "top_decisions": scored[:10],
        "score_weights": SCORE_WEIGHTS,
    }


def save_mode_config(mode: str) -> None:
    config = {
        "updated_at": now_iso(),
        "mode": mode,
        **EXECUTION_MODES.get(mode, EXECUTION_MODES["balanced"]),
    }
    (MEMORY_DIR / "execution_mode_config.json").write_text(json.dumps(config, indent=2))


def main():
    print("[priority] Starting execution priority engine...")

    mode = os.environ.get("EXECUTION_MODE", "balanced").lower()
    if mode not in EXECUTION_MODES:
        print(f"[priority] Unknown mode '{mode}' — defaulting to 'balanced'")
        mode = "balanced"

    cfg = EXECUTION_MODES[mode]
    print(f"[priority] Mode: {mode} — {cfg['description']}")
    print(
        f"[priority] Trust ≥{cfg['trust_threshold']} | "
        f"QA ≥{cfg['qa_gate']} | "
        f"Max {cfg['max_missions_per_cycle']} missions/cycle"
    )

    report = reorder_queue(mode)
    save_mode_config(mode)

    out = Path("memory/priority_report.json")
    out.write_text(json.dumps(report, indent=2))

    top = report.get("top_decisions", [])[:3]
    print(f"[priority] Scored {report.get('total_decisions', 0)} decisions")
    for d in top:
        label = d.get("title", d.get("action", ""))[:55]
        print(f"  {d.get('priority_score', 0):.1f}pts — [{d.get('project')}] {label}")

    print(f"[priority] Report → {out}")
    return report


if __name__ == "__main__":
    main()

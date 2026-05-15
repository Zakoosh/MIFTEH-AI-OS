"""
MIFTEH OS — Self-Evolution Engine
Analyzes system performance and evolves: prompts, QA thresholds, merge criteria,
token usage, workflow timing, and architecture recommendations.
Applies safe (non-breaking) evolutions automatically; saves the rest as recommendations.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")


def collect_system_data() -> dict:
    data: dict = {}

    # Prompt performance
    prompts_dir = MEMORY_DIR / "prompts"
    prompt_stats = []
    if prompts_dir.exists():
        for f in prompts_dir.glob("*.json"):
            try:
                p = json.loads(f.read_text())
                prompt_stats.append({
                    "key": f.stem,
                    "uses": p.get("uses", 0),
                    "avg_qa_score": p.get("avg_score", 0),
                    "avg_tokens": p.get("avg_tokens", 0),
                    "success_rate_pct": p.get("success_rate", 0),
                })
            except Exception:
                pass
    data["prompt_performance"] = sorted(
        prompt_stats, key=lambda x: x.get("avg_qa_score", 0)
    )

    # Visual QA stats
    qa_f = MEMORY_DIR / "visual_qa_summary.json"
    qa_data = {}
    if qa_f.exists():
        try:
            qa_data = json.loads(qa_f.read_text())
        except Exception:
            pass
    data["visual_qa"] = {
        "total": qa_data.get("total", 0),
        "pass_rate_pct": qa_data.get("pass_rate_pct", 0),
        "avg_score": qa_data.get("avg_score", 0),
        "current_threshold": 70,
    }

    # AI QA stats
    aiqa_f = MEMORY_DIR / "ai_qa_summary.json"
    aiqa_data = {}
    if aiqa_f.exists():
        try:
            aiqa_data = json.loads(aiqa_f.read_text())
        except Exception:
            pass
    data["ai_qa"] = {
        "total": aiqa_data.get("total", 0),
        "approve_rate_pct": aiqa_data.get("approve_rate_pct", 0),
        "avg_composite_score": aiqa_data.get("avg_composite_score", 0),
    }

    # Merge stats
    merge_log = []
    ml_f = MEMORY_DIR / "automerge_log.json"
    if ml_f.exists():
        try:
            merge_log = json.loads(ml_f.read_text())
        except Exception:
            pass
    merges = [e for e in merge_log if e.get("action") == "merged"]
    rollbacks = [e for e in merge_log if e.get("action") == "rolled_back"]
    data["merge_stats"] = {
        "total_merges": len(merges),
        "total_rollbacks": len(rollbacks),
        "rollback_rate_pct": round(
            len(rollbacks) / max(len(merges), 1) * 100, 1
        ),
        "current_trust_threshold": 90,
    }

    # Token efficiency
    si_f = MEMORY_DIR / "self_improvement_report.json"
    si_data = {}
    if si_f.exists():
        try:
            si_data = json.loads(si_f.read_text())
        except Exception:
            pass
    raw = si_data.get("raw_metrics", {})
    data["token_efficiency"] = {
        "total_tokens": raw.get("total_tokens", 0),
        "total_cost_usd": raw.get("total_cost_usd", 0),
        "features_generated": raw.get("features_generated", 0),
        "avg_cost_per_feature_usd": raw.get("avg_cost_per_feature", 0),
        "current_model": "gpt-4o-mini",
    }

    # Experiment results
    exp_f = MEMORY_DIR / "experiment_summary.json"
    exp_data = {}
    if exp_f.exists():
        try:
            exp_data = json.loads(exp_f.read_text())
        except Exception:
            pass
    data["experiments"] = {
        "total": exp_data.get("total", 0),
        "win_rate_pct": exp_data.get("win_rate_pct", 0),
        "avg_score_delta": exp_data.get("avg_score_delta", 0),
        "best_experiment_type": max(
            exp_data.get("by_type", {}).items(),
            key=lambda x: x[1].get("avg_delta", 0),
            default=("none", {}),
        )[0],
    }

    # Revenue & ROI
    rev_f = MEMORY_DIR / "revenue_report.json"
    rev_data = {}
    if rev_f.exists():
        try:
            rev_data = json.loads(rev_f.read_text())
        except Exception:
            pass
    data["revenue"] = rev_data.get("portfolio_summary", {})

    # Execution mode
    mode_f = MEMORY_DIR / "execution_mode_config.json"
    if mode_f.exists():
        try:
            data["execution_mode"] = json.loads(mode_f.read_text())
        except Exception:
            data["execution_mode"] = {"mode": "balanced"}
    else:
        data["execution_mode"] = {"mode": "balanced"}

    return data


def generate_evolution_recommendations(system_data: dict) -> dict:
    system = (
        "You are the MIFTEH OS self-evolution AI. Analyze system performance metrics "
        "and generate specific, actionable recommendations to improve the autonomous system. "
        "Think like a senior ML engineer optimizing a production AI pipeline."
    )
    prompt = f"""System performance data:
{json.dumps(system_data, indent=2)}

Generate evolution recommendations. Respond with JSON:
{{
  "evolution_summary": "2-3 sentence analysis of system health and maturity",
  "system_maturity_score": 0,
  "recommended_evolutions": [
    {{
      "target": "prompt_quality|qa_thresholds|merge_criteria|token_efficiency|workflow_timing|architecture",
      "current_state": "description",
      "recommended_change": "specific change",
      "expected_improvement": "measurable outcome",
      "implementation": "how to apply it",
      "priority": 1,
      "breaking_change": false
    }}
  ],
  "prompt_improvements": [
    {{
      "prompt_key": "key",
      "issue": "what is underperforming",
      "suggested_fix": "how to improve"
    }}
  ],
  "threshold_recommendations": {{
    "qa_threshold": 70,
    "trust_threshold": 85,
    "auto_merge_min_score": 90,
    "rationale": "why these values"
  }},
  "architecture_recommendations": [
    "recommendation 1",
    "recommendation 2"
  ],
  "token_optimization": {{
    "current_avg_cost_per_feature_usd": 0,
    "target_avg_cost_per_feature_usd": 0,
    "strategy": "description"
  }},
  "next_evolution_priority": "single most impactful change to make right now"
}}
Return ONLY valid JSON."""

    try:
        data, _, _, ok = generate_json(system, prompt, max_tokens=2000)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return data
    except Exception as e:
        return {
            "evolution_summary": "Evolution analysis unavailable — using defaults",
            "system_maturity_score": 40,
            "recommended_evolutions": [],
            "prompt_improvements": [],
            "threshold_recommendations": {
                "qa_threshold": 70,
                "trust_threshold": 85,
                "auto_merge_min_score": 90,
                "rationale": "Conservative defaults",
            },
            "architecture_recommendations": [
                "Collect more data before making threshold changes",
                "Run experiment engine to identify winning content patterns",
            ],
            "token_optimization": {
                "current_avg_cost_per_feature_usd": 0,
                "target_avg_cost_per_feature_usd": 0,
                "strategy": "N/A",
            },
            "next_evolution_priority": "Collect more performance data across 10+ features",
            "error": str(e),
        }


def apply_safe_evolutions(recommendations: dict) -> list:
    """Apply non-breaking evolutions automatically."""
    applied = []

    # Update execution thresholds
    thresholds = recommendations.get("threshold_recommendations", {})
    if thresholds:
        mode_f = MEMORY_DIR / "execution_mode_config.json"
        existing = {}
        if mode_f.exists():
            try:
                existing = json.loads(mode_f.read_text())
            except Exception:
                pass
        existing.update({
            "evolution_updated_at": now_iso(),
            "recommended_qa_threshold": thresholds.get("qa_threshold", 70),
            "recommended_trust_threshold": thresholds.get("trust_threshold", 85),
            "recommended_auto_merge_min": thresholds.get("auto_merge_min_score", 90),
            "threshold_rationale": thresholds.get("rationale", ""),
        })
        mode_f.write_text(json.dumps(existing, indent=2))
        applied.append(
            f"Threshold recommendations saved: "
            f"QA≥{thresholds.get('qa_threshold', 70)}, "
            f"trust≥{thresholds.get('trust_threshold', 85)}"
        )

    # Save prompt improvement suggestions
    improvements = recommendations.get("prompt_improvements", [])
    if improvements:
        sug_f = MEMORY_DIR / "prompt_improvement_suggestions.json"
        sug_f.write_text(json.dumps({
            "generated_at": now_iso(),
            "suggestions": improvements,
        }, indent=2))
        applied.append(f"Saved {len(improvements)} prompt improvement suggestions")

    # Save architecture recommendations
    arch = recommendations.get("architecture_recommendations", [])
    if arch:
        arch_f = MEMORY_DIR / "architecture_recommendations.json"
        arch_f.write_text(json.dumps({
            "generated_at": now_iso(),
            "recommendations": arch,
        }, indent=2))
        applied.append(f"Saved {len(arch)} architecture recommendations")

    return applied


def main():
    print("[evolution] Starting self-evolution engine...")

    system_data = collect_system_data()
    print(f"[evolution] Collected data across {len(system_data)} system dimensions")

    recommendations = generate_evolution_recommendations(system_data)
    score = recommendations.get("system_maturity_score", 0)
    n_evolutions = len(recommendations.get("recommended_evolutions", []))
    print(f"[evolution] Maturity score: {score}/100")
    print(f"[evolution] {n_evolutions} evolution recommendations")
    print(f"[evolution] Priority: {recommendations.get('next_evolution_priority', '')[:80]}")

    applied = apply_safe_evolutions(recommendations)
    for a in applied:
        print(f"  [evolution] Applied: {a}")

    report = {
        "generated_at": now_iso(),
        "system_maturity_score": score,
        "evolution_summary": recommendations.get("evolution_summary", ""),
        "next_evolution_priority": recommendations.get("next_evolution_priority", ""),
        "recommended_evolutions": recommendations.get("recommended_evolutions", []),
        "prompt_improvements": recommendations.get("prompt_improvements", []),
        "threshold_recommendations": recommendations.get("threshold_recommendations", {}),
        "architecture_recommendations": recommendations.get("architecture_recommendations", []),
        "token_optimization": recommendations.get("token_optimization", {}),
        "applied_evolutions": applied,
        "system_snapshot": system_data,
    }

    out = Path("memory/evolution_report.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"[evolution] Report → {out}")
    return report


if __name__ == "__main__":
    main()

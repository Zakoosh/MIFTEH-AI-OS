"""
MIFTEH OS — Autonomous Experimentation Engine
Generates A/B test variants for headlines, CTAs, layouts, SEO structures.
Evaluates winners by QA score delta. Saves winning variants for review.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_text, now_iso
from visual_validator import validate_html

MEMORY_DIR = Path("memory")
EXPERIMENTS_DIR = MEMORY_DIR / "experiments"

VALID_TYPES = ["headline", "cta", "layout", "seo_structure", "content_depth"]

HYPOTHESES = {
    "headline": (
        "A specific, benefit-focused headline increases engagement and click-through rate"
    ),
    "cta": (
        "Above-fold CTA with urgency language increases conversion rate"
    ),
    "layout": (
        "Content-first layout (main content before sidebar) improves reading flow and dwell time"
    ),
    "seo_structure": (
        "Explicit keyword in first 100 words and FAQ section improves search ranking"
    ),
    "content_depth": (
        "Longer content (500+ words) with structured subheadings improves dwell time and authority"
    ),
}

AGENT_TASKS = {
    "headline": (
        "Rewrite the main H1 heading and all H2 subheadings to be more specific, "
        "benefit-focused, and keyword-rich. Keep the same topic and page structure."
    ),
    "cta": (
        "Optimize all CTA buttons: improve copy with action verbs + benefit, "
        "add an above-fold CTA if missing, add urgency signals where appropriate."
    ),
    "layout": (
        "Reorganize page sections to lead with the most valuable content. "
        "Move the primary value proposition above any widgets or secondary content."
    ),
    "seo_structure": (
        "Improve SEO structure: add the primary keyword in the first paragraph, "
        "improve heading hierarchy (H1→H2→H3), add a FAQ section at the bottom, "
        "and add/improve the meta description."
    ),
    "content_depth": (
        "Expand the main content sections with more specific information, examples, "
        "and supporting details. Add at least 2 new informational paragraphs."
    ),
}


def generate_variant(
    original_html: str, experiment_type: str, project: str, hypothesis: str
) -> dict:
    task = AGENT_TASKS.get(experiment_type, hypothesis)
    system = (
        f"You are an A/B testing expert optimizing HTML for {experiment_type} improvement. "
        "Generate a complete improved HTML page that tests the hypothesis. "
        "Preserve all existing scripts, styles, and structural tags."
    )
    prompt = f"""Project: {project}
Experiment: {experiment_type}
Hypothesis: {hypothesis}
Task: {task}

Original HTML (first 4000 chars):
{original_html[:4000]}

Generate the COMPLETE improved HTML variant. Return ONLY the HTML."""

    try:
        html, _, _, ok = generate_text(system, prompt, max_tokens=3500)
        if not ok or not html:
            raise ValueError("generate_text returned no content")
        return {"success": True, "html": html}
    except Exception as e:
        return {"success": False, "html": original_html, "error": str(e)}


def run_experiment(
    feature_id: str,
    project: str,
    html_path: Path,
    experiment_type: str,
) -> dict:
    if experiment_type not in VALID_TYPES:
        return {"success": False, "error": f"Unknown experiment type: {experiment_type}"}

    original_html = html_path.read_text(encoding="utf-8")
    hypothesis = HYPOTHESES[experiment_type]

    control_score = validate_html(
        original_html, label=f"{feature_id}_control", project=project
    )

    variant_result = generate_variant(original_html, experiment_type, project, hypothesis)
    if not variant_result["success"]:
        return {"success": False, "error": variant_result.get("error")}

    variant_html = variant_result["html"]
    variant_score = validate_html(
        variant_html, label=f"{feature_id}_variant_{experiment_type}", project=project
    )

    score_delta = variant_score["score"] - control_score["score"]
    winner = "variant" if score_delta > 0 else "control"

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{project}_{feature_id}_{experiment_type}_{ts}"

    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "experiment_id": experiment_id,
        "feature_id": feature_id,
        "project": project,
        "experiment_type": experiment_type,
        "hypothesis": hypothesis,
        "control_score": control_score["score"],
        "control_grade": control_score.get("grade", ""),
        "variant_score": variant_score["score"],
        "variant_grade": variant_score.get("grade", ""),
        "score_delta": score_delta,
        "winner": winner,
        "promote_recommended": winner == "variant" and score_delta >= 3,
        "generated_at": now_iso(),
        "control_html_path": str(html_path),
    }

    if record["promote_recommended"]:
        variant_path = (
            Path("frontend/dashboard/previews") / project
            / f"{feature_id}_variant_{experiment_type}.html"
        )
        variant_path.parent.mkdir(parents=True, exist_ok=True)
        variant_path.write_text(variant_html, encoding="utf-8")
        record["variant_html_path"] = str(variant_path)
        print(f"    → Variant WINS +{score_delta:.0f}pts ({variant_score['score']}/100) saved")
    else:
        print(
            f"    → Control wins (variant {score_delta:+.0f}pts | "
            f"control {control_score['score']} vs variant {variant_score['score']})"
        )

    (EXPERIMENTS_DIR / f"{experiment_id}.json").write_text(json.dumps(record, indent=2))
    return record


def build_experiment_summary() -> dict:
    experiments = []
    if EXPERIMENTS_DIR.exists():
        for f in sorted(EXPERIMENTS_DIR.glob("*.json"), reverse=True)[:100]:
            try:
                experiments.append(json.loads(f.read_text()))
            except Exception:
                pass

    if not experiments:
        return {
            "generated_at": now_iso(),
            "total": 0,
            "winners": 0,
            "win_rate_pct": 0,
            "avg_score_delta": 0,
            "by_type": {},
            "promote_recommended": [],
            "recent": [],
        }

    winners = [e for e in experiments if e.get("winner") == "variant"]
    by_type: dict = {}
    for e in experiments:
        t = e.get("experiment_type", "unknown")
        if t not in by_type:
            by_type[t] = {"total": 0, "variant_wins": 0, "avg_delta": 0.0}
        by_type[t]["total"] += 1
        if e.get("winner") == "variant":
            by_type[t]["variant_wins"] += 1
        n = by_type[t]["total"]
        by_type[t]["avg_delta"] = round(
            (by_type[t]["avg_delta"] * (n - 1) + e.get("score_delta", 0)) / n, 1
        )

    return {
        "generated_at": now_iso(),
        "total": len(experiments),
        "winners": len(winners),
        "win_rate_pct": round(len(winners) / max(len(experiments), 1) * 100, 1),
        "avg_score_delta": round(
            sum(e.get("score_delta", 0) for e in experiments) / max(len(experiments), 1), 1
        ),
        "by_type": by_type,
        "promote_recommended": [
            e for e in experiments if e.get("promote_recommended")
        ][:5],
        "recent": [
            {
                "experiment_id": e["experiment_id"],
                "project": e["project"],
                "experiment_type": e["experiment_type"],
                "winner": e["winner"],
                "score_delta": e["score_delta"],
                "control_score": e["control_score"],
                "variant_score": e["variant_score"],
                "promote_recommended": e.get("promote_recommended", False),
                "generated_at": e["generated_at"],
            }
            for e in experiments[:15]
        ],
    }


def main():
    print("[experiment] Starting experiment engine...")

    target_project = os.environ.get("TARGET_PROJECT", "all")
    exp_types_env = os.environ.get("EXPERIMENT_TYPES", "headline,cta,seo_structure")
    experiment_types = [t.strip() for t in exp_types_env.split(",") if t.strip() in VALID_TYPES]

    if not experiment_types:
        experiment_types = ["headline", "cta", "seo_structure"]

    projects = (
        ["yallaplays", "fionera", "mifteh"]
        if target_project == "all"
        else [target_project]
    )

    total_experiments = 0
    total_wins = 0

    for project in projects:
        previews_dir = Path("frontend/dashboard/previews") / project
        if not previews_dir.exists():
            print(f"  [experiment] No previews for {project} — skipping")
            continue

        # Only experiment on base HTML files (not already-variant files)
        html_files = [
            f for f in sorted(previews_dir.glob("*.html"))
            if "_variant_" not in f.stem
        ][:3]

        if not html_files:
            print(f"  [experiment] No HTML files for {project} — skipping")
            continue

        print(
            f"  [experiment] {project}: "
            f"{len(html_files)} features × {len(experiment_types)} types"
        )

        for html_file in html_files:
            feature_id = html_file.stem
            for exp_type in experiment_types:
                print(f"    [{feature_id}] {exp_type}...")
                result = run_experiment(feature_id, project, html_file, exp_type)
                total_experiments += 1
                if result.get("winner") == "variant":
                    total_wins += 1

    summary = build_experiment_summary()
    out = Path("memory/experiment_summary.json")
    out.write_text(json.dumps(summary, indent=2))
    print(
        f"[experiment] {total_experiments} experiments | "
        f"{total_wins} variant wins | "
        f"win rate {summary['win_rate_pct']}%"
    )
    print(f"[experiment] Summary → {out}")
    return summary


if __name__ == "__main__":
    main()

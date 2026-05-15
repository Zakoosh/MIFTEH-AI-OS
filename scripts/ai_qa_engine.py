"""
MIFTEH OS — AI QA Engine
AI-powered quality review for every generated HTML feature.
Evaluates: visual hierarchy, CTA quality, UX clarity, conversion optimization,
content readability, SEO quality, trust signals, and accessibility.
Outputs: score (0-100), critique, recommendations, merge/block decision.

Combines static QA (visual_validator), browser QA (browser_runtime),
and AI critique (OpenAI) into a single authoritative report.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, timestamp_str
from visual_validator import validate_html

QA_DIR  = Path("memory/visual_qa")
AI_QA_DIR = Path("memory/ai_qa")

AI_QA_DIR.mkdir(parents=True, exist_ok=True)
QA_DIR.mkdir(parents=True, exist_ok=True)


SYSTEM_PROMPT = """You are a senior product quality reviewer at a top-tier web agency.
You review AI-generated HTML features for production readiness.
Be critical, specific, and actionable. Think like a conversion rate optimizer + SEO expert + UX designer.
Return valid JSON only."""


def build_review_prompt(
    html: str,
    static_qa: dict,
    project: str,
    feature_type: str,
    label: str,
    browser_qa: dict | None = None,
) -> str:
    # Summarize static scores
    cats = static_qa.get("categories", {})
    seo_s   = cats.get("seo",           {}).get("score", 0)
    mob_s   = cats.get("mobile",        {}).get("score", 0)
    a11y_s  = cats.get("accessibility", {}).get("score", 0)
    perf_s  = cats.get("performance",   {}).get("score", 0)
    ux_s    = cats.get("ux",            {}).get("score", 0)
    all_issues = static_qa.get("all_issues", [])[:8]

    browser_section = ""
    if browser_qa:
        browser_section = f"""
BROWSER VALIDATION (real Chromium):
  - Score: {browser_qa.get('score', 'N/A')}/100
  - Console errors: {len(browser_qa.get('console_errors', []))}
  - CLS violations: {browser_qa.get('cls_score', 0):.2f}
  - Broken interactions: {browser_qa.get('interactions', {}).get('broken_interactions', 0)}
  - Performance (DOM loaded): {browser_qa.get('performance', {}).get('dom_content_loaded', '?')}ms
  - Mobile overflow issues: {sum(1 for i in browser_qa.get('issues', []) if 'mobile' in i.lower() or 'overflow' in i.lower())}"""

    # Truncate HTML for AI context
    html_snippet = html[:3000] + ("..." if len(html) > 3000 else "")

    return f"""Review this AI-generated HTML feature for production readiness.

FEATURE INFO:
  - Label: {label}
  - Project: {project}
  - Type: {feature_type}

STATIC QA SCORES:
  - SEO: {seo_s}/30
  - Mobile: {mob_s}/25
  - Accessibility: {a11y_s}/20
  - Performance: {perf_s}/15
  - UX: {ux_s}/10
  - Total: {static_qa.get('score', 0)}/100
  - Grade: {static_qa.get('grade', '?')}
  - Known issues: {json.dumps(all_issues)}
{browser_section}

HTML CONTENT (first 3000 chars):
{html_snippet}

Evaluate these dimensions:
1. Visual hierarchy (H1→H2→H3 flow, section clarity, visual weight)
2. CTA quality (button copy, placement, prominence, number of CTAs)
3. UX clarity (navigation, user flow, cognitive load)
4. Conversion optimization (above-fold value prop, trust signals, friction reduction)
5. Content readability (sentence length, scannability, word choice)
6. SEO quality (keyword density, heading usage, meta accuracy, schema)
7. Trust signals (social proof, credentials, contact info, privacy)
8. Accessibility (ARIA, contrast, keyboard nav, screen reader friendliness)

Return this JSON structure:
{{
  "ai_score": <0-100 integer, your holistic quality score>,
  "merge_decision": "approve" | "review_required" | "block",
  "merge_reason": "<1 sentence explaining the decision>",
  "dimension_scores": {{
    "visual_hierarchy": <0-100>,
    "cta_quality": <0-100>,
    "ux_clarity": <0-100>,
    "conversion": <0-100>,
    "readability": <0-100>,
    "seo_quality": <0-100>,
    "trust_signals": <0-100>,
    "accessibility": <0-100>
  }},
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "critical_issues": ["<blocker if any>"],
  "recommendations": [
    {{
      "area": "<dimension>",
      "issue": "<specific problem>",
      "fix": "<concrete fix>",
      "impact": "high|medium|low"
    }}
  ],
  "overall_critique": "<2-3 sentences: honest professional critique>",
  "production_readiness": "ready" | "needs_minor_fixes" | "needs_major_rework"
}}

Scoring guide for merge_decision:
  - approve: ai_score >= 75 AND no critical issues
  - review_required: ai_score 55-74 OR has fixable issues
  - block: ai_score < 55 OR critical issues present (broken layout, placeholder text, missing navigation)"""


def run_ai_review(
    html: str,
    project: str,
    feature_id: str,
    feature_type: str,
    label: str,
    static_qa: dict | None = None,
    browser_qa: dict | None = None,
) -> dict:
    """Run full AI QA review and return combined report."""

    # Run static QA if not provided
    if static_qa is None:
        static_qa = validate_html(html, label=label, project=project)

    sys_prompt = SYSTEM_PROMPT
    user_prompt = build_review_prompt(html, static_qa, project, feature_type, label, browser_qa)

    print(f"  [ai-qa] Reviewing {project}/{feature_id}...")
    ai_data, tokens, cost, ok = generate_json(sys_prompt, user_prompt, max_tokens=2000)

    if not ok or not ai_data:
        ai_data = {
            "ai_score": static_qa.get("score", 0),
            "merge_decision": "review_required",
            "merge_reason": "AI review unavailable — defaulting to static QA score",
            "dimension_scores": {},
            "strengths": [],
            "critical_issues": [],
            "recommendations": [],
            "overall_critique": "AI review unavailable",
            "production_readiness": "needs_minor_fixes",
        }

    # Compute composite score: 60% AI, 40% static
    ai_score = ai_data.get("ai_score", 0)
    static_score = static_qa.get("score", 0)
    composite = round(ai_score * 0.6 + static_score * 0.4)

    report = {
        "project": project,
        "feature_id": feature_id,
        "feature_type": feature_type,
        "label": label,
        "reviewed_at": now_iso(),
        "ai_generated": ok,
        "tokens_used": tokens,
        "cost_usd": cost,
        # Scores
        "composite_score": composite,
        "ai_score": ai_score,
        "static_score": static_score,
        "grade": "A" if composite >= 90 else "B" if composite >= 80 else "C" if composite >= 70 else "D" if composite >= 60 else "F",
        "passes_auto_merge_threshold": composite >= 70,
        # AI review
        "merge_decision": ai_data.get("merge_decision", "review_required"),
        "merge_reason": ai_data.get("merge_reason", ""),
        "dimension_scores": ai_data.get("dimension_scores", {}),
        "strengths": ai_data.get("strengths", []),
        "critical_issues": ai_data.get("critical_issues", []),
        "recommendations": ai_data.get("recommendations", []),
        "overall_critique": ai_data.get("overall_critique", ""),
        "production_readiness": ai_data.get("production_readiness", ""),
        # Static QA summary
        "static_qa": {
            "score": static_score,
            "grade": static_qa.get("grade", "?"),
            "issues": static_qa.get("all_issues", [])[:5],
        },
    }

    # Save report
    out = AI_QA_DIR / f"{project}_{feature_id}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"  [ai-qa] {label}: composite={composite}/100 grade={report['grade']} decision={report['merge_decision']}")

    return report


def review_all_previews(target_project: str = "all", force: bool = False) -> list[dict]:
    """Run AI QA on all saved HTML previews."""
    previews_root = Path("frontend/dashboard/previews")
    if not previews_root.exists():
        print("[ai-qa] No previews found")
        return []

    reports = []
    for proj_dir in previews_root.iterdir():
        if not proj_dir.is_dir():
            continue
        project = proj_dir.name
        if target_project != "all" and project.lower() != target_project.lower():
            continue

        for html_file in sorted(proj_dir.glob("*.html")):
            feature_id = html_file.stem
            out_path = AI_QA_DIR / f"{project}_{feature_id}.json"

            if not force and out_path.exists():
                print(f"  [ai-qa] {project}/{feature_id} already reviewed — skip")
                try:
                    reports.append(json.loads(out_path.read_text()))
                except Exception:
                    pass
                continue

            html = html_file.read_text(encoding="utf-8", errors="replace")

            # Load existing static QA if available
            static_path = QA_DIR / f"{project}_{feature_id}.json"
            static_qa = None
            if static_path.exists():
                try:
                    static_qa = json.loads(static_path.read_text())
                except Exception:
                    pass

            # Load browser QA if available
            browser_path = QA_DIR / f"{project}_{feature_id}_browser.json"
            browser_qa = None
            if browser_path.exists():
                try:
                    browser_qa = json.loads(browser_path.read_text())
                except Exception:
                    pass

            # Determine feature type from filename / static qa
            ftype = (static_qa or {}).get("feature_type", "unknown")
            label = (static_qa or {}).get("label", html_file.stem)

            report = run_ai_review(
                html, project, feature_id, ftype, label,
                static_qa=static_qa, browser_qa=browser_qa,
            )
            reports.append(report)

    return reports


def build_ai_qa_summary() -> dict:
    """Aggregate all AI QA reports."""
    all_reports = []
    for f in AI_QA_DIR.glob("*.json"):
        try:
            all_reports.append(json.loads(f.read_text()))
        except Exception:
            pass

    if not all_reports:
        return {"total": 0, "passing": 0, "avg_score": 0, "reports": []}

    approved  = [r for r in all_reports if r.get("merge_decision") == "approve"]
    review    = [r for r in all_reports if r.get("merge_decision") == "review_required"]
    blocked   = [r for r in all_reports if r.get("merge_decision") == "block"]
    avg_comp  = round(sum(r.get("composite_score", 0) for r in all_reports) / len(all_reports))
    avg_ai    = round(sum(r.get("ai_score", 0) for r in all_reports) / len(all_reports))

    return {
        "total": len(all_reports),
        "approved": len(approved),
        "review_required": len(review),
        "blocked": len(blocked),
        "avg_composite_score": avg_comp,
        "avg_ai_score": avg_ai,
        "reports": sorted(
            [
                {
                    "project": r.get("project", ""),
                    "feature_id": r.get("feature_id", ""),
                    "label": r.get("label", ""),
                    "composite_score": r.get("composite_score", 0),
                    "ai_score": r.get("ai_score", 0),
                    "static_score": r.get("static_score", 0),
                    "grade": r.get("grade", "?"),
                    "merge_decision": r.get("merge_decision", ""),
                    "production_readiness": r.get("production_readiness", ""),
                    "overall_critique": r.get("overall_critique", ""),
                    "strengths": r.get("strengths", [])[:2],
                    "critical_issues": r.get("critical_issues", [])[:2],
                    "top_recommendations": [
                        rec for rec in r.get("recommendations", [])
                        if rec.get("impact") == "high"
                    ][:2],
                    "dimension_scores": r.get("dimension_scores", {}),
                    "reviewed_at": r.get("reviewed_at", ""),
                }
                for r in all_reports
            ],
            key=lambda x: x["composite_score"],
            reverse=True,
        ),
    }


def save_ai_qa_summary():
    summary = build_ai_qa_summary()
    out = Path("memory") / "ai_qa_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[ai-qa] Summary → {out}  ({summary['approved']} approved, {summary['blocked']} blocked)")
    return summary


def main():
    print("[ai-qa] Starting AI QA review engine...")
    force = os.environ.get("FORCE_REVIEW", "").lower() in ("1", "true", "yes")
    target_project = os.environ.get("TARGET_PROJECT", "all")

    reports = review_all_previews(target_project=target_project, force=force)
    print(f"[ai-qa] Reviewed {len(reports)} features")
    save_ai_qa_summary()


if __name__ == "__main__":
    main()

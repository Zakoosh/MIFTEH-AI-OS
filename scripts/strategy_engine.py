"""
MIFTEH OS — Strategic Planning Engine
Analyzes all intelligence sources, detects growth bottlenecks,
generates 30-day and 90-day execution plans, injects top items into executor queue.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

INTEL_SOURCES = {
    "analytics": "memory/analytics_intelligence.json",
    "roadmap": "memory/roadmap.json",
    "revenue": "memory/revenue_report.json",
    "deployment": "memory/deployment_monitor.json",
    "self_improvement": "memory/self_improvement_report.json",
    "cross_project": "memory/cross_project_summary.json",
    "market": "memory/market_intelligence.json",
    "experiments": "memory/experiment_summary.json",
}


def load_intelligence() -> dict:
    sources = {}
    for name, path in INTEL_SOURCES.items():
        f = Path(path)
        if f.exists():
            try:
                sources[name] = json.loads(f.read_text())
            except Exception:
                pass
    return sources


def detect_bottlenecks(intel: dict) -> list:
    bottlenecks = []

    # Site availability
    for site, data in intel.get("deployment", {}).get("sites", {}).items():
        if data.get("status") == "degraded":
            bottlenecks.append({
                "type": "availability",
                "severity": "critical",
                "project": site,
                "issue": f"{site} is currently degraded/unreachable",
                "impact": "Zero traffic while down",
            })
        score = data.get("score", 100)
        if score < 70:
            bottlenecks.append({
                "type": "quality",
                "severity": "high",
                "project": site,
                "issue": f"Site quality score {score}/100 — below threshold",
                "impact": "SEO penalties, poor user experience",
            })

    # SEO gaps from roadmap
    for proj, pdata in intel.get("roadmap", {}).get("projects", {}).items():
        gaps = pdata.get("seo_gaps", [])
        if len(gaps) >= 3:
            bottlenecks.append({
                "type": "seo",
                "severity": "medium",
                "project": proj,
                "issue": f"{len(gaps)} unaddressed SEO gaps",
                "impact": "Missed organic traffic",
            })

    # Low revenue ROI
    for proj, rdata in intel.get("revenue", {}).get("projects", {}).items():
        if rdata.get("portfolio_roi", 999) < 10:
            bottlenecks.append({
                "type": "revenue",
                "severity": "medium",
                "project": proj,
                "issue": f"Low feature ROI ({rdata.get('portfolio_roi', 0):.1f}x)",
                "impact": "Token spend not converting to revenue",
            })

    # Low QA pass rate
    si = intel.get("self_improvement", {}).get("raw_metrics", {})
    qa_rate = si.get("qa_pass_rate_pct", 100)
    if qa_rate < 60:
        bottlenecks.append({
            "type": "quality",
            "severity": "high",
            "project": "all",
            "issue": f"QA pass rate {qa_rate:.0f}% — too many features failing validation",
            "impact": "Wasted generation cycles",
        })

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(bottlenecks, key=lambda x: severity_order.get(x["severity"], 4))


def generate_strategic_plan(intel: dict, bottlenecks: list) -> dict:
    system = (
        "You are the strategic AI of MIFTEH OS — an autonomous AI company. "
        "Synthesize all available intelligence into concrete 30-day and 90-day growth plans. "
        "Think like a startup CEO + growth hacker + AI engineer combined."
    )

    revenue_summary = intel.get("revenue", {}).get("portfolio_summary", {})
    deploy_summary = {
        site: {"status": d.get("status"), "score": d.get("score")}
        for site, d in intel.get("deployment", {}).get("sites", {}).items()
    }
    cross_proj = intel.get("analytics", {}).get("cross_project", {})
    top_patterns = intel.get("cross_project", {}).get("top_patterns", [])[:3]
    market_topics = []
    for proj_trends in intel.get("market", {}).get("trends", {}).values():
        market_topics.extend(proj_trends.get("trending_topics", [])[:2])

    prompt = f"""Available intelligence:

Revenue portfolio: {json.dumps(revenue_summary)}
Deployment health: {json.dumps(deploy_summary)}
Analytics cross-project: {json.dumps(cross_proj)}
Critical bottlenecks: {json.dumps(bottlenecks[:5], indent=2)}
Top cross-project patterns: {json.dumps(top_patterns)}
Market trending topics: {json.dumps(market_topics[:6])}

Generate strategic plans. Respond with JSON:
{{
  "strategic_summary": "2-3 sentence company strategy",
  "north_star_metric": "the single most important metric to move",
  "30_day_plan": {{
    "theme": "plan theme",
    "objectives": ["objective 1", "objective 2", "objective 3"],
    "key_initiatives": [
      {{
        "initiative": "name",
        "project": "yallaplays|fionera|mifteh|all",
        "description": "what to do",
        "expected_impact": "measurable outcome",
        "priority": 1,
        "effort": "low|medium|high",
        "owner": "autonomous_executor|swarm|manual"
      }}
    ],
    "success_metrics": ["metric 1", "metric 2"],
    "projected_traffic_growth_pct": 0,
    "projected_revenue_growth_usd": 0
  }},
  "90_day_plan": {{
    "theme": "plan theme",
    "objectives": ["objective 1", "objective 2", "objective 3"],
    "milestones": [
      {{"week": 4, "milestone": "what we expect", "metrics": "success criteria"}},
      {{"week": 8, "milestone": "what we expect", "metrics": "success criteria"}},
      {{"week": 12, "milestone": "what we expect", "metrics": "success criteria"}}
    ],
    "projected_traffic_growth_pct": 0,
    "projected_revenue_growth_usd": 0
  }},
  "priority_matrix": [
    {{
      "initiative": "name",
      "impact": "high|medium|low",
      "effort": "high|medium|low",
      "quadrant": "do_now|plan|delegate|drop",
      "project": "project"
    }}
  ],
  "roi_forecasts": {{
    "30d_roi_multiplier": 0,
    "90d_roi_multiplier": 0,
    "confidence_pct": 0
  }},
  "execution_queue": [
    {{
      "rank": 1,
      "action": "specific action",
      "project": "project",
      "type": "seo_page|widget|optimization|content",
      "rationale": "why first"
    }}
  ]
}}
Return ONLY valid JSON."""

    try:
        data, _, _, ok = generate_json(system, prompt, max_tokens=2000)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return data
    except Exception as e:
        return {
            "strategic_summary": "Strategic analysis unavailable — using defaults",
            "north_star_metric": "Monthly organic traffic",
            "30_day_plan": {
                "theme": "Foundation",
                "objectives": ["Fix deployment gaps", "Launch 5 SEO pages", "Improve QA score"],
                "key_initiatives": [],
                "success_metrics": ["Traffic +10%", "QA avg ≥75"],
                "projected_traffic_growth_pct": 10,
                "projected_revenue_growth_usd": 50,
            },
            "90_day_plan": {
                "theme": "Scale",
                "objectives": ["Dominate 50 keywords", "Reach $500/mo revenue", "Full automation"],
                "milestones": [
                    {"week": 4, "milestone": "SEO foundation complete", "metrics": "+10% traffic"},
                    {"week": 8, "milestone": "Revenue engine active", "metrics": "$200/mo"},
                    {"week": 12, "milestone": "Autonomous at scale", "metrics": "+35% traffic"},
                ],
                "projected_traffic_growth_pct": 35,
                "projected_revenue_growth_usd": 500,
            },
            "priority_matrix": [],
            "roi_forecasts": {
                "30d_roi_multiplier": 5,
                "90d_roi_multiplier": 20,
                "confidence_pct": 40,
            },
            "execution_queue": [],
            "error": str(e),
        }


def inject_into_executor_queue(plan: dict) -> int:
    queue = plan.get("execution_queue", [])
    if not queue:
        return 0

    intel_file = Path("memory/analytics_intelligence.json")
    intel = {}
    if intel_file.exists():
        try:
            intel = json.loads(intel_file.read_text())
        except Exception:
            pass

    existing = intel.get("autonomous_decisions", [])
    existing_ids = {d.get("decision_id") for d in existing}

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    new_decisions = []
    for item in queue[:5]:
        did = f"strategy_r{item.get('rank', 0)}_{today}"
        if did in existing_ids:
            continue
        new_decisions.append({
            "decision_id": did,
            "project": item.get("project", "yallaplays"),
            "type": item.get("type", "seo_page"),
            "title": item.get("action", ""),
            "rationale": item.get("rationale", "Strategy engine recommendation"),
            "priority_weight": max(1, 10 - item.get("rank", 5)),
            "source": "strategy_engine",
        })

    intel["autonomous_decisions"] = new_decisions + existing
    intel["strategy_updated_at"] = now_iso()
    intel_file.write_text(json.dumps(intel, indent=2))
    return len(new_decisions)


def main():
    print("[strategy] Starting strategic planning engine...")

    intel = load_intelligence()
    print(f"[strategy] Loaded {len(intel)} intelligence sources")

    bottlenecks = detect_bottlenecks(intel)
    critical = sum(1 for b in bottlenecks if b["severity"] == "critical")
    print(f"[strategy] {len(bottlenecks)} bottlenecks detected ({critical} critical)")
    for b in bottlenecks[:3]:
        print(f"  [{b['severity'].upper()}] {b['project']}: {b['issue']}")

    plan = generate_strategic_plan(intel, bottlenecks)
    print(f"[strategy] North star: {plan.get('north_star_metric', '')}")
    print(f"[strategy] 30d theme: {plan.get('30_day_plan', {}).get('theme', '')}")

    injected = inject_into_executor_queue(plan)
    print(f"[strategy] Injected {injected} items into executor queue")

    report = {
        "generated_at": now_iso(),
        "bottlenecks": bottlenecks,
        "strategic_plan": plan,
        "intelligence_sources_used": list(intel.keys()),
        "executor_items_injected": injected,
    }

    out = Path("memory/strategy_report.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"[strategy] Report → {out}")
    return report


if __name__ == "__main__":
    main()

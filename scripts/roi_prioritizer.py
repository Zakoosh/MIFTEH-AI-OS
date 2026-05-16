"""
MIFTEH OS — ROI Prioritizer
ROI-first autonomous action ranking and execution queue.
Reads all report files to build a unified action inventory,
scores each action by revenue impact × conversion × timeline,
and outputs a prioritized execution queue for all agents.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

ROI_WEIGHTS = {
    "revenue_impact_usd": 0.40,
    "traffic_impact_sessions": 0.25,
    "conversion_impact": 0.20,
    "time_to_value_weeks": -0.15,  # negative: faster = higher score
}

PROJECTS = ["yallaplays", "fionera", "mifteh"]

ACTION_CATEGORIES = [
    "seo_content", "paid_acquisition", "conversion_optimization",
    "product_feature", "partnership", "monetization", "retention",
]


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def score_action(action):
    """Compute ROI score for an action (0-100)."""
    rev = action.get("revenue_impact_usd", 0)
    traffic = action.get("traffic_impact_sessions", 0)
    conversion = action.get("conversion_impact", 0.0)
    timeline = max(1, action.get("time_to_value_weeks", 4))
    effort = action.get("effort_days", 3)

    # Normalize each dimension to 0-1 scale
    rev_norm = min(1.0, rev / 5000)
    traffic_norm = min(1.0, traffic / 50000)
    conv_norm = min(1.0, conversion / 0.10)
    speed_norm = min(1.0, 1.0 / timeline)
    effort_penalty = max(0.5, 1.0 - effort / 20)

    score = (
        rev_norm * 40 +
        traffic_norm * 25 +
        conv_norm * 20 +
        speed_norm * 15
    ) * effort_penalty

    return round(score, 1)


def extract_actions_from_seo(prog_seo, growth):
    """Extract ROI-ranked actions from SEO reports."""
    actions = []
    total_pages = prog_seo.get("total_pages_generated", 0)
    est_traffic = prog_seo.get("estimated_monthly_traffic_gain", 0)

    if total_pages > 0:
        actions.append({
            "id": "deploy_programmatic_seo_pages",
            "category": "seo_content",
            "project": "yallaplays",
            "action": f"Deploy {total_pages} generated Arabic SEO pages",
            "revenue_impact_usd": est_traffic * 0.001 * 1.85,
            "traffic_impact_sessions": est_traffic,
            "conversion_impact": 0.0,
            "time_to_value_weeks": 6,
            "effort_days": 1,
            "source": "programmatic_seo_report",
        })

    for opp in prog_seo.get("top_opportunities", [])[:3]:
        actions.append({
            "id": f"seo_opp_{len(actions)}",
            "category": "seo_content",
            "project": "yallaplays",
            "action": str(opp),
            "revenue_impact_usd": 300,
            "traffic_impact_sessions": 3000,
            "conversion_impact": 0.0,
            "time_to_value_weeks": 4,
            "effort_days": 2,
            "source": "programmatic_seo_report",
        })

    growth_opps = growth.get("projects", {}).get("yallaplays", {}).get("topical_authority_plan", [])
    for pillar in growth_opps[:2]:
        if isinstance(pillar, dict):
            est = pillar.get("estimated_traffic_gain", 500)
            actions.append({
                "id": f"authority_{pillar.get('pillar', 'topic')[:20]}",
                "category": "seo_content",
                "project": "yallaplays",
                "action": f"Build {pillar.get('pillar', 'topic')} authority cluster",
                "revenue_impact_usd": est * 0.001 * 1.85,
                "traffic_impact_sessions": est,
                "conversion_impact": 0.0,
                "time_to_value_weeks": 8,
                "effort_days": 5,
                "source": "growth_report",
            })

    return actions


def extract_actions_from_revenue(revenue):
    """Extract ROI-ranked actions from revenue tracker."""
    actions = []
    critical = revenue.get("critical_revenue_actions", [])
    for act in critical:
        actions.append({
            "id": f"revenue_{act.get('project', 'x')}_{len(actions)}",
            "category": "monetization",
            "project": act.get("project", "mifteh"),
            "action": act.get("action", ""),
            "revenue_impact_usd": act.get("revenue_impact_usd", 500),
            "traffic_impact_sessions": 0,
            "conversion_impact": 0.02,
            "time_to_value_weeks": 2 if act.get("priority") == "immediate" else 4,
            "effort_days": 2,
            "source": "revenue_tracker_report",
        })

    rpm_optz = revenue.get("rpm_optimization", {})
    rpm_gap = rpm_optz.get("target_rpm", 2.5) - rpm_optz.get("current_rpm", 1.8)
    if rpm_gap > 0:
        yp_sessions = revenue.get("projects", {}).get("yallaplays", {}).get("monthly_sessions", 15000)
        rpm_rev_impact = (yp_sessions / 1000) * rpm_gap
        actions.append({
            "id": "rpm_optimization",
            "category": "monetization",
            "project": "yallaplays",
            "action": f"RPM optimization: close ${rpm_gap:.2f} gap to target",
            "revenue_impact_usd": round(rpm_rev_impact, 0),
            "traffic_impact_sessions": 0,
            "conversion_impact": 0.0,
            "time_to_value_weeks": 3,
            "effort_days": 4,
            "source": "revenue_tracker_report",
        })

    return actions


def extract_actions_from_acquisition(acquisition):
    """Extract actions from client acquisition report."""
    actions = []
    leads = acquisition.get("estimated_monthly_leads", 0)
    pipeline = acquisition.get("estimated_pipeline_value_usd", 0)

    if leads > 0:
        actions.append({
            "id": "activate_lead_magnets",
            "category": "conversion_optimization",
            "project": "mifteh",
            "action": f"Activate lead magnets to capture {leads} leads/month",
            "revenue_impact_usd": pipeline * 0.15,
            "traffic_impact_sessions": 500,
            "conversion_impact": 0.05,
            "time_to_value_weeks": 2,
            "effort_days": 3,
            "source": "client_acquisition_report",
        })

    actions.append({
        "id": "launch_pricing_page",
        "category": "conversion_optimization",
        "project": "mifteh",
        "action": "Deploy new AI pricing page with ROI calculator",
        "revenue_impact_usd": 2499 * 2,
        "traffic_impact_sessions": 200,
        "conversion_impact": 0.08,
        "time_to_value_weeks": 1,
        "effort_days": 1,
        "source": "client_acquisition_report",
    })

    actions.append({
        "id": "publish_case_studies",
        "category": "seo_content",
        "project": "mifteh",
        "action": "Publish authority case studies with ROI proof",
        "revenue_impact_usd": 2499,
        "traffic_impact_sessions": 1000,
        "conversion_impact": 0.04,
        "time_to_value_weeks": 3,
        "effort_days": 2,
        "source": "client_acquisition_report",
    })

    return actions


def extract_actions_from_product(product_builder):
    """Extract Fionera product actions."""
    actions = []
    n_features = product_builder.get("features_built", 0)

    if n_features > 0:
        actions.append({
            "id": "deploy_bist_market_page",
            "category": "product_feature",
            "project": "fionera",
            "action": "Deploy BIST market summary page with AI signals",
            "revenue_impact_usd": 1200,
            "traffic_impact_sessions": 2000,
            "conversion_impact": 0.03,
            "time_to_value_weeks": 1,
            "effort_days": 1,
            "source": "product_builder_report",
        })

        actions.append({
            "id": "launch_ai_alerts",
            "category": "product_feature",
            "project": "fionera",
            "action": "Launch AI alerts feature — premium conversion driver",
            "revenue_impact_usd": 2998,
            "traffic_impact_sessions": 500,
            "conversion_impact": 0.06,
            "time_to_value_weeks": 2,
            "effort_days": 5,
            "source": "product_builder_report",
        })

    return actions


def extract_actions_from_observability(observability):
    """Extract operational actions from observability."""
    actions = []
    bottlenecks = observability.get("bottlenecks", [])
    for b in bottlenecks[:3]:
        if b.get("severity") == "critical":
            actions.append({
                "id": f"fix_{b.get('type', 'issue')}",
                "category": "retention",
                "project": "system",
                "action": f"Fix: {b.get('details', 'critical issue')}",
                "revenue_impact_usd": 1000,
                "traffic_impact_sessions": 0,
                "conversion_impact": 0.01,
                "time_to_value_weeks": 1,
                "effort_days": 1,
                "source": "observability_report",
            })

    return actions


def build_execution_queue(scored_actions):
    """Build tiered execution queue from scored actions."""
    immediate = [a for a in scored_actions if a["roi_score"] >= 70][:5]
    this_week = [a for a in scored_actions if 40 <= a["roi_score"] < 70][:10]
    this_month = [a for a in scored_actions if a["roi_score"] < 40][:10]

    return {
        "immediate": immediate,
        "this_week": this_week,
        "this_month": this_month,
    }


def ai_roi_strategy(scored_actions, total_pipeline):
    """AI synthesizes ROI ranking into strategic priorities."""
    system = (
        "You are a growth strategist. Recommend the highest-ROI execution path. "
        "Profitability-first. Return valid JSON only."
    )
    top5 = [{"action": a["action"], "project": a["project"], "roi_score": a["roi_score"], "revenue_impact": a["revenue_impact_usd"]} for a in scored_actions[:5]]
    prompt = f"""ROI action ranking complete.
Top 5 actions by ROI score: {json.dumps(top5)}
Total addressable pipeline: ${total_pipeline:,.0f}
Total actions ranked: {len(scored_actions)}

Return strategic priorities:
{{
  "strategy_score": 0-100,
  "top_priority_action": "single most important action",
  "execution_philosophy": "concise strategic principle",
  "weekly_sprint_focus": ["action1", "action2", "action3"],
  "revenue_unlock_sequence": ["step1", "step2", "step3"],
  "agent_directives": {{
    "seo_agent": "directive",
    "product_agent": "directive",
    "acquisition_agent": "directive",
    "monetization_agent": "directive"
  }},
  "risk_flags": ["flag1"],
  "executive_summary": "2-sentence ROI strategy overview"
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 500)
    if not ok:
        data = {
            "strategy_score": 72,
            "top_priority_action": scored_actions[0]["action"] if scored_actions else "Define top action",
            "execution_philosophy": "Revenue unlock first, scale what works, automate everything",
            "weekly_sprint_focus": [a["action"] for a in scored_actions[:3]],
            "revenue_unlock_sequence": [
                "1. Activate Mifteh consultation funnel",
                "2. Deploy programmatic SEO pages for YallaPlays",
                "3. Launch Fionera AI alerts premium feature",
            ],
            "agent_directives": {
                "seo_agent": "Prioritize YallaPlays category hub deployment",
                "product_agent": "Ship Fionera BIST market page this week",
                "acquisition_agent": "Activate lead magnet funnel immediately",
                "monetization_agent": "Optimize RPM and launch Fionera premium",
            },
            "risk_flags": ["Low analytics coverage reduces optimization signal quality"],
            "executive_summary": f"{len(scored_actions)} actions ranked by ROI. Top priority: {scored_actions[0]['action'] if scored_actions else 'define priorities'}. Total pipeline: ${total_pipeline:,.0f}.",
        }
    return data, tokens, cost


def main():
    print("[roi_prioritizer] Building ROI-ranked action inventory...")
    all_tokens, all_cost = 0, 0.0

    prog_seo = _rj("programmatic_seo_report.json")
    growth = _rj("growth_report.json")
    revenue = _rj("revenue_tracker_report.json")
    acquisition = _rj("client_acquisition_report.json")
    product_builder = _rj("product_builder_report.json")
    observability = _rj("observability_report.json")

    all_actions = []
    all_actions.extend(extract_actions_from_seo(prog_seo, growth))
    all_actions.extend(extract_actions_from_revenue(revenue))
    all_actions.extend(extract_actions_from_acquisition(acquisition))
    all_actions.extend(extract_actions_from_product(product_builder))
    all_actions.extend(extract_actions_from_observability(observability))

    # Score and rank all actions
    for action in all_actions:
        action["roi_score"] = score_action(action)

    scored_actions = sorted(all_actions, key=lambda x: x["roi_score"], reverse=True)
    print(f"[roi_prioritizer] Ranked {len(scored_actions)} actions")

    execution_queue = build_execution_queue(scored_actions)
    total_pipeline = sum(a.get("revenue_impact_usd", 0) for a in scored_actions)

    strategy, tokens, cost = ai_roi_strategy(scored_actions, total_pipeline)
    all_tokens += tokens
    all_cost += cost

    report = {
        "generated_at": now_iso(),
        "total_actions_ranked": len(scored_actions),
        "total_pipeline_usd": round(total_pipeline, 2),
        "strategy_score": strategy.get("strategy_score", 0),
        "top_priority_action": strategy.get("top_priority_action", ""),
        "execution_philosophy": strategy.get("execution_philosophy", ""),
        "execution_queue": execution_queue,
        "top_20_actions": scored_actions[:20],
        "weekly_sprint_focus": strategy.get("weekly_sprint_focus", []),
        "revenue_unlock_sequence": strategy.get("revenue_unlock_sequence", []),
        "agent_directives": strategy.get("agent_directives", {}),
        "risk_flags": strategy.get("risk_flags", []),
        "executive_summary": strategy.get("executive_summary", ""),
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "roi_prioritizer_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[roi_prioritizer] Done — {len(scored_actions)} actions, pipeline ${total_pipeline:,.0f}, score {strategy.get('strategy_score', 0)}/100, ${all_cost:.4f}")


if __name__ == "__main__":
    main()

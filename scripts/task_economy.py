"""
MIFTEH OS — Task Economy
Every task has: expected ROI, execution cost, confidence, strategic value,
urgency, risk, and resource weight. AI allocates resources intelligently
to maximize portfolio value per dollar spent.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

# Token cost model (OpenAI gpt-4o-mini approximate)
TOKEN_COST_PER_1K = 0.00015   # input
OUTPUT_COST_PER_1K = 0.00060  # output
AVG_TOKENS_PER_TASK = 2500

# SEO value model: est. revenue per organic visit
SEO_VALUE_PER_VISIT = 0.35  # USD

# Resource weight by task type (normalized to 1.0)
RESOURCE_WEIGHTS = {
    "seo_page":          0.6,
    "seo_hub":           1.0,
    "content":           0.4,
    "optimization":      0.5,
    "campaign":          1.2,
    "qa_review":         0.3,
    "intel":             0.8,
    "emergency_response":1.5,
    "widget":            0.4,
    "category_page":     0.7,
}

# Urgency multipliers
URGENCY_MULTIPLIERS = {
    "critical": 3.0,
    "high":     2.0,
    "medium":   1.0,
    "low":      0.5,
}

# Strategic value by source
SOURCE_STRATEGIC_VALUE = {
    "manual":                  100,
    "emergency_response":       95,
    "campaign_engine":          85,
    "seo_opportunity_engine":   80,
    "analytics_intelligence":   75,
    "strategy_engine":          72,
    "roadmap":                  70,
    "swarm":                    65,
    "market_intelligence":      60,
    "experiment":               55,
}


def load_source(path: str) -> dict:
    f = Path(path)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def estimate_task_cost(task: dict) -> dict:
    task_type = task.get("type", "seo_page")
    resource_weight = RESOURCE_WEIGHTS.get(task_type, 0.7)
    est_tokens = int(AVG_TOKENS_PER_TASK * resource_weight)
    input_cost = (est_tokens * 0.7 / 1000) * TOKEN_COST_PER_1K
    output_cost = (est_tokens * 0.3 / 1000) * OUTPUT_COST_PER_1K
    total_cost = round(input_cost + output_cost, 5)
    return {
        "est_tokens": est_tokens,
        "est_cost_usd": total_cost,
        "resource_weight": resource_weight,
    }


def estimate_roi(task: dict, revenue_data: dict) -> dict:
    task_type = task.get("type", "seo_page")
    project = task.get("project", "")
    seo_target = task.get("seo_target", "")
    est_monthly_searches = task.get("est_monthly_searches", 500)

    # SEO value
    ctr_by_type = {"seo_hub": 0.10, "seo_page": 0.06, "content": 0.04, "category_page": 0.07}
    ctr = ctr_by_type.get(task_type, 0.05)
    monthly_clicks = est_monthly_searches * ctr
    seo_value_monthly = monthly_clicks * SEO_VALUE_PER_VISIT
    seo_value_annual = seo_value_monthly * 12

    # Direct revenue value from monetization model
    proj_revenue = revenue_data.get("projects", {}).get(project, {})
    portfolio_roi = proj_revenue.get("portfolio_roi", 10)
    direct_value = portfolio_roi * seo_value_monthly * 0.1  # 10% revenue attribution

    total_monthly = seo_value_monthly + direct_value
    total_annual = total_monthly * 12

    cost = estimate_task_cost(task)
    roi_ratio = round(total_annual / max(cost["est_cost_usd"], 0.001))

    return {
        "monthly_clicks_est": round(monthly_clicks),
        "seo_value_monthly_usd": round(seo_value_monthly, 2),
        "direct_value_monthly_usd": round(direct_value, 2),
        "total_value_monthly_usd": round(total_monthly, 2),
        "total_value_annual_usd": round(total_annual, 2),
        "roi_ratio": roi_ratio,
        "payback_days": round(cost["est_cost_usd"] / max(total_monthly / 30, 0.001)),
    }


def score_urgency(task: dict, alerts_data: dict) -> float:
    urgency_label = task.get("urgency", "medium")
    base = URGENCY_MULTIPLIERS.get(urgency_label, 1.0)

    # Boost if realtime event triggered this task
    if task.get("source") == "realtime_event_engine":
        base *= 1.5

    alert_level = alerts_data.get("alert_level", "normal")
    if alert_level in ("high", "critical") and task.get("type") == "emergency_response":
        base *= 2.0

    return round(base, 2)


def score_confidence(task: dict, evolution_data: dict) -> float:
    source = task.get("source", "")
    base = SOURCE_STRATEGIC_VALUE.get(source, 60) / 100.0

    system_maturity = evolution_data.get("system_maturity_score", 50) / 100
    confidence = base * 0.7 + system_maturity * 0.3
    return round(min(1.0, confidence), 3)


def compute_economy_score(task: dict, roi: dict, urgency: float,
                          confidence: float, risk_score: float) -> float:
    roi_norm = min(1.0, roi["roi_ratio"] / 1000)
    urgency_norm = urgency / 3.0
    confidence_norm = confidence
    risk_norm = 1.0 - (risk_score / 100)
    value_norm = min(1.0, roi["total_value_annual_usd"] / 5000)

    score = (
        roi_norm        * 0.30 +
        value_norm      * 0.25 +
        urgency_norm    * 0.20 +
        confidence_norm * 0.15 +
        risk_norm       * 0.10
    ) * 100

    return round(score, 1)


def build_optimal_portfolio(scored_tasks: list, total_budget_usd: float) -> dict:
    """Knapsack-style optimal task selection within token/cost budget."""
    selected = []
    remaining_budget = total_budget_usd
    total_value = 0.0

    # Sort by economy score
    for task in sorted(scored_tasks, key=lambda x: x["economy_score"], reverse=True):
        cost = task["cost_model"]["est_cost_usd"]
        if remaining_budget >= cost:
            selected.append(task)
            remaining_budget -= cost
            total_value += task["roi_model"]["total_value_annual_usd"]
        if len(selected) >= 15:  # max 15 tasks per cycle
            break

    return {
        "selected_tasks": selected,
        "total_tasks": len(selected),
        "budget_used_usd": round(total_budget_usd - remaining_budget, 4),
        "budget_remaining_usd": round(remaining_budget, 4),
        "total_est_annual_value_usd": round(total_value, 2),
        "portfolio_roi_ratio": round(total_value / max(total_budget_usd - remaining_budget, 0.001)),
    }


def ai_economy_analysis(portfolio: dict, scored_tasks: list) -> dict:
    system = (
        "You are the MIFTEH OS task economy AI. Analyze the selected task portfolio "
        "for ROI maximization and resource efficiency."
    )
    prompt = f"""Selected task portfolio: {portfolio['total_tasks']} tasks
Budget used: ${portfolio['budget_used_usd']:.4f}
Est. annual value: ${portfolio['total_est_annual_value_usd']:,.0f}
Portfolio ROI ratio: {portfolio['portfolio_roi_ratio']:,}×

Top 5 tasks by economy score:
{json.dumps([{k: v for k, v in t.items() if k not in ('cost_model',)} for t in scored_tasks[:5]], indent=2)}

Provide economy intelligence. Respond with JSON:
{{
  "economy_health": "excellent|good|fair|poor",
  "economy_score": 0,
  "budget_efficiency": "description",
  "value_concentration_risk": "description",
  "reallocation_suggestions": [
    {{"from": "task/project", "to": "task/project", "rationale": "why"}}
  ],
  "economy_insights": ["insight 1", "insight 2"],
  "next_cycle_budget_recommendation_usd": 0.0
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=700)
    if ok and data:
        return data
    return {
        "economy_health": "good",
        "economy_score": 70,
        "budget_efficiency": "Standard",
        "value_concentration_risk": "Low",
        "reallocation_suggestions": [],
        "economy_insights": [],
        "next_cycle_budget_recommendation_usd": 1.0,
    }


def main():
    print("[economy] Starting task economy engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    revenue_data   = load_source("memory/revenue_report.json")
    alerts_data    = load_source("memory/realtime_alerts.json")
    evolution_data = load_source("memory/evolution_report.json")
    gov_data       = load_source("memory/governance_report.json")
    bus_data       = load_source("memory/agent_bus.json")
    intel_data     = load_source("memory/analytics_intelligence.json")

    # Build task list from all sources
    all_tasks = []
    for t in bus_data.get("task_queue", [])[:30]:
        if t.get("status") == "queued":
            all_tasks.append(t)
    for d in intel_data.get("autonomous_decisions", [])[:20]:
        all_tasks.append({
            "task_id": d.get("decision_id", ""),
            "type": d.get("type", "seo_page"),
            "project": d.get("project", ""),
            "title": d.get("title", ""),
            "source": d.get("source", "analytics_intelligence"),
            "priority": d.get("priority_weight", 5),
            "est_monthly_searches": 500,
        })

    # Deduplicate
    seen, unique = set(), []
    for t in all_tasks:
        tid = t.get("task_id", "")
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(t)
    all_tasks = unique

    print(f"  [economy] Scoring {len(all_tasks)} tasks...")

    # Score each task
    scored_tasks = []
    for task in all_tasks:
        cost = estimate_task_cost(task)
        roi = estimate_roi(task, revenue_data)
        urgency = score_urgency(task, alerts_data)
        confidence = score_confidence(task, evolution_data)

        # Risk from governance report
        gov_blocked = {a.get("decision_id", "") for a in gov_data.get("blocked_actions", [])}
        if task.get("task_id") in gov_blocked:
            continue
        risk_score = 20.0  # default low risk for SEO tasks

        economy_score = compute_economy_score(task, roi, urgency, confidence, risk_score)

        scored_tasks.append({
            **task,
            "economy_score": economy_score,
            "cost_model": cost,
            "roi_model": roi,
            "urgency_score": urgency,
            "confidence_score": confidence,
            "risk_score": risk_score,
        })

    scored_tasks.sort(key=lambda x: x["economy_score"], reverse=True)

    # Build optimal portfolio
    cycle_budget = gov_data.get("mode_config", {}).get("max_cost_per_cycle_usd", 1.0)
    portfolio = build_optimal_portfolio(scored_tasks, cycle_budget)
    print(f"  [economy] Portfolio: {portfolio['total_tasks']} tasks selected")
    print(f"  [economy] Budget used: ${portfolio['budget_used_usd']:.4f} / ${cycle_budget:.2f}")
    print(f"  [economy] Est. annual value: ${portfolio['total_est_annual_value_usd']:,.0f}")

    # AI economy analysis
    ai_analysis = ai_economy_analysis(portfolio, scored_tasks)
    health = ai_analysis.get("economy_health", "good")
    print(f"  [economy] Economy health: {health} | score: {ai_analysis.get('economy_score', 0)}/100")

    # Summary by project
    by_project: dict = {}
    for t in scored_tasks:
        p = t.get("project", "unknown")
        if p not in by_project:
            by_project[p] = {"count": 0, "total_annual_value_usd": 0, "total_cost_usd": 0}
        by_project[p]["count"] += 1
        by_project[p]["total_annual_value_usd"] += t["roi_model"]["total_value_annual_usd"]
        by_project[p]["total_cost_usd"] += t["cost_model"]["est_cost_usd"]

    report = {
        "generated_at": now_iso(),
        "tasks_scored": len(scored_tasks),
        "portfolio": portfolio,
        "ai_analysis": ai_analysis,
        "by_project": by_project,
        "top_tasks": [{k: v for k, v in t.items() if k != "cost_model"} for t in scored_tasks[:15]],
        "total_est_portfolio_annual_value_usd": sum(
            t["roi_model"]["total_value_annual_usd"] for t in scored_tasks
        ),
    }

    out = MEMORY_DIR / "task_economy_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[economy] {len(scored_tasks)} tasks scored | portfolio ROI {portfolio['portfolio_roi_ratio']:,}×")
    print(f"[economy] Report → {out}")
    return report


if __name__ == "__main__":
    main()

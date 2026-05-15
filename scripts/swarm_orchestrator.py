"""
MIFTEH OS — Swarm Orchestrator
Coordinates multiple specialized AI agents on a single mission.
Each agent runs with a domain-expert system prompt; outputs are merged,
conflicts resolved, and a final implementation plan synthesized.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
SWARM_DIR = MEMORY_DIR / "swarm"

AGENT_ROLES = {
    "seo": {
        "name": "SEO Agent",
        "system": (
            "You are an expert SEO agent. Analyze missions from an SEO perspective. "
            "Focus on: keyword opportunities, on-page optimization, technical SEO, content gaps, "
            "internal linking, page speed signals, meta optimization, structured data. "
            "Output specific, actionable improvements with estimated traffic impact."
        ),
    },
    "ux": {
        "name": "UX Agent",
        "system": (
            "You are an expert UX/UI agent. Analyze missions from a UX perspective. "
            "Focus on: user flow, navigation clarity, CTAs, visual hierarchy, mobile experience, "
            "accessibility, engagement patterns, friction reduction, conversion optimization. "
            "Output specific improvements with estimated engagement impact."
        ),
    },
    "content": {
        "name": "Content Agent",
        "system": (
            "You are an expert content strategy agent. Focus on: content gaps, topic clusters, "
            "user intent alignment, content freshness, E-E-A-T signals, readability, content depth "
            "vs competition, headline optimization. Output content improvements with authority impact."
        ),
    },
    "monetization": {
        "name": "Monetization Agent",
        "system": (
            "You are an expert monetization agent. Focus on: ad placement optimization, RPM improvement, "
            "conversion funnels, upsell opportunities, affiliate potential, premium features, "
            "traffic monetization. Output improvements with estimated revenue impact (USD/month)."
        ),
    },
    "analytics": {
        "name": "Analytics Agent",
        "system": (
            "You are an expert analytics agent. Focus on: conversion bottlenecks, user behavior patterns, "
            "traffic sources, engagement metrics, A/B test opportunities, funnel analysis, "
            "cohort patterns. Output data-driven improvements with measurable success metrics."
        ),
    },
    "performance": {
        "name": "Performance Agent",
        "system": (
            "You are an expert performance agent. Focus on: Core Web Vitals, LCP/FID/CLS improvement, "
            "asset optimization, caching, lazy loading, script optimization, render blocking, bundle size. "
            "Output specific improvements with estimated score improvements."
        ),
    },
}


def run_agent(role: str, mission: str, project: str, context: str) -> dict:
    agent = AGENT_ROLES[role]
    prompt = f"""Project: {project}
Mission: {mission}
Context:
{context}

Analyze this mission from your specialized perspective ({agent['name']}).
Respond with a JSON object:
{{
  "proposals": [
    {{
      "title": "short proposal title",
      "description": "what to do and how",
      "impact": "expected impact",
      "effort": "low|medium|high",
      "confidence": 0,
      "priority": 1,
      "implementation_hint": "specific HTML/content guidance"
    }}
  ],
  "conflicts": ["any conflicts with other agents approaches"],
  "dependencies": ["what this needs from other agents"],
  "estimated_impact": {{
    "traffic_delta_pct": 0,
    "revenue_delta_usd": 0,
    "ux_score_delta": 0,
    "seo_score_delta": 0
  }}
}}
Return ONLY valid JSON. Max 5 proposals."""

    try:
        data, _, _, ok = generate_json(agent["system"], prompt, max_tokens=1200)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return {"role": role, "agent": agent["name"], "success": True, **data}
    except Exception as e:
        return {
            "role": role,
            "agent": agent["name"],
            "success": False,
            "proposals": [],
            "conflicts": [],
            "dependencies": [],
            "estimated_impact": {
                "traffic_delta_pct": 0, "revenue_delta_usd": 0,
                "ux_score_delta": 0, "seo_score_delta": 0,
            },
            "error": str(e),
        }


def resolve_conflicts(agent_results: list) -> dict:
    all_proposals = []
    for role_data in agent_results:
        if not role_data.get("success"):
            continue
        for p in role_data.get("proposals", []):
            all_proposals.append({
                **p,
                "source_role": role_data["role"],
                "source_agent": role_data["agent"],
            })

    all_proposals.sort(
        key=lambda x: x.get("priority", 5) * x.get("confidence", 50),
        reverse=True,
    )

    total_traffic = sum(
        r.get("estimated_impact", {}).get("traffic_delta_pct", 0)
        for r in agent_results if r.get("success")
    )
    total_revenue = sum(
        r.get("estimated_impact", {}).get("revenue_delta_usd", 0)
        for r in agent_results if r.get("success")
    )
    total_ux = sum(
        r.get("estimated_impact", {}).get("ux_score_delta", 0)
        for r in agent_results if r.get("success")
    )
    total_seo = sum(
        r.get("estimated_impact", {}).get("seo_score_delta", 0)
        for r in agent_results if r.get("success")
    )

    all_conflicts = []
    for r in agent_results:
        all_conflicts.extend(r.get("conflicts", []))

    return {
        "ranked_proposals": all_proposals[:15],
        "top_5": all_proposals[:5],
        "conflicts_detected": all_conflicts,
        "aggregate_impact": {
            "traffic_delta_pct": round(total_traffic, 1),
            "revenue_delta_usd": round(total_revenue, 2),
            "ux_score_delta": round(total_ux, 1),
            "seo_score_delta": round(total_seo, 1),
        },
    }


def synthesize_plan(mission: str, project: str, resolved: dict) -> dict:
    system = (
        "You are the MIFTEH OS swarm orchestrator. Synthesize multiple AI agents' proposals "
        "into one coherent implementation plan. Resolve conflicts, sequence tasks logically, "
        "and produce a specific HTML/content plan."
    )
    prompt = f"""Mission: {mission}
Project: {project}

Top proposals from all agents:
{json.dumps(resolved["top_5"], indent=2)}

Conflicts detected:
{json.dumps(resolved["conflicts_detected"], indent=2)}

Synthesize into ONE coherent implementation plan. Respond with JSON:
{{
  "plan_title": "concise plan name",
  "plan_summary": "2-3 sentences describing the integrated approach",
  "implementation_steps": [
    {{
      "step": 1,
      "action": "what to do",
      "agent_source": "which agent",
      "html_component": "what HTML to add/modify",
      "rationale": "why this step"
    }}
  ],
  "conflict_resolution": "how conflicts were resolved",
  "success_metrics": ["metric 1", "metric 2"],
  "estimated_30d_impact": {{
    "traffic_increase_pct": 0,
    "revenue_increase_usd": 0,
    "seo_score_improvement": 0
  }},
  "execution_priority": "high|medium|low",
  "recommended_feature_type": "page|widget|optimization|content"
}}
Return ONLY valid JSON."""

    try:
        data, _, _, ok = generate_json(system, prompt, max_tokens=1500)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return data
    except Exception as e:
        return {
            "plan_title": f"Swarm Plan: {mission[:50]}",
            "plan_summary": "Synthesized from agent proposals.",
            "implementation_steps": [
                {
                    "step": i + 1,
                    "action": p["title"],
                    "agent_source": p.get("source_role", ""),
                    "html_component": p.get("implementation_hint", ""),
                    "rationale": p.get("description", ""),
                }
                for i, p in enumerate(resolved["top_5"][:5])
            ],
            "conflict_resolution": "Sequential prioritization by confidence score",
            "success_metrics": ["Traffic increase", "Revenue increase"],
            "estimated_30d_impact": {
                "traffic_increase_pct": 5, "revenue_increase_usd": 0, "seo_score_improvement": 2,
            },
            "execution_priority": "medium",
            "recommended_feature_type": "page",
            "error": str(e),
        }


def run_swarm(mission: str, project: str, agents: list = None, context: str = "") -> dict:
    if agents is None:
        agents = list(AGENT_ROLES.keys())

    print(f"[swarm] Mission: {mission[:70]}")
    print(f"[swarm] Project: {project} | Agents: {', '.join(agents)}")

    SWARM_DIR.mkdir(parents=True, exist_ok=True)

    agent_results = []
    for role in agents:
        if role not in AGENT_ROLES:
            continue
        print(f"  [swarm] Running {AGENT_ROLES[role]['name']}...")
        result = run_agent(role, mission, project, context)
        agent_results.append(result)
        if result["success"]:
            n = len(result["proposals"])
            impact = result.get("estimated_impact", {})
            print(f"    → {n} proposals | traffic +{impact.get('traffic_delta_pct', 0)}%")
        else:
            print(f"    → Failed: {result.get('error', 'unknown')[:60]}")

    resolved = resolve_conflicts(agent_results)
    print(
        f"[swarm] Resolved {len(resolved['ranked_proposals'])} proposals, "
        f"{len(resolved['conflicts_detected'])} conflicts"
    )

    plan = synthesize_plan(mission, project, resolved)
    print(f"[swarm] Plan: {plan.get('plan_title', 'Swarm Plan')}")

    mission_id = f"{project}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    record = {
        "mission_id": mission_id,
        "mission": mission,
        "project": project,
        "generated_at": now_iso(),
        "agents_used": agents,
        "agent_results": agent_results,
        "resolved": resolved,
        "implementation_plan": plan,
    }
    (SWARM_DIR / f"{mission_id}.json").write_text(json.dumps(record, indent=2))
    return record


def build_swarm_summary() -> dict:
    missions = []
    if SWARM_DIR.exists():
        for f in sorted(SWARM_DIR.glob("*.json"), reverse=True)[:20]:
            try:
                missions.append(json.loads(f.read_text()))
            except Exception:
                pass

    return {
        "generated_at": now_iso(),
        "total_missions": len(missions),
        "recent_missions": [
            {
                "mission_id": m["mission_id"],
                "mission": m["mission"],
                "project": m["project"],
                "agents_used": m["agents_used"],
                "plan_title": m.get("implementation_plan", {}).get("plan_title", ""),
                "execution_priority": m.get("implementation_plan", {}).get("execution_priority", ""),
                "estimated_30d_impact": m.get("implementation_plan", {}).get("estimated_30d_impact", {}),
                "top_proposals": m.get("resolved", {}).get("top_5", [])[:3],
                "aggregate_impact": m.get("resolved", {}).get("aggregate_impact", {}),
                "generated_at": m["generated_at"],
            }
            for m in missions[:10]
        ],
    }


def main():
    print("[swarm] Starting swarm orchestrator...")

    target_project = os.environ.get("TARGET_PROJECT", "all")
    mission_override = os.environ.get("SWARM_MISSION", "")

    intel_file = Path("memory/analytics_intelligence.json")
    intel = {}
    if intel_file.exists():
        try:
            intel = json.loads(intel_file.read_text())
        except Exception:
            pass

    default_missions = {
        "yallaplays": (
            "Increase YallaPlays organic traffic and ad revenue through "
            "comprehensive SEO and UX improvements"
        ),
        "fionera": (
            "Improve Fionera user engagement and retention through better "
            "data visualization and personalization"
        ),
        "mifteh": (
            "Strengthen miftehos.com authority and conversion through "
            "content depth and trust signals"
        ),
    }

    projects = (
        ["yallaplays", "fionera", "mifteh"] if target_project == "all" else [target_project]
    )

    for project in projects:
        mission = mission_override or default_missions.get(
            project, f"Improve {project} performance and growth"
        )
        context_parts = []
        proj_intel = intel.get("projects", {}).get(project, {})
        if proj_intel:
            overview = proj_intel.get("overview", {})
            context_parts.append(
                f"Monthly visits: {overview.get('monthly_visits', 'unknown')}"
            )
            context_parts.append(
                f"Top opportunity: {proj_intel.get('top_opportunity', 'unknown')}"
            )
        context = "\n".join(context_parts) or "No analytics context available."
        run_swarm(mission, project, context=context)
        print()

    summary = build_swarm_summary()
    summary_path = Path("memory/swarm_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"[swarm] Summary → {summary_path} ({summary['total_missions']} missions total)")
    return summary


if __name__ == "__main__":
    main()

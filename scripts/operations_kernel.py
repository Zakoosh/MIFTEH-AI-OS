"""
MIFTEH OS — Operations Kernel
Central nervous system for all AI activity. Tracks live agent state,
active missions, execution graph, token flow, memory flow, task queues,
execution bottlenecks, and swarm activity. The single source of truth
for the autonomous company's operational state.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
AGENTS_DIR = MEMORY_DIR / "agents"
KERNEL_FILE = MEMORY_DIR / "kernel_state.json"

AGENT_IDS = ["orchestrator", "strategist", "executor", "reviewer",
             "optimizer", "monetizer", "seo", "analytics"]

COMPANY_MODE_FILE = MEMORY_DIR / "company_mode.json"

COMPANY_MODES = {
    "assisted":        {"label": "Assisted",        "autonomy": 1, "color": "#6b7280"},
    "semi_autonomous": {"label": "Semi-Autonomous",  "autonomy": 2, "color": "#3b82f6"},
    "autonomous":      {"label": "Autonomous",       "autonomy": 3, "color": "#10b981"},
    "civilization":    {"label": "Civilization Mode","autonomy": 4, "color": "#8b5cf6"},
}


def load_json(path: str) -> dict:
    f = Path(path)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def load_agent_states() -> dict:
    states = {}
    for agent_id in AGENT_IDS:
        agent = load_json(f"memory/agents/{agent_id}.json")
        states[agent_id] = {
            "id": agent_id,
            "name": agent.get("name", agent_id.title()),
            "role": agent.get("role", agent_id),
            "tier": agent.get("tier", 3),
            "confidence": agent.get("confidence", 0.75),
            "skills": agent.get("skills", {}),
            "total_missions": agent.get("total_missions", 0),
            "success_rate": agent.get("success_rate", 1.0),
            "last_active": agent.get("last_active", ""),
            "evolution_cycle": agent.get("evolution_cycle", 0),
            "performance_score": agent.get("last_performance_score", 50),
            "status": "active" if agent.get("last_active") else "initializing",
            "current_goals": agent.get("goals", [])[:2],
        }
    return states


def compute_token_flow(all_sources: dict) -> dict:
    total_tokens = 0
    total_cost = 0.0
    by_source: dict = {}

    # From self-improvement report
    si = all_sources.get("self_improvement", {})
    raw = si.get("raw_metrics", {})
    t = raw.get("total_tokens", 0)
    c = raw.get("total_cost_usd", 0.0)
    if t:
        by_source["self_improvement"] = {"tokens": t, "cost_usd": c}
        total_tokens += t
        total_cost += c

    # From economy report
    economy = all_sources.get("economy", {})
    econ_budget = economy.get("portfolio", {}).get("budget_used_usd", 0)
    if econ_budget:
        by_source["task_economy"] = {"tokens": 0, "cost_usd": econ_budget}
        total_cost += econ_budget

    return {
        "total_tokens_all_time": total_tokens,
        "total_cost_all_time_usd": round(total_cost, 4),
        "by_source": by_source,
        "est_tokens_per_day": max(1, total_tokens // 30) if total_tokens else 5000,
        "est_cost_per_day_usd": round(total_cost / 30, 4) if total_cost else 0.05,
    }


def compute_memory_flow(all_sources: dict) -> dict:
    memory_files = list(MEMORY_DIR.glob("*.json"))
    agent_files = list(AGENTS_DIR.glob("*.json")) if AGENTS_DIR.exists() else []

    total_size_kb = sum(f.stat().st_size for f in memory_files + agent_files) / 1024

    key_files = {}
    for fname in ["agent_bus.json", "analytics_intelligence.json", "cognition_state.json",
                  "governance_state.json", "runtime_state.json", "knowledge_graph.json"]:
        fpath = MEMORY_DIR / fname
        if fpath.exists():
            key_files[fname] = round(fpath.stat().st_size / 1024, 1)

    return {
        "total_memory_files": len(memory_files) + len(agent_files),
        "total_size_kb": round(total_size_kb, 1),
        "agent_memory_files": len(agent_files),
        "key_file_sizes_kb": key_files,
        "memory_health": "healthy" if total_size_kb < 10000 else "large",
    }


def detect_bottlenecks(all_sources: dict, agent_states: dict) -> list:
    bottlenecks = []

    # Runtime bottlenecks
    runtime = all_sources.get("runtime", {})
    balance = runtime.get("workload_balance", {})
    for wtype in balance.get("bottlenecks", []):
        bottlenecks.append({
            "type": "worker_saturation",
            "component": f"worker_{wtype}",
            "severity": "medium",
            "description": f"Worker pool '{wtype}' at full capacity",
        })

    # Task economy bottlenecks
    economy = all_sources.get("economy", {})
    budget_remaining = economy.get("portfolio", {}).get("budget_remaining_usd", 1.0)
    if budget_remaining < 0.10:
        bottlenecks.append({
            "type": "budget_exhausted",
            "component": "task_economy",
            "severity": "high",
            "description": f"Only ${budget_remaining:.3f} remaining in cycle budget",
        })

    # Governance bottlenecks
    governance = all_sources.get("governance", {})
    blocked = governance.get("blocked", 0)
    total_eval = governance.get("decisions_evaluated", 1)
    if blocked > total_eval * 0.5 and total_eval > 0:
        bottlenecks.append({
            "type": "governance_blocking",
            "component": "governance_engine",
            "severity": "high",
            "description": f"{blocked}/{total_eval} actions blocked by governance",
        })

    # Cognition health
    cognition = all_sources.get("cognition", {})
    health = cognition.get("health_score", 70)
    if health < 40:
        bottlenecks.append({
            "type": "low_cognition_health",
            "component": "cognition_engine",
            "severity": "medium",
            "description": f"Cognition health at {health}/100 — strategic quality degraded",
        })

    # Bus escalations
    bus = all_sources.get("bus", {})
    pending_esc = sum(1 for e in bus.get("escalation_queue", []) if not e.get("resolved"))
    if pending_esc > 3:
        bottlenecks.append({
            "type": "escalation_backlog",
            "component": "agent_bus",
            "severity": "medium",
            "description": f"{pending_esc} unresolved escalations pending",
        })

    return bottlenecks


def compute_swarm_activity(all_sources: dict, agent_states: dict) -> dict:
    bus = all_sources.get("bus", {})
    runtime = all_sources.get("runtime", {})
    evolution = all_sources.get("agent_evolution", {})

    active_tasks = len([t for t in bus.get("task_queue", []) if t.get("status") == "queued"])
    dispatched = runtime.get("tasks_dispatched", 0)
    completed = runtime.get("tasks_completed", 0)
    agents_active = sum(1 for a in agent_states.values() if a.get("status") == "active")
    avg_perf = sum(a.get("performance_score", 50) for a in agent_states.values()) / max(len(agent_states), 1)

    return {
        "active_agents": agents_active,
        "total_agents": len(agent_states),
        "active_tasks": active_tasks,
        "tasks_dispatched_cycle": dispatched,
        "tasks_completed_total": completed,
        "avg_agent_performance": round(avg_perf, 1),
        "swarm_health": "excellent" if avg_perf >= 80 else "good" if avg_perf >= 60 else "degraded",
        "evolution_cycles": evolution.get("agents_evolved", 0),
    }


def ai_kernel_analysis(bottlenecks: list, swarm: dict, token_flow: dict,
                       company_mode: str) -> dict:
    system = (
        "You are the MIFTEH OS operations kernel AI. "
        "Analyze the current state of the autonomous company and provide "
        "operational intelligence to maintain peak performance."
    )
    prompt = f"""Company mode: {company_mode}
Swarm health: {swarm['swarm_health']} | Active agents: {swarm['active_agents']}/{swarm['total_agents']}
Active tasks: {swarm['active_tasks']} | Avg performance: {swarm['avg_agent_performance']}/100
Bottlenecks detected: {len(bottlenecks)}
Token flow: {token_flow['est_tokens_per_day']:,}/day | ${token_flow['est_cost_per_day_usd']:.4f}/day

Bottlenecks: {json.dumps(bottlenecks, indent=2)}

Provide operational assessment. Respond with JSON:
{{
  "operational_status": "nominal|degraded|critical|excellent",
  "ops_score": 0,
  "company_velocity": "description of how fast the company is moving",
  "immediate_actions": ["action 1", "action 2"],
  "optimization_opportunities": ["opp 1", "opp 2"],
  "predicted_issues": [
    {{"issue": "description", "probability": 0.0, "timeline": "24h|48h|7d"}}
  ],
  "mode_recommendation": "assisted|semi_autonomous|autonomous|civilization",
  "kernel_insight": "single most important operational insight"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=900)
    if ok and data:
        return data
    return {
        "operational_status": "nominal",
        "ops_score": 70,
        "company_velocity": "Standard autonomous execution pace",
        "immediate_actions": [],
        "optimization_opportunities": [],
        "predicted_issues": [],
        "mode_recommendation": company_mode,
        "kernel_insight": "System operational — collecting more data for deeper analysis",
    }


def build_execution_graph(all_sources: dict) -> dict:
    """Build a simplified execution dependency graph."""
    nodes = []
    edges = []

    # Agent nodes
    for agent_id in AGENT_IDS:
        nodes.append({"id": f"agent:{agent_id}", "type": "agent", "label": agent_id})

    # Script pipeline nodes
    pipeline = [
        ("web_intel", "seo_opp"), ("seo_opp", "campaign"), ("campaign", "executor"),
        ("competitor_memory", "social_signals"), ("social_signals", "traffic_intel"),
        ("traffic_intel", "monetization"), ("monetization", "task_economy"),
        ("cognition", "governance"), ("governance", "runtime"), ("runtime", "agent_bus"),
    ]
    for src, tgt in pipeline:
        if not any(n["id"] == f"script:{src}" for n in nodes):
            nodes.append({"id": f"script:{src}", "type": "script", "label": src})
        if not any(n["id"] == f"script:{tgt}" for n in nodes):
            nodes.append({"id": f"script:{tgt}", "type": "script", "label": tgt})
        edges.append({"source": f"script:{src}", "target": f"script:{tgt}", "type": "feeds"})

    # Agent → script assignments
    agent_script_map = {
        "orchestrator": "agent_bus", "strategist": "cognition",
        "executor": "runtime", "reviewer": "governance",
        "optimizer": "agent_evolution", "monetizer": "monetization",
        "seo": "seo_opp", "analytics": "web_intel",
    }
    for agent_id, script in agent_script_map.items():
        edges.append({
            "source": f"agent:{agent_id}",
            "target": f"script:{script}",
            "type": "manages",
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def load_or_create_company_mode() -> str:
    if COMPANY_MODE_FILE.exists():
        try:
            data = json.loads(COMPANY_MODE_FILE.read_text())
            return data.get("mode", "semi_autonomous")
        except Exception:
            pass
    return os.environ.get("COMPANY_MODE", "semi_autonomous")


def main():
    print("[kernel] Starting operations kernel...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    company_mode = load_or_create_company_mode()
    mode_info = COMPANY_MODES.get(company_mode, COMPANY_MODES["semi_autonomous"])
    print(f"  [kernel] Company mode: {mode_info['label']} (autonomy level {mode_info['autonomy']}/4)")

    # Load all intelligence sources
    all_sources = {
        "self_improvement": load_json("memory/self_improvement_report.json"),
        "cognition":        load_json("memory/cognition_report.json"),
        "governance":       load_json("memory/governance_report.json"),
        "runtime":          load_json("memory/runtime_report.json"),
        "economy":          load_json("memory/task_economy_report.json"),
        "bus":              load_json("memory/agent_bus.json"),
        "agent_evolution":  load_json("memory/agent_evolution_report.json"),
        "knowledge_graph":  load_json("memory/knowledge_graph.json"),
        "realtime_alerts":  load_json("memory/realtime_alerts.json"),
    }
    loaded = sum(1 for v in all_sources.values() if v)
    print(f"  [kernel] {loaded} intelligence sources loaded")

    # Gather agent states
    agent_states = load_agent_states()
    print(f"  [kernel] {len(agent_states)} agents registered")

    # Compute subsystem metrics
    token_flow = compute_token_flow(all_sources)
    memory_flow = compute_memory_flow(all_sources)
    bottlenecks = detect_bottlenecks(all_sources, agent_states)
    swarm = compute_swarm_activity(all_sources, agent_states)
    exec_graph = build_execution_graph(all_sources)

    print(f"  [kernel] Swarm: {swarm['swarm_health']} | {swarm['active_agents']} active agents")
    print(f"  [kernel] {len(bottlenecks)} bottlenecks detected")
    print(f"  [kernel] Memory: {memory_flow['total_size_kb']:.0f} KB across {memory_flow['total_memory_files']} files")

    # AI kernel analysis
    print("  [kernel] Running AI operational analysis...")
    ai_analysis = ai_kernel_analysis(bottlenecks, swarm, token_flow, company_mode)
    ops_status = ai_analysis.get("operational_status", "nominal")
    ops_score = ai_analysis.get("ops_score", 70)
    print(f"    Status: {ops_status.upper()} | Score: {ops_score}/100")
    print(f"    Insight: {ai_analysis.get('kernel_insight', '')[:80]}")

    # Update company mode file
    COMPANY_MODE_FILE.write_text(json.dumps({
        "mode": company_mode,
        "label": mode_info["label"],
        "autonomy_level": mode_info["autonomy"],
        "updated_at": now_iso(),
        "ai_recommendation": ai_analysis.get("mode_recommendation", company_mode),
    }, indent=2))

    report = {
        "generated_at": now_iso(),
        "company_mode": company_mode,
        "mode_info": mode_info,
        "operational_status": ops_status,
        "ops_score": ops_score,
        "agent_states": agent_states,
        "swarm_activity": swarm,
        "token_flow": token_flow,
        "memory_flow": memory_flow,
        "bottlenecks": bottlenecks,
        "execution_graph": exec_graph,
        "ai_analysis": ai_analysis,
        "intelligence_sources_loaded": loaded,
    }

    out = MEMORY_DIR / "kernel_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[kernel] Status: {ops_status} | Swarm: {swarm['swarm_health']} | Mode: {mode_info['label']}")
    print(f"[kernel] Report → {out}")
    return report


if __name__ == "__main__":
    main()

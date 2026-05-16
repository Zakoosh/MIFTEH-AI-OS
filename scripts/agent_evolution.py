"""
MIFTEH OS — Agent Evolution Engine
Agents improve their own prompts, strategy, execution quality, collaboration,
and reasoning chains based on observed performance. Persistent improvement
across runs — agents get smarter every cycle.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
AGENTS_DIR = MEMORY_DIR / "agents"
EVOLUTION_LOG = MEMORY_DIR / "agent_evolution_log.json"

AGENT_IDS = ["orchestrator", "strategist", "executor", "reviewer",
             "optimizer", "monetizer", "seo", "analytics"]

# Dimensions agents can evolve across
EVOLUTION_DIMENSIONS = {
    "prompt_quality":       {"weight": 0.25, "description": "Quality and clarity of agent prompts"},
    "strategy_accuracy":    {"weight": 0.20, "description": "Accuracy of strategic recommendations"},
    "execution_quality":    {"weight": 0.20, "description": "Quality of task execution outputs"},
    "collaboration":        {"weight": 0.15, "description": "Effectiveness of inter-agent coordination"},
    "reasoning_depth":      {"weight": 0.10, "description": "Depth and correctness of reasoning chains"},
    "confidence_calibration": {"weight": 0.10, "description": "How well confidence matches actual outcomes"},
}


def load_agent(agent_id: str) -> dict:
    f = AGENTS_DIR / f"{agent_id}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"id": agent_id, "confidence": 0.75, "skills": {}, "execution_history": [],
            "memory": {}, "total_missions": 0, "success_rate": 1.0}


def save_agent(agent: dict) -> None:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    agent["last_active"] = now_iso()
    (AGENTS_DIR / f"{agent['id']}.json").write_text(json.dumps(agent, indent=2))


def load_performance_data() -> dict:
    sources = {}
    for name, path in [
        ("evolution",    "memory/evolution_report.json"),
        ("experiments",  "memory/experiment_summary.json"),
        ("bus",          "memory/agent_bus.json"),
        ("cognition",    "memory/cognition_report.json"),
        ("governance",   "memory/governance_report.json"),
        ("runtime",      "memory/runtime_report.json"),
        ("economy",      "memory/task_economy_report.json"),
    ]:
        f = Path(path)
        if f.exists():
            try:
                sources[name] = json.loads(f.read_text())
            except Exception:
                pass
    return sources


def score_agent_performance(agent: dict, perf_data: dict) -> dict:
    """Score an agent's current performance across all dimensions."""
    scores = {}

    runtime = perf_data.get("runtime", {})
    economy = perf_data.get("economy", {})
    evolution = perf_data.get("evolution", {})
    cognition = perf_data.get("cognition", {})

    # Prompt quality — from evolution report prompt improvements
    prompt_suggestions = evolution.get("prompt_improvements", [])
    scores["prompt_quality"] = max(40, 90 - len(prompt_suggestions) * 8)

    # Strategy accuracy — from cognition health score
    health = cognition.get("health_score", 50)
    scores["strategy_accuracy"] = health

    # Execution quality — from runtime completions
    completed = runtime.get("tasks_completed", 0)
    failed = runtime.get("tasks_failed", 0)
    total = completed + failed
    scores["execution_quality"] = round(completed / max(total, 1) * 100) if total else 70

    # Collaboration — from bus delegation success
    bus = perf_data.get("bus", {})
    delegations = len(bus.get("delegation_log", []))
    scores["collaboration"] = min(90, 60 + delegations * 5)

    # Reasoning depth — from cognition chain confidence
    chain_conf = cognition.get("chain_confidence", 0.6)
    scores["reasoning_depth"] = round(chain_conf * 100)

    # Confidence calibration — compare agent's stated confidence to success_rate
    stated = agent.get("confidence", 0.75)
    actual_sr = agent.get("success_rate", 1.0)
    calibration_error = abs(stated - actual_sr)
    scores["confidence_calibration"] = round((1 - calibration_error) * 100)

    # Weighted composite
    composite = sum(
        scores[dim] * EVOLUTION_DIMENSIONS[dim]["weight"]
        for dim in EVOLUTION_DIMENSIONS
        if dim in scores
    )

    return {
        "dimension_scores": scores,
        "composite_score": round(composite, 1),
        "vs_previous": agent.get("last_performance_score", composite) - composite,
    }


def generate_agent_improvements(agent: dict, performance: dict, perf_data: dict) -> dict:
    system = (
        f"You are evolving the {agent.get('name', agent['id'])} AI agent in MIFTEH OS. "
        f"This agent's role: {agent.get('role', agent['id'])}. "
        "Generate specific improvements to make this agent more effective."
    )
    weak_dims = sorted(
        performance["dimension_scores"].items(),
        key=lambda x: x[1]
    )[:3]

    prompt = f"""Agent: {agent['id']} ({agent.get('name', '')})
Current skills: {json.dumps(agent.get('skills', {}), indent=2)}
Performance score: {performance['composite_score']}/100
Weakest dimensions: {json.dumps(weak_dims)}
Current goals: {json.dumps(agent.get('goals', [])[:3])}
Total missions: {agent.get('total_missions', 0)}
Success rate: {agent.get('success_rate', 1.0):.1%}

Cognition health: {perf_data.get('cognition', {}).get('health_score', 50)}/100
Economy score: {perf_data.get('economy', {}).get('ai_analysis', {}).get('economy_score', 70)}/100

Generate specific evolution improvements. Respond with JSON:
{{
  "prompt_improvements": [
    {{"dimension": "dimension_name", "improvement": "specific change to make", "expected_delta": 5}}
  ],
  "skill_upgrades": {{
    "skill_name": 0.05
  }},
  "new_goals": ["new goal to add if relevant"],
  "strategy_refinements": ["strategic change 1", "strategic change 2"],
  "collaboration_protocols": ["how to work better with other agents"],
  "confidence_adjustment": 0.0,
  "reasoning_chain_templates": [
    "IF [trigger] THEN [action] BECAUSE [rationale]"
  ],
  "evolution_summary": "1-sentence summary of biggest improvement"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1000)
    if ok and data:
        return data
    return {
        "prompt_improvements": [],
        "skill_upgrades": {},
        "new_goals": [],
        "strategy_refinements": [],
        "collaboration_protocols": [],
        "confidence_adjustment": 0.0,
        "reasoning_chain_templates": [],
        "evolution_summary": f"{agent['id']} performance stable",
    }


def apply_evolution(agent: dict, improvements: dict, performance: dict) -> dict:
    evolved = {**agent}

    # Apply skill upgrades (capped at 0.99)
    current_skills = dict(evolved.get("skills", {}))
    for skill, delta in improvements.get("skill_upgrades", {}).items():
        current_skills[skill] = min(0.99, current_skills.get(skill, 0.75) + float(delta))
    evolved["skills"] = current_skills

    # Apply confidence adjustment
    conf_adj = float(improvements.get("confidence_adjustment", 0.0))
    evolved["confidence"] = round(
        max(0.3, min(0.99, evolved.get("confidence", 0.75) + conf_adj)), 3
    )

    # Add new goals (max 6)
    current_goals = evolved.get("goals", [])
    for goal in improvements.get("new_goals", []):
        if goal and goal not in current_goals:
            current_goals.append(goal)
    evolved["goals"] = current_goals[:6]

    # Store evolution history in agent memory
    if "evolution_history" not in evolved.get("memory", {}):
        evolved.setdefault("memory", {})["evolution_history"] = []

    evolved["memory"]["evolution_history"].append({
        "evolved_at": now_iso(),
        "performance_score": performance["composite_score"],
        "improvements_applied": len(improvements.get("prompt_improvements", [])) +
                                  len(improvements.get("skill_upgrades", {})),
        "summary": improvements.get("evolution_summary", ""),
    })

    # Keep evolution history bounded
    evolved["memory"]["evolution_history"] = evolved["memory"]["evolution_history"][-10:]

    # Store reasoning chain templates
    templates = improvements.get("reasoning_chain_templates", [])
    if templates:
        evolved["memory"]["reasoning_templates"] = templates[:5]

    # Update performance tracking
    evolved["last_performance_score"] = performance["composite_score"]
    evolved["evolution_cycle"] = evolved.get("evolution_cycle", 0) + 1

    return evolved


def orchestrate_hierarchy_update(all_agents: dict, all_performances: dict) -> dict:
    """Update the Autonomous Hierarchy based on agent performances."""
    system = (
        "You are the MIFTEH OS hierarchy optimizer. "
        "Based on agent performances, update the organizational structure "
        "to maximize coordination effectiveness."
    )
    agent_summaries = {aid: {"score": perf.get("composite_score", 0),
                              "role": agent.get("role", ""),
                              "confidence": agent.get("confidence", 0.75)}
                       for aid, (agent, perf) in zip(
                           all_agents.keys(),
                           zip(all_agents.values(), all_performances.values())
                       )}
    prompt = f"""Agent performance summary:
{json.dumps(agent_summaries, indent=2)}

Current hierarchy:
Supreme Orchestrator → [strategist, executor, reviewer, optimizer, monetizer, seo, analytics]

Update hierarchy and coordination strategy. Respond with JSON:
{{
  "hierarchy": {{
    "tier_1": ["orchestrator"],
    "tier_2": ["best performers"],
    "tier_3": ["remaining agents"]
  }},
  "coordination_updates": [
    {{"from": "agent", "to": "agent", "protocol": "description"}}
  ],
  "underperformers": ["agents needing extra evolution cycles"],
  "standout_agents": ["top performing agents"],
  "hierarchy_health_score": 0
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=700)
    if ok and data:
        return data
    return {
        "hierarchy": {"tier_1": ["orchestrator"], "tier_2": ["seo", "analytics"], "tier_3": []},
        "coordination_updates": [],
        "underperformers": [],
        "standout_agents": [],
        "hierarchy_health_score": 70,
    }


def main():
    print("[agent-evolution] Starting agent evolution engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    perf_data = load_performance_data()
    print(f"  [agent-evolution] {len(perf_data)} performance sources loaded")

    all_agents = {}
    all_performances = {}
    evolution_results = {}

    for agent_id in AGENT_IDS:
        print(f"  [agent-evolution] Evolving {agent_id}...")
        agent = load_agent(agent_id)
        all_agents[agent_id] = agent

        # Score current performance
        performance = score_agent_performance(agent, perf_data)
        all_performances[agent_id] = performance
        score = performance["composite_score"]

        # Generate improvements
        improvements = generate_agent_improvements(agent, performance, perf_data)

        # Apply evolution
        evolved_agent = apply_evolution(agent, improvements, performance)
        save_agent(evolved_agent)

        evolution_results[agent_id] = {
            "performance_score": score,
            "evolution_summary": improvements.get("evolution_summary", ""),
            "skills_upgraded": len(improvements.get("skill_upgrades", {})),
            "new_confidence": evolved_agent["confidence"],
        }

        n_upgrades = len(improvements.get("skill_upgrades", {}))
        print(f"    {agent_id}: score={score}/100 | {n_upgrades} skills upgraded | conf={evolved_agent['confidence']:.2f}")

    # Update hierarchy
    print("  [agent-evolution] Updating agent hierarchy...")
    hierarchy = orchestrate_hierarchy_update(all_agents, all_performances)
    h_score = hierarchy.get("hierarchy_health_score", 70)
    print(f"    Hierarchy health: {h_score}/100 | Standouts: {hierarchy.get('standout_agents', [])}")

    # Update evolution log
    log = []
    if EVOLUTION_LOG.exists():
        try:
            log = json.loads(EVOLUTION_LOG.read_text())
        except Exception:
            pass
    log.append({"evolved_at": now_iso(), "results": evolution_results, "hierarchy": hierarchy})
    EVOLUTION_LOG.write_text(json.dumps(log[-20:], indent=2))

    avg_score = sum(p["composite_score"] for p in all_performances.values()) / max(len(all_performances), 1)

    report = {
        "generated_at": now_iso(),
        "agents_evolved": len(AGENT_IDS),
        "avg_performance_score": round(avg_score, 1),
        "hierarchy": hierarchy,
        "evolution_results": evolution_results,
        "dimension_weights": {k: v["weight"] for k, v in EVOLUTION_DIMENSIONS.items()},
    }

    out = MEMORY_DIR / "agent_evolution_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[agent-evolution] {len(AGENT_IDS)} agents evolved | avg score: {avg_score:.1f}/100")
    print(f"[agent-evolution] Report → {out}")
    return report


if __name__ == "__main__":
    main()

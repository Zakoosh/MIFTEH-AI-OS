"""
MIFTEH OS — Cognition Engine
Multi-step reasoning, strategic planning loops, recursive self-analysis,
long-horizon thinking, objective decomposition, and reflection cycles.
The AI thinks continuously across runs via persistent reasoning chains.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
COGNITION_FILE = MEMORY_DIR / "cognition_state.json"
REASONING_DIR = MEMORY_DIR / "reasoning_chains"

PROJECTS = ["yallaplays", "fionera", "mifteh"]

COMPANY_OBJECTIVES = [
    "Achieve $10k/mo portfolio revenue",
    "Rank top-3 for primary keyword per project",
    "Build 100+ SEO pages across portfolio",
    "Establish MIFTEH OS as recognized AI OS platform",
    "Reach 100k monthly visits across portfolio",
]

REFLECTION_DIMENSIONS = [
    "strategic_alignment",   # Are we pursuing the right goals?
    "execution_quality",     # Are outputs meeting standards?
    "resource_efficiency",   # Are we spending tokens wisely?
    "market_positioning",    # Are we positioned to win?
    "agent_coordination",    # Are agents working well together?
    "risk_exposure",         # What risks are we carrying?
]


def load_cognition() -> dict:
    if COGNITION_FILE.exists():
        try:
            return json.loads(COGNITION_FILE.read_text())
        except Exception:
            pass
    return {
        "created_at": now_iso(),
        "reasoning_chains": [],
        "active_objectives": COMPANY_OBJECTIVES[:],
        "completed_objectives": [],
        "reflection_history": [],
        "strategic_hypotheses": [],
        "long_horizon_plans": {},
        "cognition_cycles": 0,
    }


def load_all_intelligence() -> dict:
    sources = {}
    for name, path in [
        ("revenue",      "memory/revenue_report.json"),
        ("seo",          "memory/seo_opportunities.json"),
        ("strategy",     "memory/strategy_report.json"),
        ("competitor",   "memory/competitor_memory.json"),
        ("social",       "memory/social_signals.json"),
        ("traffic",      "memory/traffic_intelligence.json"),
        ("monetization", "memory/monetization_report.json"),
        ("evolution",    "memory/evolution_report.json"),
        ("analytics",    "memory/analytics_intelligence.json"),
        ("bus",          "memory/agent_bus.json"),
    ]:
        f = Path(path)
        if f.exists():
            try:
                sources[name] = json.loads(f.read_text())
            except Exception:
                pass
    return sources


def decompose_objective(objective: str, intel: dict) -> dict:
    system = (
        "You are the MIFTEH OS supreme cognition engine. "
        "Decompose high-level objectives into concrete, measurable sub-goals "
        "with actionable steps, success criteria, and dependencies."
    )
    portfolio_value = intel.get("revenue", {}).get("portfolio_summary", {}).get("total_est_value_usd", 0)
    prompt = f"""Company objective: {objective}

Current portfolio state:
- Est. monthly revenue: ${portfolio_value:.0f}
- Active SEO projects: {', '.join(PROJECTS)}
- Intelligence sources loaded: {list(intel.keys())}

Decompose this objective into executable sub-goals. Respond with JSON:
{{
  "objective": "{objective}",
  "sub_goals": [
    {{
      "goal": "specific sub-goal",
      "metric": "how to measure success",
      "target_value": "the number/threshold",
      "current_value": "estimated current state",
      "gap": "distance to target",
      "actions": ["action 1", "action 2"],
      "dependencies": ["what must happen first"],
      "timeline_weeks": 0,
      "assigned_agent": "seo|executor|monetizer|strategist|analytics|optimizer"
    }}
  ],
  "critical_path": ["step 1 → step 2 → step 3"],
  "success_probability": 0.0,
  "blocking_risks": ["risk 1", "risk 2"]
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1500)
    if ok and data:
        return data
    return {
        "objective": objective,
        "sub_goals": [],
        "critical_path": [],
        "success_probability": 0.5,
        "blocking_risks": ["Intelligence insufficient for decomposition"],
    }


def run_reflection_cycle(cognition: dict, intel: dict) -> dict:
    system = (
        "You are the MIFTEH OS self-reflection engine. "
        "Analyze the current state of the autonomous company across multiple dimensions "
        "and identify what is working, what is not, and what to change."
    )
    last_chain = cognition["reasoning_chains"][-1] if cognition["reasoning_chains"] else {}
    prompt = f"""Reflection cycle #{cognition['cognition_cycles'] + 1}

Active objectives: {json.dumps(cognition['active_objectives'][:3])}
Previous reasoning: {json.dumps(last_chain, indent=2)[:600]}

Intelligence snapshot:
- Revenue est: ${intel.get('revenue', {}).get('portfolio_summary', {}).get('total_est_value_usd', 0):.0f}/mo
- SEO addressable traffic: {intel.get('seo', {}).get('total_addressable_traffic', 0):,}/mo
- Evolution maturity score: {intel.get('evolution', {}).get('system_maturity_score', 0)}/100
- Active bus tasks: {len(intel.get('bus', {}).get('task_queue', []))}

Reflect across these dimensions: {', '.join(REFLECTION_DIMENSIONS)}

Respond with JSON:
{{
  "reflection_id": "cycle_{cognition['cognition_cycles'] + 1}",
  "dimension_scores": {{
    "strategic_alignment": 0,
    "execution_quality": 0,
    "resource_efficiency": 0,
    "market_positioning": 0,
    "agent_coordination": 0,
    "risk_exposure": 0
  }},
  "what_is_working": ["insight 1", "insight 2"],
  "what_is_not_working": ["problem 1", "problem 2"],
  "strategic_pivots": [
    {{"pivot": "description", "from": "current approach", "to": "new approach", "rationale": "why"}}
  ],
  "next_cycle_focus": "single most important thing to address",
  "overall_health_score": 0,
  "confidence": 0.0
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1200)
    if ok and data:
        return data
    return {
        "reflection_id": f"cycle_{cognition['cognition_cycles'] + 1}",
        "dimension_scores": {d: 50 for d in REFLECTION_DIMENSIONS},
        "what_is_working": [],
        "what_is_not_working": [],
        "strategic_pivots": [],
        "next_cycle_focus": "Collect more system data",
        "overall_health_score": 50,
        "confidence": 0.6,
    }


def build_reasoning_chain(cognition: dict, intel: dict, reflection: dict) -> dict:
    system = (
        "You are the MIFTEH OS long-horizon reasoning engine. "
        "Build a multi-step reasoning chain that connects current state to 12-month objectives. "
        "Think in causal chains: IF we do X, THEN Y happens, WHICH LEADS TO Z."
    )
    prompt = f"""Current reflection health: {reflection.get('overall_health_score', 50)}/100
Next cycle focus: {reflection.get('next_cycle_focus', '')}
Active objectives: {json.dumps(cognition['active_objectives'][:2])}
Strategic pivots proposed: {json.dumps(reflection.get('strategic_pivots', [])[:2])}

Build a 5-step causal reasoning chain for the next 12 weeks. Respond with JSON:
{{
  "chain_id": "chain_{cognition['cognition_cycles']}",
  "reasoning_steps": [
    {{
      "step": 1,
      "action": "what to do",
      "mechanism": "how it works",
      "expected_outcome": "measurable result",
      "timeline_weeks": 2,
      "confidence": 0.0
    }}
  ],
  "hypothesis": "IF we execute steps 1-5 THEN company reaches X by week 12",
  "alternative_paths": [
    {{"path": "description", "trigger": "when to use this instead"}}
  ],
  "chain_confidence": 0.0,
  "key_assumptions": ["assumption 1", "assumption 2"]
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1200)
    if ok and data:
        return {**data, "built_at": now_iso()}
    return {
        "chain_id": f"chain_{cognition['cognition_cycles']}",
        "reasoning_steps": [],
        "hypothesis": "Insufficient data for reasoning chain",
        "alternative_paths": [],
        "chain_confidence": 0.5,
        "key_assumptions": [],
        "built_at": now_iso(),
    }


def generate_long_horizon_plan(intel: dict, cognition: dict) -> dict:
    system = (
        "You are the MIFTEH OS 12-month strategic planner. "
        "Create a quarter-by-quarter execution plan that achieves all company objectives."
    )
    prompt = f"""Company objectives:
{json.dumps(COMPANY_OBJECTIVES, indent=2)}

Current state:
- Portfolio revenue: ${intel.get('revenue', {}).get('portfolio_summary', {}).get('total_est_value_usd', 0):.0f}/mo
- Cognition cycles completed: {cognition['cognition_cycles']}
- Active reasoning chains: {len(cognition['reasoning_chains'])}

Create a 12-month horizon plan. Respond with JSON:
{{
  "plan_horizon_months": 12,
  "quarters": [
    {{
      "quarter": "Q1 (months 1-3)",
      "theme": "strategic theme",
      "primary_objectives": ["obj 1", "obj 2"],
      "key_milestones": ["milestone 1", "milestone 2"],
      "success_metrics": {{"metric": "target"}},
      "agent_focus": {{"orchestrator": "focus", "seo": "focus", "monetizer": "focus"}}
    }}
  ],
  "revenue_trajectory": [
    {{"month": 1, "est_revenue_usd": 0}},
    {{"month": 3, "est_revenue_usd": 0}},
    {{"month": 6, "est_revenue_usd": 0}},
    {{"month": 12, "est_revenue_usd": 0}}
  ],
  "critical_dependencies": ["dep 1", "dep 2"],
  "plan_confidence": 0.0
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1500)
    if ok and data:
        return {**data, "generated_at": now_iso()}
    return {
        "plan_horizon_months": 12,
        "quarters": [],
        "revenue_trajectory": [],
        "critical_dependencies": [],
        "plan_confidence": 0.5,
        "generated_at": now_iso(),
    }


def main():
    print("[cognition] Starting cognition engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    REASONING_DIR.mkdir(parents=True, exist_ok=True)

    cognition = load_cognition()
    intel = load_all_intelligence()
    print(f"  [cognition] Loaded {len(intel)} intelligence sources | cycle #{cognition['cognition_cycles'] + 1}")

    # Decompose top objective
    print("  [cognition] Decomposing primary objective...")
    primary_obj = cognition["active_objectives"][0] if cognition["active_objectives"] else COMPANY_OBJECTIVES[0]
    decomposition = decompose_objective(primary_obj, intel)
    n_subgoals = len(decomposition.get("sub_goals", []))
    prob = decomposition.get("success_probability", 0)
    print(f"    {n_subgoals} sub-goals | {prob:.0%} success probability")

    # Reflection cycle
    print("  [cognition] Running reflection cycle...")
    reflection = run_reflection_cycle(cognition, intel)
    health = reflection.get("overall_health_score", 50)
    print(f"    Health: {health}/100 | Focus: {reflection.get('next_cycle_focus', '')[:60]}")

    # Build reasoning chain
    print("  [cognition] Building reasoning chain...")
    chain = build_reasoning_chain(cognition, intel, reflection)
    n_steps = len(chain.get("reasoning_steps", []))
    print(f"    {n_steps} reasoning steps | confidence: {chain.get('chain_confidence', 0):.0%}")

    # Long-horizon plan (every 5 cycles or first run)
    long_plan = cognition.get("long_horizon_plans", {})
    if cognition["cognition_cycles"] % 5 == 0:
        print("  [cognition] Generating 12-month horizon plan...")
        long_plan = generate_long_horizon_plan(intel, cognition)
        print(f"    {len(long_plan.get('quarters', []))} quarters planned")

    # Update cognition state
    cognition["cognition_cycles"] += 1
    cognition["updated_at"] = now_iso()
    cognition["long_horizon_plans"] = long_plan

    cognition["reflection_history"].append(reflection)
    if len(cognition["reflection_history"]) > 20:
        cognition["reflection_history"] = cognition["reflection_history"][-20:]

    cognition["reasoning_chains"].append(chain)
    if len(cognition["reasoning_chains"]) > 20:
        cognition["reasoning_chains"] = cognition["reasoning_chains"][-20:]

    # Save current chain as a standalone file
    chain_file = REASONING_DIR / f"chain_{cognition['cognition_cycles']:04d}.json"
    chain_file.write_text(json.dumps({
        "decomposition": decomposition,
        "reflection": reflection,
        "chain": chain,
    }, indent=2))

    COGNITION_FILE.write_text(json.dumps(cognition, indent=2))

    report = {
        "generated_at": now_iso(),
        "cognition_cycle": cognition["cognition_cycles"],
        "health_score": health,
        "active_objectives": cognition["active_objectives"],
        "current_focus": reflection.get("next_cycle_focus", ""),
        "reasoning_steps": n_steps,
        "chain_confidence": chain.get("chain_confidence", 0),
        "decomposition": decomposition,
        "reflection": reflection,
        "latest_chain": chain,
        "long_horizon_plan": long_plan,
    }

    out = MEMORY_DIR / "cognition_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[cognition] Cycle {cognition['cognition_cycles']} complete | health={health}/100")
    print(f"[cognition] Report → {out}")
    return report


if __name__ == "__main__":
    main()

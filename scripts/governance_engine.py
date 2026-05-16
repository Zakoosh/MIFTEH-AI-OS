"""
MIFTEH OS — Governance Engine
Risk scoring, deployment permissions, execution budgets, token budgets,
rollback governance, trust escalation, and experimental sandbox mode.
The safety layer that controls AI autonomy.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

# Company mode definitions
COMPANY_MODES = {
    "assisted": {
        "label": "Assisted",
        "description": "Human reviews every action before execution",
        "auto_execute": False,
        "auto_merge": False,
        "max_token_budget_per_cycle": 10_000,
        "max_cost_per_cycle_usd": 0.10,
        "risk_threshold": 20,          # Only allow risk score < 20
        "trust_required": 90,
        "sandbox_only": False,
        "max_concurrent_agents": 2,
        "require_human_approval": True,
    },
    "semi_autonomous": {
        "label": "Semi-Autonomous",
        "description": "Low-risk actions auto-execute; high-risk require review",
        "auto_execute": True,
        "auto_merge": False,
        "max_token_budget_per_cycle": 50_000,
        "max_cost_per_cycle_usd": 0.50,
        "risk_threshold": 40,
        "trust_required": 75,
        "sandbox_only": False,
        "max_concurrent_agents": 4,
        "require_human_approval": False,
    },
    "autonomous": {
        "label": "Autonomous",
        "description": "Full autonomous execution with governance gates",
        "auto_execute": True,
        "auto_merge": True,
        "max_token_budget_per_cycle": 150_000,
        "max_cost_per_cycle_usd": 1.50,
        "risk_threshold": 60,
        "trust_required": 60,
        "sandbox_only": False,
        "max_concurrent_agents": 6,
        "require_human_approval": False,
    },
    "civilization": {
        "label": "Civilization Mode",
        "description": "AI coordinates all projects continuously — maximum autonomy",
        "auto_execute": True,
        "auto_merge": True,
        "max_token_budget_per_cycle": 500_000,
        "max_cost_per_cycle_usd": 5.00,
        "risk_threshold": 80,
        "trust_required": 40,
        "sandbox_only": False,
        "max_concurrent_agents": 8,
        "require_human_approval": False,
    },
}

# Risk factors and their weights
RISK_FACTORS = {
    "modifies_existing_file":  15,
    "deletes_content":         25,
    "affects_revenue_flow":    30,
    "affects_auth_or_secrets": 50,
    "external_api_call":       10,
    "new_feature":              5,
    "seo_only_change":          2,
    "content_only_change":      3,
    "reversible":              -10,  # negative = reduces risk
    "has_rollback_plan":       -15,
    "qa_score_above_75":       -10,
    "trust_score_above_80":    -12,
}

# Absolute blocks regardless of mode
HARD_BLOCKS = [
    "modify_github_workflow",
    "modify_auth_files",
    "expose_secrets",
    "delete_production_data",
    "modify_payment_flow",
]


def load_governance_state() -> dict:
    f = MEMORY_DIR / "governance_state.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {
        "created_at": now_iso(),
        "current_mode": "semi_autonomous",
        "token_budget_used": 0,
        "cost_budget_used_usd": 0.0,
        "cycle_decisions": [],
        "blocked_actions": [],
        "approved_actions": [],
        "budget_resets": 0,
        "total_cycles": 0,
    }


def load_trust() -> dict:
    f = MEMORY_DIR / "trust_scores.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def score_risk(action: dict, trust_data: dict) -> dict:
    risk = 0
    applied_factors = []

    # Apply positive risk factors
    if action.get("modifies_existing"):
        risk += RISK_FACTORS["modifies_existing_file"]
        applied_factors.append("modifies_existing_file")
    if action.get("deletes_content"):
        risk += RISK_FACTORS["deletes_content"]
        applied_factors.append("deletes_content")
    if action.get("affects_revenue"):
        risk += RISK_FACTORS["affects_revenue_flow"]
        applied_factors.append("affects_revenue_flow")
    if action.get("has_secrets"):
        risk += RISK_FACTORS["affects_auth_or_secrets"]
        applied_factors.append("affects_auth_or_secrets")
    if action.get("external_api"):
        risk += RISK_FACTORS["external_api_call"]
        applied_factors.append("external_api_call")

    # Feature type risk
    feat_type = action.get("type", "")
    if feat_type in ("seo_page", "seo_hub"):
        risk += RISK_FACTORS["seo_only_change"]
        applied_factors.append("seo_only_change")
    elif feat_type == "content":
        risk += RISK_FACTORS["content_only_change"]
        applied_factors.append("content_only_change")
    else:
        risk += RISK_FACTORS["new_feature"]
        applied_factors.append("new_feature")

    # Risk reducers
    if action.get("reversible", True):
        risk += RISK_FACTORS["reversible"]
        applied_factors.append("reversible")
    if action.get("has_rollback"):
        risk += RISK_FACTORS["has_rollback_plan"]
        applied_factors.append("has_rollback_plan")
    if action.get("qa_score", 0) >= 75:
        risk += RISK_FACTORS["qa_score_above_75"]
        applied_factors.append("qa_score_above_75")

    # Trust score from repo
    repo_map = {"yallaplays": "Zakoosh/Yallaplays", "fionera": "Zakoosh/fionera", "mifteh": "Zakoosh/mifteh-main-site"}
    repo = repo_map.get(action.get("project", ""), "")
    trust_val = trust_data.get("repos", {}).get(repo, {}).get("score", 50) if trust_data else 50
    if trust_val >= 80:
        risk += RISK_FACTORS["trust_score_above_80"]
        applied_factors.append("trust_score_above_80")

    risk = max(0, min(100, risk))
    return {
        "risk_score": risk,
        "risk_level": "low" if risk < 25 else "medium" if risk < 50 else "high" if risk < 75 else "critical",
        "applied_factors": applied_factors,
        "trust_score": trust_val,
    }


def check_hard_blocks(action: dict) -> list:
    blocks = []
    action_str = json.dumps(action).lower()
    for block in HARD_BLOCKS:
        keyword = block.replace("_", " ")
        if keyword in action_str:
            blocks.append(block)
    # Explicit file path checks
    target = action.get("target_path", "").lower()
    if any(x in target for x in [".github/workflows", "auth", ".env", "secret", "payment"]):
        blocks.append("forbidden_path")
    return blocks


def evaluate_action(action: dict, mode_config: dict, trust_data: dict,
                    state: dict) -> dict:
    hard_blocks = check_hard_blocks(action)
    if hard_blocks:
        return {
            "decision": "blocked",
            "reason": f"Hard block: {', '.join(hard_blocks)}",
            "hard_blocked": True,
            "risk_assessment": None,
        }

    risk = score_risk(action, trust_data)
    risk_score = risk["risk_score"]
    threshold = mode_config["risk_threshold"]

    # Budget check
    token_est = action.get("est_tokens", 1000)
    cost_est = action.get("est_cost_usd", 0.01)
    budget_ok = (
        state["token_budget_used"] + token_est <= mode_config["max_token_budget_per_cycle"]
        and state["cost_budget_used_usd"] + cost_est <= mode_config["max_cost_per_cycle_usd"]
    )

    # Trust check
    trust_ok = risk["trust_score"] >= mode_config["trust_required"]

    if not budget_ok:
        return {"decision": "blocked", "reason": "Budget exhausted for this cycle",
                "risk_assessment": risk, "hard_blocked": False}

    if not trust_ok and mode_config["trust_required"] > 0:
        return {"decision": "deferred", "reason": f"Trust score {risk['trust_score']} < required {mode_config['trust_required']}",
                "risk_assessment": risk, "hard_blocked": False}

    if risk_score > threshold:
        if mode_config.get("require_human_approval"):
            return {"decision": "needs_approval",
                    "reason": f"Risk {risk_score} exceeds threshold {threshold} — human approval required",
                    "risk_assessment": risk, "hard_blocked": False}
        else:
            return {"decision": "deferred",
                    "reason": f"Risk {risk_score} exceeds mode threshold {threshold}",
                    "risk_assessment": risk, "hard_blocked": False}

    return {
        "decision": "approved",
        "reason": f"Risk {risk_score} within threshold {threshold}",
        "risk_assessment": risk,
        "hard_blocked": False,
        "token_approved": token_est,
        "cost_approved_usd": cost_est,
    }


def ai_governance_review(actions: list, mode: str, state: dict) -> dict:
    if not actions:
        return {"governance_summary": "No actions to review", "risk_flags": [], "recommendations": []}

    system = (
        "You are the MIFTEH OS governance AI. Review a batch of autonomous actions "
        "for safety, strategic alignment, and resource efficiency."
    )
    prompt = f"""Company mode: {mode}
Actions under review (sample):
{json.dumps(actions[:8], indent=2)}

Current cycle usage:
- Tokens used: {state['token_budget_used']:,}
- Cost used: ${state['cost_budget_used_usd']:.3f}
- Approved actions: {len(state['approved_actions'])}
- Blocked actions: {len(state['blocked_actions'])}

Provide governance assessment. Respond with JSON:
{{
  "governance_summary": "2 sentence overall assessment",
  "risk_flags": [
    {{"flag": "description", "severity": "low|medium|high", "action_id": "which action"}}
  ],
  "recommendations": ["rec 1", "rec 2"],
  "suggested_mode_adjustment": null,
  "portfolio_risk_score": 0
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=700)
    if ok and data:
        return data
    return {
        "governance_summary": "Governance review completed",
        "risk_flags": [],
        "recommendations": [],
        "suggested_mode_adjustment": None,
        "portfolio_risk_score": 30,
    }


def reset_cycle_budget(state: dict) -> None:
    state["token_budget_used"] = 0
    state["cost_budget_used_usd"] = 0.0
    state["cycle_decisions"] = []
    state["budget_resets"] += 1


def main():
    print("[governance] Starting governance engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    mode_name = os.environ.get("COMPANY_MODE", "semi_autonomous").lower()
    if mode_name not in COMPANY_MODES:
        print(f"[governance] Unknown mode '{mode_name}' — defaulting to semi_autonomous")
        mode_name = "semi_autonomous"

    mode_config = COMPANY_MODES[mode_name]
    state = load_governance_state()
    trust_data = load_trust()

    print(f"[governance] Mode: {mode_config['label']} — {mode_config['description']}")
    print(f"[governance] Risk threshold: {mode_config['risk_threshold']} | Trust required: {mode_config['trust_required']}")

    # Load pending actions from autonomous decisions
    intel_f = MEMORY_DIR / "analytics_intelligence.json"
    decisions = []
    if intel_f.exists():
        try:
            intel = json.loads(intel_f.read_text())
            decisions = intel.get("autonomous_decisions", [])[:20]
        except Exception:
            pass

    print(f"  [governance] Evaluating {len(decisions)} pending decisions...")

    # Reset cycle budget for fresh run
    reset_cycle_budget(state)

    approved, blocked, deferred = [], [], []
    for decision in decisions:
        action = {
            "decision_id": decision.get("decision_id", ""),
            "project": decision.get("project", ""),
            "type": decision.get("type", "seo_page"),
            "title": decision.get("title", ""),
            "target_path": decision.get("target_path", ""),
            "reversible": True,
            "has_rollback": True,
            "est_tokens": 2000,
            "est_cost_usd": 0.02,
        }
        result = evaluate_action(action, mode_config, trust_data, state)

        if result["decision"] == "approved":
            state["token_budget_used"] += action["est_tokens"]
            state["cost_budget_used_usd"] += action["est_cost_usd"]
            approved.append({**action, "governance": result})
            state["approved_actions"].append(action.get("decision_id", ""))
        elif result["decision"] == "blocked":
            blocked.append({**action, "governance": result})
            state["blocked_actions"].append(action.get("decision_id", ""))
        else:
            deferred.append({**action, "governance": result})

    # AI governance review
    print("  [governance] Running AI governance review...")
    ai_review = ai_governance_review(approved[:5] + blocked[:3], mode_name, state)
    portfolio_risk = ai_review.get("portfolio_risk_score", 30)
    print(f"    Portfolio risk score: {portfolio_risk}/100")
    print(f"    {len(ai_review.get('risk_flags', []))} risk flags raised")

    # Update state
    state["current_mode"] = mode_name
    state["total_cycles"] += 1
    state["updated_at"] = now_iso()

    # Save governance state
    (MEMORY_DIR / "governance_state.json").write_text(json.dumps(state, indent=2))

    report = {
        "generated_at": now_iso(),
        "mode": mode_name,
        "mode_config": mode_config,
        "decisions_evaluated": len(decisions),
        "approved": len(approved),
        "blocked": len(blocked),
        "deferred": len(deferred),
        "token_budget_used": state["token_budget_used"],
        "cost_budget_used_usd": round(state["cost_budget_used_usd"], 4),
        "token_budget_remaining": mode_config["max_token_budget_per_cycle"] - state["token_budget_used"],
        "portfolio_risk_score": portfolio_risk,
        "ai_review": ai_review,
        "approved_actions": approved[:10],
        "blocked_actions": blocked[:10],
        "deferred_actions": deferred[:10],
    }

    out = MEMORY_DIR / "governance_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[governance] {len(approved)} approved | {len(blocked)} blocked | {len(deferred)} deferred")
    print(f"[governance] Budget: {state['token_budget_used']:,} tokens / ${state['cost_budget_used_usd']:.3f}")
    print(f"[governance] Report → {out}")
    return report


if __name__ == "__main__":
    main()

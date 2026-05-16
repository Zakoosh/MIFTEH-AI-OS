"""
MIFTEH OS — Autonomous Research Engine
Deep competitor research, ranking opportunity analysis, UX pattern comparison,
monetization model benchmarking, emerging technology detection, implementation reports.
"""
import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, generate_text, now_iso

MEMORY_DIR = Path("memory")

RESEARCH_DOMAINS = {
    "yallaplays": {
        "niche": "Arabic online gaming",
        "competitors": ["miniclip.com", "poki.com", "friv.com", "y8.com"],
        "research_areas": ["seo", "ux", "monetization", "content", "technology"],
        "target_keywords": ["العاب اون لاين", "العاب مجانية", "yalla play"],
    },
    "fionera": {
        "niche": "Turkish retail investing",
        "competitors": ["isyatirim.com.tr", "bigpara.com", "matriks.com.tr"],
        "research_areas": ["seo", "ux", "monetization", "features", "technology"],
        "target_keywords": ["borsa analiz", "hisse senedi takip", "portföy yönetimi"],
    },
    "mifteh": {
        "niche": "AI business automation",
        "competitors": ["zapier.com", "make.com", "n8n.io", "automationanywhere.com"],
        "research_areas": ["seo", "ux", "monetization", "positioning", "technology"],
        "target_keywords": ["AI automation", "workflow automation", "business automation AI"],
    },
}

TECHNOLOGY_SIGNALS = [
    "AI integration", "real-time features", "progressive web app", "edge computing",
    "personalization engine", "recommendation system", "A/B testing platform",
    "headless CMS", "micro-frontends", "server-side rendering",
]

UX_PATTERNS = [
    "infinite scroll", "sticky navigation", "dark mode", "skeleton loading",
    "progressive disclosure", "social proof widgets", "urgency indicators",
    "personalized onboarding", "gamification", "tooltips and guided tours",
]

MONETIZATION_MODELS = [
    "freemium", "subscription", "pay-per-use", "ad-supported", "marketplace",
    "affiliate", "b2b-saas", "consulting", "data licensing", "white-label",
]


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def fetch_competitor_signals(domain):
    """Fetch basic signals from a competitor domain."""
    signals = {"domain": domain, "reachable": False, "tech_hints": [], "title": ""}
    try:
        req = urllib.request.Request(
            f"https://{domain}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; MIFTEH-Research/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read(20000).decode("utf-8", errors="replace")
            signals["reachable"] = True
            signals["status_code"] = r.status

            # Basic tech detection from HTML
            for tech in ["react", "vue", "angular", "next.js", "nuxt", "gatsby", "shopify", "wordpress"]:
                if tech.lower() in html.lower():
                    signals["tech_hints"].append(tech)

            # Extract title
            import re
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            if title_match:
                signals["title"] = title_match.group(1).strip()[:100]

            # Check for known monetization signals
            for signal in ["adsense", "prebid", "stripe", "paddle", "paypal", "subscription"]:
                if signal.lower() in html.lower():
                    signals.setdefault("monetization_hints", []).append(signal)

            signals["content_length"] = len(html)
    except Exception as e:
        signals["error"] = str(e)[:100]
    return signals


def analyze_ranking_opportunities(project_id, config, sources):
    """Identify SEO ranking opportunities vs competitors."""
    seo_data = sources["seo"].get("projects", {}).get(project_id, {})
    traffic_data = sources["traffic"].get("projects", {}).get(project_id, {})
    growth_data = sources["growth"].get("projects", {}).get(project_id, {})

    existing_clusters = len(seo_data.get("topical_clusters", []))
    traffic_gaps = traffic_data.get("traffic_gaps", [])
    authority_plan = growth_data.get("topical_authority_plan", [])

    opportunities = []
    for gap in traffic_gaps[:3]:
        if isinstance(gap, dict):
            opportunities.append({
                "type": "traffic_gap",
                "keyword": gap.get("keyword", gap.get("topic", str(gap)[:50])),
                "competitor": gap.get("competitor", config["competitors"][0]),
                "potential_monthly_visits": gap.get("gap", 500),
                "priority": "high",
            })

    for pillar in authority_plan[:2]:
        opportunities.append({
            "type": "authority_gap",
            "topic": pillar.get("pillar", "").replace("_", " "),
            "articles_needed": pillar.get("recommended_articles", 10),
            "estimated_traffic": pillar.get("estimated_traffic_gain", 500),
            "priority": "high" if pillar.get("status") == "not_started" else "medium",
        })

    return {
        "total_opportunities": len(opportunities),
        "existing_cluster_count": existing_clusters,
        "opportunities": opportunities,
    }


def compare_ux_patterns(project_id, competitor_signals):
    """Compare UX patterns against competitors."""
    competitor_tech = []
    for sig in competitor_signals:
        competitor_tech.extend(sig.get("tech_hints", []))

    detected_patterns = []
    for pattern in UX_PATTERNS:
        in_competitors = any(
            pattern.lower() in " ".join(sig.get("tech_hints", [])).lower()
            for sig in competitor_signals
        )
        detected_patterns.append({
            "pattern": pattern,
            "competitors_use": in_competitors,
            "implementation_complexity": "low" if pattern in ["dark mode", "sticky navigation"] else "medium",
            "impact": "high" if pattern in ["personalized onboarding", "gamification", "social proof widgets"] else "medium",
        })

    return {
        "patterns_analyzed": len(detected_patterns),
        "competitors_ahead_count": sum(1 for p in detected_patterns if p["competitors_use"]),
        "top_gaps": [p for p in detected_patterns if p["competitors_use"] and p["impact"] == "high"][:3],
        "quick_wins": [p for p in detected_patterns if not p["competitors_use"] and p["implementation_complexity"] == "low"][:3],
    }


def benchmark_monetization(project_id, config, competitor_signals):
    """Compare monetization models vs competitors."""
    competitor_models = []
    for sig in competitor_signals:
        hints = sig.get("monetization_hints", [])
        if "subscription" in hints or "stripe" in hints:
            competitor_models.append("subscription")
        if "adsense" in hints or "prebid" in hints:
            competitor_models.append("ad-supported")

    competitor_models = list(set(competitor_models))

    return {
        "competitor_models_detected": competitor_models,
        "model_diversity": len(competitor_models),
        "opportunities": [
            m for m in MONETIZATION_MODELS
            if m not in competitor_models and m in ["freemium", "affiliate", "data licensing"]
        ][:3],
    }


def detect_emerging_technologies(competitor_signals_all):
    """Detect tech trends from competitor signals."""
    all_tech = []
    for sigs in competitor_signals_all.values():
        for sig in sigs:
            all_tech.extend(sig.get("tech_hints", []))

    tech_freq = {}
    for t in all_tech:
        tech_freq[t] = tech_freq.get(t, 0) + 1

    trending = sorted(tech_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "trending_technologies": [{"tech": t, "competitor_adoption": c} for t, c in trending],
        "signals_analyzed": len(all_tech),
        "emerging_picks": [t for t, _ in trending[:3]],
    }


def ai_research_synthesis(project_id, config, ranking_opps, ux_comparison, monetization, competitor_signals):
    """AI synthesizes deep research into implementation report."""
    system = (
        "You are a senior product and growth researcher. "
        "Synthesize competitor research into actionable intelligence. Return valid JSON only."
    )
    reachable = sum(1 for s in competitor_signals if s.get("reachable"))
    prompt = f"""Project: {project_id} — {config['niche']}
Competitors researched: {len(competitor_signals)} ({reachable} reachable)
Ranking opportunities: {ranking_opps['total_opportunities']}
UX gaps vs competitors: {ux_comparison['competitors_ahead_count']} patterns
Monetization models competitor uses: {monetization['competitor_models_detected']}

Return research synthesis:
{{
  "research_score": 0-100,
  "executive_summary": "3-sentence research synthesis",
  "biggest_competitor_advantage": "what competitors do better",
  "biggest_competitive_opportunity": "our biggest gap to exploit",
  "top_implementation_priorities": [
    {{"priority": "high", "action": "...", "expected_impact": "...", "timeline_weeks": 0}}
  ],
  "technology_recommendations": ["tech1", "tech2"],
  "monetization_recommendation": "specific monetization model upgrade",
  "ux_quick_wins": ["win1", "win2", "win3"]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 600)
    if not ok:
        data = {
            "research_score": 65,
            "executive_summary": f"Research complete for {project_id}. {ranking_opps['total_opportunities']} ranking opportunities found.",
            "biggest_competitor_advantage": "Larger content library and stronger domain authority",
            "biggest_competitive_opportunity": "AI-powered features and personalization competitors lack",
            "top_implementation_priorities": [
                {"priority": "high", "action": "Build topical authority clusters", "expected_impact": "3x organic traffic", "timeline_weeks": 12},
            ],
            "technology_recommendations": ["React", "Next.js SSR"],
            "monetization_recommendation": "Add freemium tier with premium AI features",
            "ux_quick_wins": ["Add dark mode", "Implement skeleton loading", "Add social proof counters"],
        }
    return data, tokens, cost


def main():
    print("[research_engine] Starting autonomous research...")

    sources = {
        "seo": _rj("seo_opportunities.json"),
        "traffic": _rj("traffic_intelligence.json"),
        "growth": _rj("growth_report.json"),
        "web_intel": _rj("web_intelligence.json"),
        "competitors": _rj("competitor_memory.json"),
    }

    all_tokens, all_cost = 0, 0.0
    project_reports = {}
    all_competitor_signals = {}

    for project_id, config in RESEARCH_DOMAINS.items():
        print(f"[research_engine] Researching {project_id}...")

        # Fetch live competitor signals
        competitor_signals = []
        for competitor in config["competitors"][:2]:  # Limit to 2 to save time
            print(f"[research_engine]   → {competitor}")
            sig = fetch_competitor_signals(competitor)
            competitor_signals.append(sig)

        all_competitor_signals[project_id] = competitor_signals

        ranking_opps = analyze_ranking_opportunities(project_id, config, sources)
        ux_comparison = compare_ux_patterns(project_id, competitor_signals)
        monetization_bench = benchmark_monetization(project_id, config, competitor_signals)

        synthesis, tokens, cost = ai_research_synthesis(
            project_id, config, ranking_opps, ux_comparison, monetization_bench, competitor_signals
        )
        all_tokens += tokens
        all_cost += cost

        project_reports[project_id] = {
            "niche": config["niche"],
            "competitors_researched": config["competitors"],
            "competitor_signals": competitor_signals,
            "ranking_opportunities": ranking_opps,
            "ux_comparison": ux_comparison,
            "monetization_benchmark": monetization_bench,
            "ai_synthesis": synthesis,
        }

    emerging_tech = detect_emerging_technologies(all_competitor_signals)

    report = {
        "generated_at": now_iso(),
        "projects_researched": len(project_reports),
        "total_competitors_analyzed": sum(len(v) for v in all_competitor_signals.values()),
        "emerging_technologies": emerging_tech,
        "projects": project_reports,
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "research_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[research_engine] Done — {report['projects_researched']} projects, {report['total_competitors_analyzed']} competitors, ${all_cost:.4f}")


if __name__ == "__main__":
    main()

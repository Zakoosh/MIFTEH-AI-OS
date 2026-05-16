"""
MIFTEH OS — SEO Opportunity Engine
Keyword gap detection, semantic cluster generation, long-tail discovery,
internal linking optimization, topical authority mapping.
Reads from web intelligence + market intelligence + competitor memory.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

PROJECT_DOMAINS = {
    "yallaplays": {"domain": "yallaplays.com", "niche": "free online browser games", "primary_kw": "free online games"},
    "fionera":    {"domain": "fionera.app",    "niche": "stock portfolio tracker Turkey BIST", "primary_kw": "bist stock tracker"},
    "mifteh":     {"domain": "miftehos.com",   "niche": "AI operating system autonomous development", "primary_kw": "AI OS platform"},
}

DIFFICULTY_BANDS = {
    "easy":   {"range": "0–20", "color": "green",  "est_rank_weeks": 4},
    "medium": {"range": "21–50", "color": "yellow", "est_rank_weeks": 12},
    "hard":   {"range": "51–80", "color": "orange", "est_rank_weeks": 26},
    "expert": {"range": "81–100", "color": "red",   "est_rank_weeks": 52},
}


def load_existing_intelligence() -> dict:
    sources = {}
    for name, path in [
        ("market",     "memory/market_intelligence.json"),
        ("web_intel",  "memory/web_intelligence.json"),
        ("roadmap",    "memory/roadmap.json"),
        ("competitor", "memory/competitor_memory.json"),
        ("analytics",  "memory/analytics_intelligence.json"),
    ]:
        f = Path(path)
        if f.exists():
            try:
                sources[name] = json.loads(f.read_text())
            except Exception:
                pass
    return sources


def generate_keyword_clusters(project: str, intel: dict) -> dict:
    proj_cfg = PROJECT_DOMAINS[project]
    kw_gaps = intel.get("market", {}).get("keyword_gaps", {}).get(project, [])
    trends = intel.get("market", {}).get("trending_topics", {}).get(project, [])

    system = (
        "You are an expert SEO strategist specializing in topical authority and "
        "semantic keyword clustering. Generate actionable, specific clusters."
    )
    prompt = f"""Project: {project}
Domain: {proj_cfg['domain']}
Niche: {proj_cfg['niche']}
Primary keyword: {proj_cfg['primary_kw']}

Existing keyword gaps: {json.dumps(kw_gaps[:5])}
Trending topics: {json.dumps(trends[:5])}

Generate a complete SEO keyword strategy. Respond with JSON:
{{
  "topical_clusters": [
    {{
      "cluster_name": "cluster name",
      "hub_keyword": "main keyword",
      "hub_page_title": "proposed page title",
      "hub_page_path": "/proposed-path",
      "spoke_keywords": ["kw1", "kw2", "kw3"],
      "est_monthly_searches": 0,
      "difficulty": "easy|medium|hard|expert",
      "est_rank_weeks": 0,
      "content_type": "hub|landing|category|comparison|how-to|listicle"
    }}
  ],
  "long_tail_opportunities": [
    {{
      "keyword": "long tail keyword",
      "est_monthly_searches": 0,
      "difficulty": "easy",
      "intent": "informational|navigational|commercial|transactional",
      "suggested_page": "/path"
    }}
  ],
  "quick_wins": [
    {{
      "keyword": "easy keyword",
      "current_rank": "not ranking",
      "action": "create new page | optimize existing",
      "est_traffic_gain": 0
    }}
  ],
  "internal_linking_plan": [
    {{
      "source_page": "/source",
      "target_page": "/target",
      "anchor_text": "anchor",
      "rationale": "why this link"
    }}
  ],
  "total_addressable_traffic": 0
}}
Return ONLY valid JSON. Be specific to {project}."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1800)
    if ok and data:
        return data
    # Fallback per project
    return _fallback_clusters(project, proj_cfg)


def _fallback_clusters(project: str, cfg: dict) -> dict:
    fallbacks = {
        "yallaplays": {
            "topical_clusters": [
                {"cluster_name": "Action Games Hub", "hub_keyword": "free action games online", "hub_page_title": "Free Action Games — Play Online Now", "hub_page_path": "/action-games", "spoke_keywords": ["shooting games", "fighting games", "adventure games"], "est_monthly_searches": 45000, "difficulty": "medium", "est_rank_weeks": 12, "content_type": "hub"},
                {"cluster_name": "Puzzle Games Hub", "hub_keyword": "free puzzle games online", "hub_page_title": "Best Free Puzzle Games Online", "hub_page_path": "/puzzle-games", "spoke_keywords": ["brain games", "logic games", "word games"], "est_monthly_searches": 32000, "difficulty": "easy", "est_rank_weeks": 6, "content_type": "hub"},
            ],
            "long_tail_opportunities": [
                {"keyword": "unblocked games at school", "est_monthly_searches": 8000, "difficulty": "easy", "intent": "navigational", "suggested_page": "/unblocked-games"},
                {"keyword": "free online games no download", "est_monthly_searches": 5500, "difficulty": "easy", "intent": "commercial", "suggested_page": "/no-download-games"},
            ],
            "quick_wins": [{"keyword": "play games online free", "current_rank": "not ranking", "action": "create new page", "est_traffic_gain": 3000}],
            "internal_linking_plan": [{"source_page": "/action-games", "target_page": "/puzzle-games", "anchor_text": "puzzle games", "rationale": "cross-category discovery"}],
            "total_addressable_traffic": 85000,
        },
        "fionera": {
            "topical_clusters": [
                {"cluster_name": "BIST Portfolio Tracker", "hub_keyword": "bist portfolio tracker", "hub_page_title": "Track Your BIST Portfolio — Free Tool", "hub_page_path": "/bist-portfolio", "spoke_keywords": ["borsa istanbul stocks", "turkish stocks app", "hisse senedi takip"], "est_monthly_searches": 12000, "difficulty": "easy", "est_rank_weeks": 6, "content_type": "landing"},
                {"cluster_name": "Stock Analysis Turkey", "hub_keyword": "turkish stock analysis", "hub_page_title": "Turkish Stock Market Analysis Dashboard", "hub_page_path": "/stock-analysis", "spoke_keywords": ["bist 100 analysis", "hisse analiz", "borsa teknik analiz"], "est_monthly_searches": 8000, "difficulty": "medium", "est_rank_weeks": 10, "content_type": "hub"},
            ],
            "long_tail_opportunities": [
                {"keyword": "bist 100 hisse takip uygulaması", "est_monthly_searches": 2200, "difficulty": "easy", "intent": "commercial", "suggested_page": "/bist-hisse-takip"},
            ],
            "quick_wins": [{"keyword": "free stock portfolio tracker turkey", "current_rank": "not ranking", "action": "create new page", "est_traffic_gain": 800}],
            "internal_linking_plan": [],
            "total_addressable_traffic": 22000,
        },
        "mifteh": {
            "topical_clusters": [
                {"cluster_name": "AI Development Platform", "hub_keyword": "AI development platform", "hub_page_title": "MIFTEH OS — Autonomous AI Development Platform", "hub_page_path": "/ai-platform", "spoke_keywords": ["autonomous AI", "AI OS", "AI startup tools"], "est_monthly_searches": 4000, "difficulty": "medium", "est_rank_weeks": 16, "content_type": "landing"},
            ],
            "long_tail_opportunities": [
                {"keyword": "autonomous AI product development", "est_monthly_searches": 900, "difficulty": "easy", "intent": "informational", "suggested_page": "/autonomous-ai-development"},
            ],
            "quick_wins": [{"keyword": "AI operating system 2025", "current_rank": "not ranking", "action": "create new page", "est_traffic_gain": 400}],
            "internal_linking_plan": [],
            "total_addressable_traffic": 6000,
        },
    }
    return fallbacks.get(project, {"topical_clusters": [], "long_tail_opportunities": [], "quick_wins": [], "internal_linking_plan": [], "total_addressable_traffic": 0})


def build_execution_queue(clusters_by_project: dict) -> list:
    queue = []
    for project, clusters in clusters_by_project.items():
        difficulty_weight = {"easy": 10, "medium": 7, "hard": 4, "expert": 2}
        for cluster in clusters.get("topical_clusters", []):
            queue.append({
                "project": project,
                "type": "seo_hub",
                "title": cluster.get("hub_page_title", ""),
                "target_path": cluster.get("hub_page_path", ""),
                "seo_target": cluster.get("hub_keyword", ""),
                "difficulty": cluster.get("difficulty", "medium"),
                "est_monthly_searches": cluster.get("est_monthly_searches", 0),
                "est_rank_weeks": cluster.get("est_rank_weeks", 12),
                "priority_score": difficulty_weight.get(cluster.get("difficulty", "medium"), 5) * (cluster.get("est_monthly_searches", 0) / 1000),
                "source": "seo_opportunity_engine",
            })
        for kw in clusters.get("quick_wins", []):
            queue.append({
                "project": project,
                "type": "seo_page",
                "title": f"Target: {kw.get('keyword', '')}",
                "target_path": kw.get("action", "").replace("create new page", "").strip() or "/seo",
                "seo_target": kw.get("keyword", ""),
                "difficulty": "easy",
                "est_traffic_gain": kw.get("est_traffic_gain", 0),
                "priority_score": kw.get("est_traffic_gain", 0) / 100,
                "source": "seo_opportunity_engine",
            })

    queue.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return queue[:30]


def inject_into_analytics_intel(queue: list) -> int:
    intel_file = Path("memory/analytics_intelligence.json")
    intel = {}
    if intel_file.exists():
        try:
            intel = json.loads(intel_file.read_text())
        except Exception:
            pass

    existing = intel.get("autonomous_decisions", [])
    existing_paths = {d.get("target_path", "") for d in existing}

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    new_items = []
    for item in queue[:10]:
        if item.get("target_path") in existing_paths:
            continue
        new_items.append({
            "decision_id": f"seo_{today}_{len(new_items)}",
            "project": item["project"],
            "type": item["type"],
            "title": item["title"],
            "target_path": item.get("target_path", ""),
            "seo_target": item.get("seo_target", ""),
            "rationale": f"SEO opportunity: {item.get('seo_target', '')} ({item.get('est_monthly_searches', 0):,} searches/mo)",
            "priority_weight": min(10, int(item.get("priority_score", 5))),
            "source": "seo_opportunity_engine",
        })

    intel["autonomous_decisions"] = new_items + existing
    intel["seo_queue_updated_at"] = now_iso()
    intel_file.write_text(json.dumps(intel, indent=2))
    return len(new_items)


def main():
    print("[seo] Starting SEO opportunity engine...")

    intel = load_existing_intelligence()
    print(f"[seo] Loaded {len(intel)} intelligence sources")

    target_project = os.environ.get("TARGET_PROJECT", "all")
    projects = ["yallaplays", "fionera", "mifteh"] if target_project == "all" else [target_project]

    clusters_by_project = {}
    for project in projects:
        print(f"  [seo] Generating clusters for {project}...")
        clusters = generate_keyword_clusters(project, intel)
        clusters_by_project[project] = clusters
        n_clusters = len(clusters.get("topical_clusters", []))
        n_longtail = len(clusters.get("long_tail_opportunities", []))
        traffic = clusters.get("total_addressable_traffic", 0)
        print(f"    {n_clusters} clusters, {n_longtail} long-tail, ~{traffic:,} addressable visits/mo")

    queue = build_execution_queue(clusters_by_project)
    injected = inject_into_analytics_intel(queue)

    report = {
        "generated_at": now_iso(),
        "projects": clusters_by_project,
        "execution_queue": queue,
        "total_addressable_traffic": sum(
            c.get("total_addressable_traffic", 0) for c in clusters_by_project.values()
        ),
        "executor_items_injected": injected,
    }

    out = Path("memory/seo_opportunities.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"[seo] {len(queue)} items in execution queue, {injected} injected into executor")
    print(f"[seo] Total addressable traffic: {report['total_addressable_traffic']:,} visits/mo")
    print(f"[seo] Report → {out}")
    return report


if __name__ == "__main__":
    main()

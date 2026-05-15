"""
MIFTEH OS — Market Intelligence Engine
Monitors competitors, tracks keyword trends, detects viral topics and new
monetization angles. No external API key required for basic operation.
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

COMPETITOR_SITES = {
    "yallaplays": [
        {"name": "Poki", "url": "https://poki.com"},
        {"name": "CrazyGames", "url": "https://www.crazygames.com"},
        {"name": "Y8", "url": "https://www.y8.com"},
    ],
    "fionera": [
        {"name": "TradingView", "url": "https://www.tradingview.com"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com"},
    ],
    "mifteh": [
        {"name": "Indie Hackers", "url": "https://www.indiehackers.com"},
        {"name": "Product Hunt", "url": "https://www.producthunt.com"},
    ],
}

TARGET_KEYWORDS = {
    "yallaplays": [
        "free online games", "browser games", "play games online",
        "action games", "puzzle games", "casual games",
    ],
    "fionera": [
        "stock market app", "portfolio tracker", "bist stocks",
        "finance dashboard", "invest turkey", "stock analysis",
    ],
    "mifteh": [
        "AI OS", "autonomous AI", "AI product development",
        "AI startup", "automated SEO", "AI company",
    ],
}


def fetch_url(url: str, timeout: int = 10) -> tuple:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MIFTEH-AI-Monitor/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(60000).decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def analyze_competitor(site: dict) -> dict:
    status, html = fetch_url(site["url"])

    result = {
        "name": site["name"],
        "url": site["url"],
        "reachable": status == 200,
        "status_code": status,
        "title": "",
        "internal_link_count": 0,
        "has_structured_data": False,
        "has_hreflang": False,
        "content_word_count": 0,
        "has_lazy_loading": False,
        "has_video_content": False,
    }

    if status == 200 and html:
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        result["title"] = title_m.group(1).strip() if title_m else ""
        result["internal_link_count"] = len(re.findall(r'href=["\']/', html))
        result["has_structured_data"] = bool(re.search(r"application/ld\+json", html, re.I))
        result["has_hreflang"] = bool(re.search(r"hreflang", html, re.I))
        result["has_lazy_loading"] = bool(re.search(r'loading=["\']lazy["\']', html, re.I))
        result["has_video_content"] = bool(re.search(r"<video|youtube\.com/embed", html, re.I))
        text = re.sub(r"<[^>]+>", " ", html)
        result["content_word_count"] = len(re.sub(r"\s+", " ", text).split())

    return result


def detect_trending_topics(project: str) -> dict:
    keywords = ", ".join(TARGET_KEYWORDS.get(project, []))
    month_year = datetime.now(timezone.utc).strftime("%B %Y")

    system = (
        "You are a market intelligence analyst with expertise in SEO and content strategy. "
        "Identify currently trending topics and keyword opportunities."
    )
    prompt = f"""Project: {project}
Target keywords: {keywords}
Current month: {month_year}

Identify trends and opportunities. Respond with JSON:
{{
  "trending_topics": [
    {{
      "topic": "topic name",
      "search_trend": "rising|stable|declining",
      "relevance": "why relevant",
      "opportunity": "content/page opportunity",
      "est_monthly_searches": 0,
      "competition": "low|medium|high"
    }}
  ],
  "keyword_gaps": [
    {{
      "keyword": "keyword",
      "est_monthly_searches": 0,
      "current_coverage": "none|partial|good",
      "opportunity_score": 1
    }}
  ],
  "viral_angles": ["angle 1", "angle 2"],
  "seasonal_opportunities": ["opportunity 1"],
  "new_monetization_angles": ["angle 1"]
}}
Return ONLY valid JSON. Focus on {month_year} trends for {project}."""

    try:
        data, _, _, ok = generate_json(system, prompt, max_tokens=1000)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return data
    except Exception:
        return {
            "trending_topics": [],
            "keyword_gaps": [],
            "viral_angles": [],
            "seasonal_opportunities": [],
            "new_monetization_angles": [],
        }


def analyze_competitive_gap(project: str, competitor_data: list) -> dict:
    reachable = [c for c in competitor_data if c.get("reachable")]
    if not reachable:
        return {"gaps": [], "advantages": [], "summary": "No competitor data available"}

    system = "You are a competitive analysis expert. Identify content and feature gaps."
    prompt = f"""Project: {project}
Competitor analysis:
{json.dumps(reachable, indent=2)}

Identify competitive gaps and opportunities. Respond with JSON:
{{
  "content_gaps": ["gap 1", "gap 2"],
  "feature_gaps": ["gap 1", "gap 2"],
  "advantages": ["our advantage 1"],
  "quick_wins": ["what to build next"],
  "summary": "2-sentence competitive position summary"
}}
Return ONLY valid JSON."""

    try:
        data, _, _, ok = generate_json(system, prompt, max_tokens=600)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return data
    except Exception:
        return {
            "content_gaps": [],
            "feature_gaps": [],
            "advantages": [],
            "quick_wins": [],
            "summary": "Analysis unavailable",
        }


def main():
    print("[market] Starting market intelligence engine...")

    all_competitors = {}
    all_trends = {}
    all_competitive_gaps = {}

    for project in ["yallaplays", "fionera", "mifteh"]:
        print(f"  [market] Analyzing {project}...")

        competitors = []
        for site in COMPETITOR_SITES.get(project, []):
            print(f"    Checking {site['name']}...")
            comp = analyze_competitor(site)
            competitors.append(comp)
            time.sleep(0.5)

        all_competitors[project] = competitors
        reached = sum(1 for c in competitors if c.get("reachable"))
        print(f"    {reached}/{len(competitors)} competitors reachable")

        trends = detect_trending_topics(project)
        all_trends[project] = trends
        n_topics = len(trends.get("trending_topics", []))
        n_gaps = len(trends.get("keyword_gaps", []))
        print(f"    {n_topics} trending topics, {n_gaps} keyword gaps")

        gaps = analyze_competitive_gap(project, competitors)
        all_competitive_gaps[project] = gaps

    report = {
        "generated_at": now_iso(),
        "competitors": all_competitors,
        "trends": all_trends,
        "competitive_gaps": all_competitive_gaps,
        "trending_topics": {
            proj: data.get("trending_topics", [])
            for proj, data in all_trends.items()
        },
        "keyword_gaps": {
            proj: data.get("keyword_gaps", [])
            for proj, data in all_trends.items()
        },
        "new_monetization_angles": {
            proj: data.get("new_monetization_angles", [])
            for proj, data in all_trends.items()
        },
    }

    out = Path("memory/market_intelligence.json")
    out.write_text(json.dumps(report, indent=2))

    total_topics = sum(len(d.get("trending_topics", [])) for d in all_trends.values())
    total_kw_gaps = sum(len(d.get("keyword_gaps", [])) for d in all_trends.values())
    print(
        f"[market] {total_topics} trending topics, "
        f"{total_kw_gaps} keyword gaps across all projects"
    )
    print(f"[market] Report → {out}")
    return report


if __name__ == "__main__":
    main()

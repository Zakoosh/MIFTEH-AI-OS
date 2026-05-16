"""
MIFTEH OS — Traffic Intelligence Engine
Estimates competitor traffic, detects CTR shifts, identifies seasonal spikes,
models traffic opportunity by keyword cluster and content gap.
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MIFTEH-AI-Monitor/2.0)"}

# Estimated baseline monthly traffic for known competitors (public estimates)
COMPETITOR_BASELINES = {
    "poki":          {"est_monthly_visits": 80_000_000, "primary_channel": "organic"},
    "crazygames":    {"est_monthly_visits": 30_000_000, "primary_channel": "organic"},
    "y8":            {"est_monthly_visits": 15_000_000, "primary_channel": "organic"},
    "tradingview":   {"est_monthly_visits": 50_000_000, "primary_channel": "direct"},
    "yahoo_finance": {"est_monthly_visits": 120_000_000, "primary_channel": "direct"},
    "indiehackers":  {"est_monthly_visits": 1_500_000,  "primary_channel": "organic"},
    "producthunt":   {"est_monthly_visits": 4_000_000,  "primary_channel": "direct"},
}

# Seasonal traffic multipliers by month (1–12) and project
SEASONAL_MULTIPLIERS = {
    "yallaplays": {1: 1.3, 2: 1.1, 3: 0.9, 4: 0.8, 5: 0.8, 6: 1.2,
                   7: 1.4, 8: 1.3, 9: 0.9, 10: 0.9, 11: 1.0, 12: 1.2},
    "fionera":    {1: 1.1, 2: 1.0, 3: 1.2, 4: 1.1, 5: 1.0, 6: 0.9,
                   7: 0.8, 8: 0.8, 9: 1.1, 10: 1.2, 11: 1.1, 12: 0.9},
    "mifteh":     {1: 1.0, 2: 1.0, 3: 1.1, 4: 1.2, 5: 1.1, 6: 1.0,
                   7: 0.9, 8: 0.9, 9: 1.1, 10: 1.1, 11: 1.0, 12: 0.9},
}

# Estimated organic CTR by SERP position
POSITION_CTR = {
    1: 0.316, 2: 0.158, 3: 0.098, 4: 0.073, 5: 0.058,
    6: 0.046, 7: 0.037, 8: 0.030, 9: 0.025, 10: 0.021,
}


def fetch(url: str, timeout: int = 10) -> tuple:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(100000).decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def probe_competitor_signals(name: str, url: str) -> dict:
    status, html = fetch(url)
    if status != 200:
        return {"name": name, "reachable": False}

    # Count internal links as proxy for site size
    internal_links = len(re.findall(r'href=["\']/', html))
    # Count images as proxy for content richness
    image_count = len(re.findall(r'<img[^>]+>', html, re.I))
    # Has structured data
    has_schema = bool(re.search(r'application/ld\+json', html, re.I))
    # Detect ads (proxy for monetization scale)
    has_ads = bool(re.search(r'googletag|adsbygoogle|prebid', html, re.I))
    # Title / meta
    title_m = re.search(r'<title[^>]*>([^<]{1,200})</title>', html, re.I)
    title = title_m.group(1).strip() if title_m else ""

    return {
        "name": name,
        "url": url,
        "reachable": True,
        "title": title,
        "internal_link_count": internal_links,
        "image_count": image_count,
        "has_schema": has_schema,
        "has_ads": has_ads,
    }


def estimate_traffic_gap(project: str, competitor_name: str,
                         our_est: int, their_est: int) -> dict:
    gap = their_est - our_est
    gap_pct = round(gap / max(their_est, 1) * 100, 1)
    catchup_months = round(gap / max(our_est * 0.15, 1000))  # assume 15% growth/mo
    return {
        "project": project,
        "competitor": competitor_name,
        "our_est_monthly": our_est,
        "their_est_monthly": their_est,
        "gap_visits": gap,
        "gap_pct": gap_pct,
        "catchup_at_15pct_growth_months": min(catchup_months, 120),
    }


def estimate_ctr_opportunity(keywords: list) -> list:
    opportunities = []
    for kw in keywords:
        searches = kw.get("est_monthly_searches", 0)
        difficulty = kw.get("difficulty", "medium")
        # Estimate reachable SERP position based on difficulty
        pos_map = {"easy": 3, "medium": 6, "hard": 10, "expert": 15}
        position = pos_map.get(difficulty, 8)
        ctr = POSITION_CTR.get(position, 0.015)
        est_clicks = round(searches * ctr)
        opportunities.append({
            "keyword": kw.get("keyword", kw.get("hub_keyword", "")),
            "est_monthly_searches": searches,
            "est_serp_position": position,
            "est_ctr": round(ctr * 100, 1),
            "est_monthly_clicks": est_clicks,
            "difficulty": difficulty,
        })
    return sorted(opportunities, key=lambda x: x["est_monthly_clicks"], reverse=True)[:15]


def detect_seasonal_spike(project: str) -> dict:
    month = datetime.now(timezone.utc).month
    multipliers = SEASONAL_MULTIPLIERS.get(project, {})
    current = multipliers.get(month, 1.0)
    next_month = multipliers.get((month % 12) + 1, 1.0)
    peak_month = max(multipliers.items(), key=lambda x: x[1])
    return {
        "current_month": month,
        "current_multiplier": current,
        "next_month_multiplier": next_month,
        "trend": "rising" if next_month > current else "falling" if next_month < current else "stable",
        "peak_month": peak_month[0],
        "peak_multiplier": peak_month[1],
        "is_peak_season": current >= 1.2,
    }


def ai_traffic_analysis(project: str, competitor_gaps: list,
                        ctr_opportunities: list, seasonal: dict,
                        seo_data: dict) -> dict:
    system = (
        "You are a traffic intelligence analyst. Model traffic opportunities, "
        "identify acquisition channels, and generate growth recommendations."
    )
    prompt = f"""Project: {project}
Competitor gaps: {json.dumps(competitor_gaps, indent=2)}
CTR opportunities (top 5): {json.dumps(ctr_opportunities[:5], indent=2)}
Seasonal context: {json.dumps(seasonal, indent=2)}
SEO addressable traffic: {seo_data.get('total_addressable_traffic', 0):,}

Generate traffic intelligence report. Respond with JSON:
{{
  "traffic_summary": "2 sentence summary",
  "est_current_monthly_visits": 0,
  "est_6mo_visits_with_seo": 0,
  "primary_growth_channel": "organic_seo|paid|social|direct|referral",
  "channel_breakdown": {{
    "organic": 0,
    "direct": 0,
    "social": 0,
    "referral": 0
  }},
  "top_traffic_opportunities": [
    {{"opportunity": "description", "est_monthly_lift": 0, "effort": "low|medium|high", "timeline_weeks": 0}}
  ],
  "ctr_improvement_actions": [
    {{"action": "description", "target_keyword": "keyword", "current_ctr_pct": 0, "target_ctr_pct": 0}}
  ],
  "seasonal_recommendation": "what to do given current seasonal position",
  "traffic_risk": "description of biggest traffic risk"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1000)
    if ok and data:
        return data
    return {
        "traffic_summary": "Traffic analysis unavailable",
        "est_current_monthly_visits": 0,
        "est_6mo_visits_with_seo": 0,
        "primary_growth_channel": "organic_seo",
        "channel_breakdown": {"organic": 70, "direct": 15, "social": 10, "referral": 5},
        "top_traffic_opportunities": [],
        "ctr_improvement_actions": [],
        "seasonal_recommendation": "",
        "traffic_risk": "",
    }


def load_seo_data() -> dict:
    f = Path("memory/seo_opportunities.json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def build_project_traffic(project: str, competitors: list, our_baseline: int) -> dict:
    # Probe competitors
    probed = []
    for comp in competitors:
        print(f"      Probing {comp['name']}...")
        result = probe_competitor_signals(comp["name"], comp["url"])
        result["baseline"] = COMPETITOR_BASELINES.get(comp["name"], {})
        probed.append(result)
        time.sleep(0.4)

    # Compute traffic gaps
    gaps = []
    for p in probed:
        their_est = p.get("baseline", {}).get("est_monthly_visits", 0)
        if their_est:
            gaps.append(estimate_traffic_gap(project, p["name"], our_baseline, their_est))

    # Seasonal
    seasonal = detect_seasonal_spike(project)

    # SEO keyword CTR
    seo_data = load_seo_data()
    proj_seo = seo_data.get("projects", {}).get(project, {})
    long_tail = proj_seo.get("long_tail_opportunities", [])
    quick_wins = proj_seo.get("quick_wins", [])
    all_kws = [{"keyword": lt.get("keyword"), "est_monthly_searches": lt.get("est_monthly_searches", 0), "difficulty": lt.get("difficulty", "medium")} for lt in long_tail]
    all_kws += [{"keyword": qw.get("keyword"), "est_monthly_searches": qw.get("est_traffic_gain", 0) * 10, "difficulty": "easy"} for qw in quick_wins]
    ctr_opps = estimate_ctr_opportunity(all_kws)

    # AI analysis
    ai = ai_traffic_analysis(project, gaps[:3], ctr_opps, seasonal, proj_seo)

    return {
        "project": project,
        "analyzed_at": now_iso(),
        "our_est_monthly_visits": our_baseline,
        "competitor_probes": probed,
        "traffic_gaps": gaps,
        "seasonal": seasonal,
        "ctr_opportunities": ctr_opps[:10],
        "ai_analysis": ai,
    }


def main():
    print("[traffic-intel] Starting traffic intelligence engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    PROJECT_CONFIGS = {
        "yallaplays": {
            "our_baseline": 15000,
            "competitors": [
                {"name": "poki",       "url": "https://poki.com"},
                {"name": "crazygames", "url": "https://www.crazygames.com"},
            ],
        },
        "fionera": {
            "our_baseline": 3000,
            "competitors": [
                {"name": "tradingview",   "url": "https://www.tradingview.com"},
                {"name": "yahoo_finance", "url": "https://finance.yahoo.com"},
            ],
        },
        "mifteh": {
            "our_baseline": 800,
            "competitors": [
                {"name": "indiehackers", "url": "https://www.indiehackers.com"},
                {"name": "producthunt",  "url": "https://www.producthunt.com"},
            ],
        },
    }

    all_projects = {}
    for project, cfg in PROJECT_CONFIGS.items():
        print(f"  [traffic-intel] Analyzing {project}...")
        result = build_project_traffic(project, cfg["competitors"], cfg["our_baseline"])
        all_projects[project] = result
        est = result["ai_analysis"].get("est_current_monthly_visits", cfg["our_baseline"])
        print(f"    Est. current: {est:,}/mo | {len(result['traffic_gaps'])} competitor gaps")

    total_addressable = sum(
        p.get("ai_analysis", {}).get("est_6mo_visits_with_seo", 0)
        for p in all_projects.values()
    )

    report = {
        "generated_at": now_iso(),
        "projects": all_projects,
        "total_addressable_6mo": total_addressable,
    }

    out = MEMORY_DIR / "traffic_intelligence.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[traffic-intel] Total addressable (6mo): {total_addressable:,} visits/mo")
    print(f"[traffic-intel] Report → {out}")
    return report


if __name__ == "__main__":
    main()

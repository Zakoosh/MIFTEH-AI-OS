"""
MIFTEH OS — Competitor Memory System
Stores and diffs competitor layouts, monetization models, SEO structures,
CTA styles, content patterns. Transfers best patterns into future generations.
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
COMPETITOR_DIR = MEMORY_DIR / "competitors"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MIFTEH-AI-Monitor/2.0)"}

COMPETITORS = {
    "yallaplays": [
        {"name": "poki",        "url": "https://poki.com"},
        {"name": "crazygames",  "url": "https://www.crazygames.com"},
        {"name": "y8",          "url": "https://www.y8.com"},
    ],
    "fionera": [
        {"name": "tradingview", "url": "https://www.tradingview.com"},
        {"name": "yahoo_finance","url": "https://finance.yahoo.com"},
    ],
    "mifteh": [
        {"name": "indiehackers","url": "https://www.indiehackers.com"},
        {"name": "producthunt", "url": "https://www.producthunt.com"},
    ],
}


def fetch(url: str) -> tuple:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(80000).decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def extract_full_profile(html: str, url: str) -> dict:
    def find(pattern, default=""):
        m = re.search(pattern, html, re.I | re.S)
        return m.group(1).strip()[:300] if m else default

    def findall(pattern):
        return [m.strip()[:200] for m in re.findall(pattern, html, re.I | re.S)][:10]

    # Layout signals
    has_sidebar = bool(re.search(r'<aside|class="[^"]*sidebar', html, re.I))
    has_hero = bool(re.search(r'class="[^"]*hero|class="[^"]*banner|class="[^"]*jumbotron', html, re.I))
    has_grid = bool(re.search(r'class="[^"]*grid|display:\s*grid', html, re.I))
    has_sticky_nav = bool(re.search(r'position:\s*sticky|position:\s*fixed', html, re.I))

    # Monetization signals
    has_ads = bool(re.search(r'googletag|adsbygoogle|ad-slot|data-ad', html, re.I))
    has_premium = bool(re.search(r'premium|pro plan|upgrade|subscription|pricing', html, re.I))
    has_affiliate = bool(re.search(r'affiliate|partner|referral', html, re.I))
    ad_positions = []
    if re.search(r'header.*ad|ad.*header', html, re.I):
        ad_positions.append("header")
    if re.search(r'sidebar.*ad|ad.*sidebar', html, re.I):
        ad_positions.append("sidebar")
    if re.search(r'footer.*ad|ad.*footer', html, re.I):
        ad_positions.append("footer")
    if re.search(r'in.?content|between|mid.?article', html, re.I):
        ad_positions.append("in-content")

    # SEO structure
    title = find(r"<title[^>]*>([^<]{1,200})</title>")
    h1s = findall(r"<h1[^>]*>([^<]{5,150})</h1>")
    h2s = findall(r"<h2[^>]*>([^<]{5,150})</h2>")
    desc = find(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{10,300})')
    has_faq = bool(re.search(r'faq|frequently.asked|accordion', html, re.I))
    has_breadcrumb = bool(re.search(r'breadcrumb|aria-label=["\']breadcrumb', html, re.I))
    schema_types = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)

    # CTA patterns
    cta_texts = findall(r'<(?:a|button)[^>]*class="[^"]*(?:btn|cta|button)[^"]*"[^>]*>([^<]{3,60})<')
    cta_colors = re.findall(r'(?:background|background-color)\s*:\s*(#[0-9a-f]{3,6}|rgba?\([^)]+\))', html, re.I)

    # Content patterns
    word_count = len(re.sub(r"<[^>]+>", " ", html).split())
    has_video = bool(re.search(r"<video|youtube\.com/embed|vimeo", html, re.I))
    has_testimonials = bool(re.search(r'testimonial|review|rating|stars', html, re.I))

    return {
        "url": url,
        "seo": {
            "title": title,
            "meta_description": desc,
            "h1s": h1s[:3],
            "h2s": h2s[:6],
            "has_faq": has_faq,
            "has_breadcrumb": has_breadcrumb,
            "schema_types": list(set(schema_types))[:8],
        },
        "layout": {
            "has_sidebar": has_sidebar,
            "has_hero": has_hero,
            "has_grid": has_grid,
            "has_sticky_nav": has_sticky_nav,
        },
        "monetization": {
            "has_ads": has_ads,
            "has_premium": has_premium,
            "has_affiliate": has_affiliate,
            "ad_positions": ad_positions,
        },
        "cta": {
            "texts": cta_texts[:5],
            "color_count": len(set(cta_colors)),
        },
        "content": {
            "word_count": word_count,
            "has_video": has_video,
            "has_testimonials": has_testimonials,
        },
    }


def ai_extract_patterns(profiles: list, project: str) -> dict:
    system = (
        "You are a competitive analysis expert. Extract actionable patterns from "
        "competitor profiles that can be transferred to improve our product."
    )
    compact = [{k: v for k, v in p.items() if k != "raw_html"} for p in profiles if p.get("reachable")]
    prompt = f"""Project being optimized: {project}
Competitor profiles:
{json.dumps(compact, indent=2)}

Extract transferable patterns. Respond with JSON:
{{
  "layout_patterns": [
    {{"pattern": "description", "used_by": ["competitor"], "transfer_recommendation": "how to apply"}}
  ],
  "monetization_patterns": [
    {{"pattern": "description", "used_by": ["competitor"], "est_revenue_impact": "description"}}
  ],
  "seo_patterns": [
    {{"pattern": "description", "used_by": ["competitor"], "implementation": "how to implement"}}
  ],
  "cta_patterns": [
    {{"pattern": "description", "examples": ["example text"], "recommendation": "apply this"}}
  ],
  "content_patterns": [
    {{"pattern": "description", "used_by": ["competitor"], "apply_as": "description"}}
  ],
  "top_3_recommendations": ["rec 1", "rec 2", "rec 3"]
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1200)
    if ok and data:
        return data
    return {
        "layout_patterns": [], "monetization_patterns": [], "seo_patterns": [],
        "cta_patterns": [], "content_patterns": [], "top_3_recommendations": [],
    }


def main():
    print("[competitor-memory] Starting competitor memory system...")

    COMPETITOR_DIR.mkdir(parents=True, exist_ok=True)

    all_patterns = {}

    for project, competitors in COMPETITORS.items():
        print(f"  [competitor-memory] {project}:")
        profiles = []

        for comp in competitors:
            print(f"    Profiling {comp['name']}...")
            status, html = fetch(comp["url"])
            reachable = status == 200

            profile = {
                "name": comp["name"],
                "url": comp["url"],
                "project": project,
                "profiled_at": now_iso(),
                "reachable": reachable,
            }

            if reachable:
                profile.update(extract_full_profile(html, comp["url"]))

            # Save individual competitor profile
            comp_file = COMPETITOR_DIR / f"{project}_{comp['name']}.json"
            comp_file.write_text(json.dumps(profile, indent=2))
            profiles.append(profile)
            print(f"      {'✓' if reachable else '○'} {comp['name']}: profiled")
            time.sleep(0.5)

        # AI pattern extraction per project
        print(f"    Extracting patterns for {project}...")
        patterns = ai_extract_patterns(profiles, project)
        all_patterns[project] = {
            "profiles": [{k: v for k, v in p.items() if k != "raw_html"} for p in profiles],
            "patterns": patterns,
            "profiled_at": now_iso(),
        }
        n_recs = len(patterns.get("top_3_recommendations", []))
        print(f"    {n_recs} top recommendations extracted")

    # Build summary
    summary = {
        "generated_at": now_iso(),
        "projects": all_patterns,
        "total_competitors": sum(len(COMPETITORS[p]) for p in COMPETITORS),
        "reachable_competitors": sum(
            sum(1 for prof in data["profiles"] if prof.get("reachable"))
            for data in all_patterns.values()
        ),
        "all_recommendations": {
            proj: data["patterns"].get("top_3_recommendations", [])
            for proj, data in all_patterns.items()
        },
    }

    out = MEMORY_DIR / "competitor_memory.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"[competitor-memory] {summary['reachable_competitors']}/{summary['total_competitors']} competitors profiled")
    print(f"[competitor-memory] Report → {out}")
    return summary


if __name__ == "__main__":
    main()

"""
MIFTEH OS — Web Intelligence Engine
Crawls competitor websites, monitors HN/Reddit/GitHub for trends,
detects SEO changes, pricing shifts, UI redesigns, new features.
All fetching uses stdlib — no external dependencies.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
WEB_INTEL_DIR = MEMORY_DIR / "web_intelligence"
SNAPSHOTS_DIR = WEB_INTEL_DIR / "snapshots"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MIFTEH-AI-Monitor/2.0; +https://miftehos.com)"}

COMPETITOR_TARGETS = {
    "yallaplays": [
        {"name": "poki", "url": "https://poki.com", "check_paths": ["/", "/en/g/action"]},
        {"name": "crazygames", "url": "https://www.crazygames.com", "check_paths": ["/"]},
    ],
    "fionera": [
        {"name": "tradingview", "url": "https://www.tradingview.com", "check_paths": ["/"]},
        {"name": "yahoo_finance", "url": "https://finance.yahoo.com", "check_paths": ["/"]},
    ],
    "mifteh": [
        {"name": "indiehackers", "url": "https://www.indiehackers.com", "check_paths": ["/"]},
    ],
}

HN_API = "https://hn.algolia.com/api/v1/search"
REDDIT_API = "https://www.reddit.com"
GITHUB_TRENDING = "https://github.com/trending"


def fetch(url: str, timeout: int = 10) -> tuple:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(80000).decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def fetch_json_api(url: str, timeout: int = 10) -> dict:
    try:
        req = urllib.request.Request(url, headers={**HEADERS, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read(200000).decode("utf-8", errors="replace"))
    except Exception:
        return {}


def extract_seo_signals(html: str) -> dict:
    def find(pattern, text, default=""):
        m = re.search(pattern, text, re.I | re.S)
        return m.group(1).strip() if m else default

    title = find(r"<title[^>]*>([^<]{1,200})</title>", html)
    desc = find(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{1,300})', html)
    h1 = find(r"<h1[^>]*>([^<]{1,200})</h1>", html)
    canonical = find(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html)
    has_schema = bool(re.search(r"application/ld\+json", html, re.I))
    word_count = len(re.sub(r"<[^>]+>", " ", html).split())
    internal_links = len(re.findall(r'href=["\']/', html))
    h2_count = len(re.findall(r"<h2[^>]*>", html, re.I))
    has_video = bool(re.search(r"<video|youtube\.com/embed|vimeo\.com", html, re.I))
    has_pricing = bool(re.search(r'pricing|price|per.month|\$/mo', html, re.I))
    has_cta = bool(re.search(r'sign.?up|get.?started|try.?free|start.?now', html, re.I))

    return {
        "title": title,
        "meta_description": desc,
        "h1": h1,
        "canonical": canonical,
        "has_schema": has_schema,
        "word_count": word_count,
        "internal_links": internal_links,
        "h2_count": h2_count,
        "has_video": has_video,
        "has_pricing": has_pricing,
        "has_cta": has_cta,
    }


def detect_changes(current: dict, previous: dict) -> list:
    changes = []
    checks = [
        ("title", "Title changed"),
        ("meta_description", "Meta description changed"),
        ("h1", "H1 changed"),
        ("has_pricing", "Pricing page presence changed"),
        ("has_schema", "Structured data presence changed"),
        ("has_cta", "CTA presence changed"),
    ]
    for key, label in checks:
        if previous and current.get(key) != previous.get(key):
            changes.append({
                "field": key,
                "label": label,
                "old": previous.get(key),
                "new": current.get(key),
            })
    # Word count delta
    prev_words = (previous or {}).get("word_count", 0)
    curr_words = current.get("word_count", 0)
    if prev_words and abs(curr_words - prev_words) > 500:
        changes.append({
            "field": "word_count",
            "label": f"Content significantly changed ({curr_words - prev_words:+d} words)",
            "old": prev_words,
            "new": curr_words,
        })
    return changes


def crawl_competitor(target: dict, project: str) -> dict:
    name = target["name"]
    base_url = target["url"]
    snapshot_file = SNAPSHOTS_DIR / f"{project}_{name}.json"

    previous = {}
    if snapshot_file.exists():
        try:
            previous = json.loads(snapshot_file.read_text())
        except Exception:
            pass

    pages = []
    for path in target.get("check_paths", ["/"]):
        url = base_url + path
        status, html = fetch(url)
        if status == 200:
            signals = extract_seo_signals(html)
            signals["url"] = url
            signals["status"] = status
            pages.append(signals)
        time.sleep(0.5)

    current_snapshot = {
        "name": name,
        "base_url": base_url,
        "project": project,
        "crawled_at": now_iso(),
        "pages": pages,
        "reachable": len(pages) > 0,
    }

    prev_pages = {p.get("url", ""): p for p in previous.get("pages", [])}
    all_changes = []
    for page in pages:
        prev_page = prev_pages.get(page.get("url", ""), {})
        changes = detect_changes(page, prev_page)
        if changes:
            all_changes.extend([{**c, "url": page.get("url")} for c in changes])

    current_snapshot["changes_detected"] = all_changes
    current_snapshot["change_count"] = len(all_changes)

    snapshot_file.write_text(json.dumps(current_snapshot, indent=2))
    return current_snapshot


def fetch_hn_stories(query: str, max_results: int = 10) -> list:
    params = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": max_results})
    data = fetch_json_api(f"{HN_API}?{params}")
    hits = data.get("hits", [])
    return [
        {
            "title": h.get("title", ""),
            "url": h.get("url", ""),
            "points": h.get("points", 0),
            "comments": h.get("num_comments", 0),
            "created_at": h.get("created_at", ""),
            "source": "hacker_news",
        }
        for h in hits[:max_results]
    ]


def fetch_reddit_posts(subreddit: str, max_results: int = 10) -> list:
    url = f"{REDDIT_API}/r/{subreddit}/hot.json?limit={max_results}"
    data = fetch_json_api(url)
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        posts.append({
            "title": d.get("title", ""),
            "url": d.get("url", ""),
            "score": d.get("score", 0),
            "comments": d.get("num_comments", 0),
            "subreddit": subreddit,
            "source": "reddit",
        })
    return posts


def fetch_github_trending(language: str = "") -> list:
    url = GITHUB_TRENDING + (f"/{language}" if language else "")
    status, html = fetch(url)
    if status != 200:
        return []
    repos = []
    for m in re.finditer(
        r'<h2[^>]*class="[^"]*h3[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>\s*([^<]+)',
        html, re.S
    ):
        href, name = m.group(1).strip(), m.group(2).strip().replace("\n", "").replace(" ", "")
        if href.count("/") == 2:
            repos.append({"repo": name, "url": f"https://github.com{href}", "source": "github_trending"})
        if len(repos) >= 10:
            break
    return repos


def analyze_opportunities(intel_data: dict) -> dict:
    system = (
        "You are a web intelligence analyst. Analyze competitor and trend data "
        "to identify actionable opportunities for content, SEO, and product development."
    )
    prompt = f"""Web intelligence data:
{json.dumps({
    "competitor_changes": [
        {k: v for k, v in c.items() if k != "pages"}
        for comps in intel_data.get("competitors", {}).values()
        for c in comps
        if c.get("change_count", 0) > 0
    ][:6],
    "trending_hn": intel_data.get("hn_stories", [])[:5],
    "trending_reddit": intel_data.get("reddit_posts", [])[:5],
    "github_trending": intel_data.get("github_trending", [])[:5],
}, indent=2)}

Identify opportunities. Respond with JSON:
{{
  "seo_opportunities": [
    {{"opportunity": "description", "project": "yallaplays|fionera|mifteh", "priority": 1, "rationale": "why"}}
  ],
  "content_opportunities": [
    {{"topic": "topic", "project": "project", "source_trend": "where spotted", "priority": 1}}
  ],
  "competitor_insights": [
    {{"competitor": "name", "change": "what changed", "action": "what we should do"}}
  ],
  "summary": "2-sentence intelligence summary"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1000)
    if ok and data:
        return data
    return {"seo_opportunities": [], "content_opportunities": [], "competitor_insights": [], "summary": ""}


def main():
    print("[web-intel] Starting web intelligence engine...")

    WEB_INTEL_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    intel_data: dict = {
        "generated_at": now_iso(),
        "competitors": {},
        "hn_stories": [],
        "reddit_posts": [],
        "github_trending": [],
    }

    # Crawl competitors
    for project, targets in COMPETITOR_TARGETS.items():
        intel_data["competitors"][project] = []
        for target in targets:
            print(f"  [web-intel] Crawling {target['name']} ({project})...")
            result = crawl_competitor(target, project)
            intel_data["competitors"][project].append(result)
            n_changes = result.get("change_count", 0)
            print(f"    {'✓' if result['reachable'] else '○'} {result['name']}: {n_changes} changes")
            time.sleep(0.3)

    # HN trending by project keywords
    print("  [web-intel] Fetching Hacker News stories...")
    hn_queries = ["SEO", "browser games", "stock market app", "AI startup", "indie hacker"]
    for q in hn_queries[:3]:
        stories = fetch_hn_stories(q, max_results=5)
        intel_data["hn_stories"].extend(stories)
        time.sleep(0.3)
    intel_data["hn_stories"] = intel_data["hn_stories"][:20]
    print(f"    {len(intel_data['hn_stories'])} HN stories fetched")

    # Reddit trending
    print("  [web-intel] Fetching Reddit posts...")
    subreddits = ["webdev", "gamedev", "investing", "SEO", "indiehackers"]
    for sub in subreddits:
        posts = fetch_reddit_posts(sub, max_results=5)
        intel_data["reddit_posts"].extend(posts)
        time.sleep(0.5)
    intel_data["reddit_posts"] = intel_data["reddit_posts"][:25]
    print(f"    {len(intel_data['reddit_posts'])} Reddit posts fetched")

    # GitHub trending
    print("  [web-intel] Fetching GitHub trending...")
    intel_data["github_trending"] = fetch_github_trending()
    print(f"    {len(intel_data['github_trending'])} trending repos")

    # AI analysis
    print("  [web-intel] Running AI opportunity analysis...")
    opportunities = analyze_opportunities(intel_data)
    intel_data["opportunities"] = opportunities

    total_changes = sum(
        c.get("change_count", 0)
        for comps in intel_data["competitors"].values()
        for c in comps
    )

    out = MEMORY_DIR / "web_intelligence.json"
    out.write_text(json.dumps(intel_data, indent=2))
    print(f"[web-intel] Done — {total_changes} competitor changes, "
          f"{len(intel_data['hn_stories'])} HN stories, "
          f"{len(intel_data['reddit_posts'])} Reddit posts")
    print(f"[web-intel] Report → {out}")
    return intel_data


if __name__ == "__main__":
    main()

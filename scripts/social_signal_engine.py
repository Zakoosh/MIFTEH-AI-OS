"""
MIFTEH OS — Social Signal Engine
Detects viral topics, rising discussions, finance sentiment, gaming trends,
emerging categories from Reddit, HN, and public trend feeds.
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MIFTEH-AI-Monitor/2.0)",
    "Accept": "application/json",
}

# Reddit sources by project domain
REDDIT_SOURCES = {
    "yallaplays": ["gaming", "WebGames", "indiegaming", "webdev"],
    "fionera":    ["stocks", "investing", "borsaistanbul", "personalfinance"],
    "mifteh":     ["artificial", "MachineLearning", "indiehackers", "SideProject"],
}

HN_QUERIES = {
    "yallaplays": ["browser games", "HTML5 games", "free online games"],
    "fionera":    ["stock portfolio", "trading app", "BIST Turkey"],
    "mifteh":     ["AI startup", "autonomous AI", "AI coding"],
}

GITHUB_TOPICS = {
    "yallaplays": ["game", "html5-game"],
    "fionera":    ["stock-market", "portfolio-tracker"],
    "mifteh":     ["ai-agent", "llm"],
}


def fetch(url: str, timeout: int = 10) -> tuple:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def fetch_reddit_hot(subreddit: str, limit: int = 15) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    status, body = fetch(url)
    if status != 200:
        return []
    try:
        data = json.loads(body)
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title": d.get("title", "")[:200],
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "url": d.get("url", ""),
                "flair": d.get("link_flair_text", ""),
                "subreddit": subreddit,
                "created_utc": d.get("created_utc", 0),
                "source": "reddit",
            })
        return posts
    except Exception:
        return []


def fetch_reddit_rising(subreddit: str, limit: int = 10) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/rising.json?limit={limit}"
    status, body = fetch(url)
    if status != 200:
        return []
    try:
        data = json.loads(body)
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title": d.get("title", "")[:200],
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "subreddit": subreddit,
                "source": "reddit_rising",
            })
        return posts
    except Exception:
        return []


def fetch_hn_stories(query: str, max_results: int = 8) -> list:
    params = urllib.parse.urlencode({
        "query": query,
        "tags": "story",
        "hitsPerPage": max_results,
        "numericFilters": "points>10",
    })
    url = f"https://hn.algolia.com/api/v1/search?{params}"
    status, body = fetch(url)
    if status != 200:
        return []
    try:
        data = json.loads(body)
        return [
            {
                "title": h.get("title", "")[:200],
                "url": h.get("url", ""),
                "points": h.get("points", 0),
                "comments": h.get("num_comments", 0),
                "author": h.get("author", ""),
                "created_at": h.get("created_at", ""),
                "source": "hacker_news",
            }
            for h in data.get("hits", [])[:max_results]
        ]
    except Exception:
        return []


def fetch_github_topic_repos(topic: str, limit: int = 5) -> list:
    url = f"https://github.com/topics/{topic}"
    status, html = fetch(url)
    if status != 200:
        return []
    repos = []
    for m in re.finditer(
        r'<h3[^>]*class="[^"]*f3[^"]*"[^>]*>\s*<a[^>]*href="(/[^"]+)"[^>]*>([^<]+)</a>',
        html, re.S
    ):
        href, name = m.group(1).strip(), m.group(2).strip()
        if href.count("/") == 2:
            repos.append({
                "name": name,
                "url": f"https://github.com{href}",
                "topic": topic,
                "source": "github_topics",
            })
        if len(repos) >= limit:
            break
    return repos


def calculate_signal_strength(posts: list) -> float:
    if not posts:
        return 0.0
    total = sum(p.get("score", 0) + p.get("comments", 0) * 2 for p in posts)
    return round(total / max(len(posts), 1), 1)


def extract_trending_keywords(posts: list) -> list:
    text = " ".join(p.get("title", "") for p in posts).lower()
    words = re.findall(r'\b[a-z]{4,}\b', text)
    stopwords = {"this", "that", "with", "from", "they", "have", "been", "what",
                 "your", "will", "when", "more", "just", "also", "about", "like",
                 "some", "than", "into", "over", "after", "here", "there", "their"}
    freq: dict = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:15]


def analyze_sentiment_signals(posts: list, project: str) -> dict:
    system = (
        "You are a market intelligence analyst specializing in social signal detection. "
        "Analyze posts to extract actionable insights for product and content strategy."
    )
    trimmed = [{"title": p["title"], "score": p.get("score", 0),
                "comments": p.get("comments", 0), "source": p.get("source", "")}
               for p in posts[:20]]
    prompt = f"""Project: {project}
Social posts sample:
{json.dumps(trimmed, indent=2)}

Analyze sentiment and extract signals. Respond with JSON:
{{
  "overall_sentiment": "positive|neutral|negative",
  "sentiment_score": 0,
  "viral_topics": [
    {{"topic": "description", "momentum": "rising|stable|declining", "relevance": "high|medium|low"}}
  ],
  "pain_points": ["pain point 1", "pain point 2"],
  "emerging_trends": ["trend 1", "trend 2"],
  "content_opportunities": [
    {{"title": "content idea", "format": "blog|video|tool|comparison", "rationale": "why"}}
  ],
  "competitor_mentions": ["any competitor names mentioned"],
  "key_insight": "single most actionable insight for {project}"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=900)
    if ok and data:
        return data
    return {
        "overall_sentiment": "neutral",
        "sentiment_score": 50,
        "viral_topics": [],
        "pain_points": [],
        "emerging_trends": [],
        "content_opportunities": [],
        "competitor_mentions": [],
        "key_insight": "",
    }


def collect_project_signals(project: str) -> dict:
    all_posts = []

    # Reddit hot
    for sub in REDDIT_SOURCES.get(project, [])[:3]:
        posts = fetch_reddit_hot(sub, limit=10)
        all_posts.extend(posts)
        time.sleep(0.4)

    # Reddit rising (first subreddit only for speed)
    subs = REDDIT_SOURCES.get(project, [])
    if subs:
        rising = fetch_reddit_rising(subs[0], limit=5)
        all_posts.extend(rising)
        time.sleep(0.3)

    # HN stories
    hn_posts = []
    for q in HN_QUERIES.get(project, [])[:2]:
        stories = fetch_hn_stories(q, max_results=5)
        hn_posts.extend(stories)
        time.sleep(0.3)
    all_posts.extend(hn_posts)

    # GitHub topics
    github_repos = []
    for topic in GITHUB_TOPICS.get(project, [])[:1]:
        repos = fetch_github_topic_repos(topic, limit=5)
        github_repos.extend(repos)
        time.sleep(0.3)

    # Compute metrics
    signal_strength = calculate_signal_strength(all_posts)
    trending_kws = extract_trending_keywords(all_posts)

    # AI sentiment analysis
    sentiment = analyze_sentiment_signals(all_posts, project)

    return {
        "project": project,
        "collected_at": now_iso(),
        "post_count": len(all_posts),
        "signal_strength": signal_strength,
        "trending_keywords": [{"word": w, "count": c} for w, c in trending_kws],
        "sentiment_analysis": sentiment,
        "github_trending": github_repos[:5],
        "top_posts": sorted(all_posts, key=lambda x: x.get("score", 0), reverse=True)[:10],
    }


def build_cross_project_signals(project_signals: dict) -> dict:
    all_trends = []
    for proj, signals in project_signals.items():
        sa = signals.get("sentiment_analysis", {})
        for t in sa.get("viral_topics", []):
            all_trends.append({**t, "project": proj})
        for t in sa.get("emerging_trends", []):
            all_trends.append({"topic": t, "project": proj, "momentum": "rising"})

    return {
        "cross_project_trends": all_trends[:20],
        "signal_summary": {
            proj: {
                "signal_strength": s.get("signal_strength", 0),
                "sentiment": s.get("sentiment_analysis", {}).get("overall_sentiment", "neutral"),
                "post_count": s.get("post_count", 0),
                "key_insight": s.get("sentiment_analysis", {}).get("key_insight", ""),
            }
            for proj, s in project_signals.items()
        },
    }


def main():
    print("[social-signals] Starting social signal engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    project_signals = {}
    for project in ["yallaplays", "fionera", "mifteh"]:
        print(f"  [social-signals] Collecting signals for {project}...")
        signals = collect_project_signals(project)
        project_signals[project] = signals
        n_posts = signals["post_count"]
        strength = signals["signal_strength"]
        sentiment = signals.get("sentiment_analysis", {}).get("overall_sentiment", "?")
        print(f"    {n_posts} posts | strength={strength} | sentiment={sentiment}")

    cross = build_cross_project_signals(project_signals)

    report = {
        "generated_at": now_iso(),
        "projects": project_signals,
        "cross_project": cross,
        "total_posts_analyzed": sum(s["post_count"] for s in project_signals.values()),
    }

    out = MEMORY_DIR / "social_signals.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[social-signals] {report['total_posts_analyzed']} total posts analyzed")
    print(f"[social-signals] Report → {out}")
    return report


if __name__ == "__main__":
    main()

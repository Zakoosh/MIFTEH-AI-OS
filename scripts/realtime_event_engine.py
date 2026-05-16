"""
MIFTEH OS — Realtime Event Engine
Monitors breaking news, Google algorithm updates, viral tech launches,
market-moving events. Injects emergency queue items when high-impact
events are detected.
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
    "Accept": "application/json, text/html",
}

# Signals that indicate high-impact events
ALERT_KEYWORDS = {
    "algorithm_update": [
        "google algorithm update", "core update", "google search update",
        "google ranking", "serp changes", "helpful content update",
    ],
    "viral_launch": [
        "product hunt", "show hn", "launch", "just launched", "open source",
        "new tool", "just shipped",
    ],
    "market_event": [
        "market crash", "stock rally", "fed rate", "inflation data",
        "earnings report", "ipo",
    ],
    "tech_trend": [
        "ai model", "gpt", "claude", "gemini", "open source model",
        "new framework", "next.js", "react",
    ],
    "gaming_event": [
        "game jam", "new browser game", "html5 game", "webgl",
        "game release", "free game",
    ],
}

# Emergency priority boost for high-impact events
EVENT_PRIORITY_WEIGHTS = {
    "algorithm_update": 10,
    "viral_launch":     8,
    "market_event":     7,
    "tech_trend":       6,
    "gaming_event":     5,
}

# Project relevance mapping
PROJECT_EVENT_RELEVANCE = {
    "yallaplays": ["algorithm_update", "viral_launch", "gaming_event"],
    "fionera":    ["algorithm_update", "market_event", "tech_trend"],
    "mifteh":     ["algorithm_update", "viral_launch", "tech_trend"],
}


def fetch(url: str, timeout: int = 10) -> tuple:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def fetch_hn_new(max_results: int = 30) -> list:
    params = urllib.parse.urlencode({
        "tags": "story",
        "hitsPerPage": max_results,
        "numericFilters": "created_at_i>0",
    })
    status, body = fetch(f"https://hn.algolia.com/api/v1/search_by_date?{params}")
    if status != 200:
        return []
    try:
        data = json.loads(body)
        return [
            {
                "title": h.get("title", ""),
                "url": h.get("url", ""),
                "points": h.get("points", 0),
                "comments": h.get("num_comments", 0),
                "source": "hn_new",
            }
            for h in data.get("hits", [])[:max_results]
        ]
    except Exception:
        return []


def fetch_reddit_new(subreddit: str, limit: int = 20) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    status, body = fetch(url)
    if status != 200:
        return []
    try:
        data = json.loads(body)
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "subreddit": subreddit,
                "created_utc": d.get("created_utc", 0),
                "source": "reddit_new",
            })
        return posts
    except Exception:
        return []


def classify_event(title: str) -> list:
    title_lower = title.lower()
    matched = []
    for event_type, keywords in ALERT_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                matched.append(event_type)
                break
    return list(set(matched))


def score_event_impact(post: dict, event_types: list) -> float:
    base = max(EVENT_PRIORITY_WEIGHTS.get(et, 0) for et in event_types) if event_types else 0
    engagement = post.get("points", post.get("score", 0)) + post.get("comments", 0) * 2
    engagement_boost = min(5, engagement / 100)
    return round(base + engagement_boost, 1)


def detect_events(posts: list) -> list:
    events = []
    for post in posts:
        title = post.get("title", "")
        event_types = classify_event(title)
        if not event_types:
            continue
        impact = score_event_impact(post, event_types)
        if impact < 5:
            continue
        events.append({
            "title": title,
            "url": post.get("url", ""),
            "event_types": event_types,
            "impact_score": impact,
            "source": post.get("source", ""),
            "detected_at": now_iso(),
        })
    return sorted(events, key=lambda x: x["impact_score"], reverse=True)


def ai_event_analysis(events: list, social_data: dict) -> dict:
    if not events:
        return {"urgent_actions": [], "event_summary": "No high-impact events detected.", "alert_level": "normal"}

    system = (
        "You are a real-time market intelligence system. Analyze breaking events "
        "and generate immediate, specific actions for each affected product."
    )
    prompt = f"""Breaking events detected:
{json.dumps(events[:10], indent=2)}

Projects: yallaplays (browser games), fionera (Turkey stock tracker), mifteh (AI OS)

For each high-impact event, generate emergency response actions. Respond with JSON:
{{
  "alert_level": "normal|elevated|high|critical",
  "event_summary": "1 sentence describing the most important event",
  "urgent_actions": [
    {{
      "event": "event title",
      "event_type": "type",
      "project": "yallaplays|fionera|mifteh|all",
      "action": "specific action to take",
      "rationale": "why urgently",
      "priority": 1,
      "deadline_hours": 24
    }}
  ],
  "content_opportunities": [
    {{"topic": "trending topic", "project": "project", "format": "blog|page|social", "urgency": "24h|48h|7d"}}
  ],
  "risks_to_monitor": ["risk 1", "risk 2"]
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=900)
    if ok and data:
        return data
    return {
        "alert_level": "normal",
        "event_summary": "Events detected but analysis unavailable.",
        "urgent_actions": [],
        "content_opportunities": [],
        "risks_to_monitor": [],
    }


def inject_emergency_queue(urgent_actions: list) -> int:
    if not urgent_actions:
        return 0

    intel_file = Path("memory/analytics_intelligence.json")
    intel = {}
    if intel_file.exists():
        try:
            intel = json.loads(intel_file.read_text())
        except Exception:
            pass

    existing = intel.get("autonomous_decisions", [])
    today = datetime.now(timezone.utc).strftime("%Y%m%d%H")

    new_items = []
    for action in urgent_actions[:5]:
        new_items.append({
            "decision_id": f"emergency_{today}_{len(new_items)}",
            "project": action.get("project", "all"),
            "type": "emergency_response",
            "title": action.get("action", "")[:100],
            "target_path": "/emergency",
            "rationale": f"URGENT: {action.get('rationale', '')}",
            "priority_weight": 10,
            "deadline_hours": action.get("deadline_hours", 24),
            "source": "realtime_event_engine",
            "event": action.get("event", ""),
        })

    # Prepend emergency items (highest priority)
    intel["autonomous_decisions"] = new_items + existing
    intel["emergency_updated_at"] = now_iso()
    intel_file.write_text(json.dumps(intel, indent=2))
    return len(new_items)


def load_previous_events() -> set:
    alert_f = MEMORY_DIR / "realtime_alerts.json"
    if not alert_f.exists():
        return set()
    try:
        data = json.loads(alert_f.read_text())
        return set(e.get("title", "") for e in data.get("events", []))
    except Exception:
        return set()


def main():
    print("[realtime] Starting realtime event engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    all_posts = []

    # HN new (most real-time)
    print("  [realtime] Fetching HN new stories...")
    hn_posts = fetch_hn_new(max_results=30)
    all_posts.extend(hn_posts)
    print(f"    {len(hn_posts)} HN stories")
    time.sleep(0.3)

    # Reddit new from key subreddits
    key_subreddits = ["technology", "webdev", "SEO", "gaming", "artificial"]
    print("  [realtime] Fetching Reddit new posts...")
    for sub in key_subreddits[:3]:
        posts = fetch_reddit_new(sub, limit=15)
        all_posts.extend(posts)
        time.sleep(0.3)
    print(f"    {len(all_posts) - len(hn_posts)} Reddit posts")

    # Detect events
    events = detect_events(all_posts)
    print(f"  [realtime] {len(events)} high-impact events detected")

    # Filter new events (not seen before)
    previous = load_previous_events()
    new_events = [e for e in events if e["title"] not in previous]
    print(f"  [realtime] {len(new_events)} new events (not previously seen)")

    # Load social data for context
    social_data = {}
    sf = MEMORY_DIR / "social_signals.json"
    if sf.exists():
        try:
            social_data = json.loads(sf.read_text())
        except Exception:
            pass

    # AI analysis
    print("  [realtime] Running AI event analysis...")
    analysis = ai_event_analysis(new_events[:10], social_data)
    alert_level = analysis.get("alert_level", "normal")
    print(f"  [realtime] Alert level: {alert_level.upper()}")

    # Inject emergency items
    injected = inject_emergency_queue(analysis.get("urgent_actions", []))
    if injected:
        print(f"  [realtime] {injected} emergency items injected into executor queue")

    report = {
        "generated_at": now_iso(),
        "posts_scanned": len(all_posts),
        "events_detected": len(events),
        "new_events": len(new_events),
        "alert_level": alert_level,
        "analysis": analysis,
        "events": events[:20],
        "executor_items_injected": injected,
    }

    out = MEMORY_DIR / "realtime_alerts.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[realtime] {len(all_posts)} posts scanned → {len(events)} events → alert={alert_level}")
    print(f"[realtime] Report → {out}")
    return report


if __name__ == "__main__":
    main()

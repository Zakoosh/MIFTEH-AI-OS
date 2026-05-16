"""
MIFTEH OS — Campaign Engine
Builds SEO keyword clusters into production HTML landing pages,
generates launch sequences, and injects campaign items into the executor queue.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, generate_text, now_iso

MEMORY_DIR = Path("memory")

# Target GitHub repos for each project
REPO_CONFIG = {
    "yallaplays": {
        "repo": "Zakoosh/Yallaplays",
        "html_dir": "public",
        "base_url": "https://yallaplays.com",
        "brand_color": "#7C3AED",
        "cta_text": "Play Now — Free",
    },
    "fionera": {
        "repo": "Zakoosh/fionera",
        "html_dir": "public",
        "base_url": "https://fionera.app",
        "brand_color": "#0EA5E9",
        "cta_text": "Track My Portfolio",
    },
    "mifteh": {
        "repo": "Zakoosh/mifteh-main-site",
        "html_dir": "public",
        "base_url": "https://miftehos.com",
        "brand_color": "#10B981",
        "cta_text": "Explore MIFTEH OS",
    },
}


def load_source(path: str) -> dict:
    f = Path(path)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def select_top_clusters(project: str, seo_data: dict, max_clusters: int = 3) -> list:
    proj = seo_data.get("projects", {}).get(project, {})
    clusters = proj.get("topical_clusters", [])
    difficulty_weight = {"easy": 10, "medium": 7, "hard": 4, "expert": 2}
    scored = sorted(
        clusters,
        key=lambda c: difficulty_weight.get(c.get("difficulty", "medium"), 5)
                      * (c.get("est_monthly_searches", 0) / 1000),
        reverse=True,
    )
    return scored[:max_clusters]


def generate_landing_page_html(cluster: dict, project: str, config: dict,
                                monetization_data: dict, social_data: dict) -> str:
    hub_kw = cluster.get("hub_keyword", "")
    hub_title = cluster.get("hub_page_title", hub_kw.title())
    hub_path = cluster.get("hub_page_path", "/page")
    spokes = cluster.get("spoke_keywords", [])
    content_type = cluster.get("content_type", "hub")
    base_url = config["base_url"]
    brand_color = config["brand_color"]
    cta_text = config["cta_text"]

    # Pull CTA optimizations from monetization
    proj_mono = monetization_data.get("projects", {}).get(project, {})
    cta_opts = proj_mono.get("monetization_plan", {}).get("cta_optimizations", [])
    hero_cta = next((c["cta_text"] for c in cta_opts if c.get("placement") == "hero"), cta_text)

    # Social proof from social signals
    proj_social = social_data.get("projects", {}).get(project, {})
    key_insight = proj_social.get("sentiment_analysis", {}).get("key_insight", "")

    system = (
        "You are an expert SEO content writer and HTML developer. "
        "Generate production-ready HTML landing pages optimized for search rankings. "
        "Include: proper meta tags, JSON-LD schema, semantic HTML5, internal linking hooks, "
        "mobile-responsive inline CSS, and conversion-focused copy. No external dependencies."
    )
    prompt = f"""Create a complete SEO landing page HTML file.

Project: {project}
Target keyword: {hub_kw}
Page title: {hub_title}
URL path: {hub_path}
Content type: {content_type}
Related keywords: {', '.join(spokes)}
Brand color: {brand_color}
CTA text: {hero_cta}
Base URL: {base_url}
Key market insight: {key_insight}

Requirements:
- Complete <!DOCTYPE html> document
- Title tag: {hub_title}
- Meta description with keyword
- JSON-LD WebPage or FAQPage schema
- H1 matching hub keyword
- 3–4 H2 sections covering spoke keywords
- 400+ words of unique, valuable content
- Sticky navigation bar
- Hero section with CTA button in brand color {brand_color}
- FAQ section with 3 questions (for featured snippet capture)
- Internal link placeholders: href="/[related-page]"
- Footer with site links
- Mobile-responsive via inline CSS (no external CSS files)
- No JavaScript required

Return ONLY the raw HTML. No markdown, no backticks, no explanation."""

    html, _, _, ok = generate_text(system, prompt, max_tokens=4000)
    if ok and html and html.strip().startswith("<!"):
        return html.strip()

    # Fallback minimal HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{hub_title}</title>
<meta name="description" content="Discover {hub_kw} — free, fast, and browser-based. No downloads needed.">
<link rel="canonical" href="{base_url}{hub_path}">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"{hub_title}","url":"{base_url}{hub_path}"}}</script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;color:#1a1a1a;line-height:1.6}}
  nav{{background:{brand_color};padding:1rem 2rem;color:#fff;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0}}
  .hero{{background:linear-gradient(135deg,{brand_color}22,#fff);padding:4rem 2rem;text-align:center}}
  .hero h1{{font-size:2.5rem;margin-bottom:1rem;color:{brand_color}}}
  .btn{{background:{brand_color};color:#fff;padding:.875rem 2rem;border-radius:.5rem;text-decoration:none;display:inline-block;margin-top:1rem;font-weight:600}}
  .content{{max-width:900px;margin:0 auto;padding:3rem 2rem}}
  h2{{color:{brand_color};margin:2rem 0 1rem}}
  .faq{{background:#f9f9f9;padding:2rem;border-radius:.5rem;margin-top:2rem}}
  footer{{background:#111;color:#aaa;text-align:center;padding:2rem}}
</style>
</head>
<body>
<nav><span style="font-weight:700;font-size:1.2rem">{project.title()}</span><a href="/" style="color:#fff">Home</a></nav>
<section class="hero">
  <h1>{hub_title}</h1>
  <p>The best {hub_kw} experience — free, instant, no download required.</p>
  <a href="{base_url}" class="btn">{hero_cta}</a>
</section>
<div class="content">
  {''.join(f'<h2>{s.title()}</h2><p>Explore our collection of {s} — updated daily with the best options available.</p>' for s in spokes[:3])}
  <div class="faq">
    <h2>Frequently Asked Questions</h2>
    <h3>What is {hub_kw}?</h3>
    <p>{hub_kw.title()} refers to a category of online content accessible directly in your browser.</p>
    <h3>Is {hub_kw} free?</h3>
    <p>Yes — completely free with no registration required.</p>
    <h3>How do I get started with {hub_kw}?</h3>
    <p>Simply visit our site and start exploring — no setup needed.</p>
  </div>
</div>
<footer><p>© 2025 {project.title()} — <a href="/" style="color:#7C3AED">Home</a></p></footer>
</body>
</html>"""


def build_launch_sequence(project: str, clusters: list, config: dict) -> list:
    sequence = []
    for i, cluster in enumerate(clusters):
        hub_path = cluster.get("hub_page_path", "/page")
        est_weeks = cluster.get("est_rank_weeks", 12)
        sequence.append({
            "week": i + 1,
            "action": "publish_hub_page",
            "path": hub_path,
            "title": cluster.get("hub_page_title", ""),
            "keyword": cluster.get("hub_keyword", ""),
            "difficulty": cluster.get("difficulty", "medium"),
            "est_rank_weeks": est_weeks,
            "est_monthly_searches": cluster.get("est_monthly_searches", 0),
        })
        sequence.append({
            "week": i + 2,
            "action": "internal_link_update",
            "source": "homepage",
            "target": hub_path,
            "anchor": cluster.get("hub_keyword", ""),
        })
        sequence.append({
            "week": i + 3,
            "action": "social_promotion",
            "content": f"New page: {cluster.get('hub_page_title', '')}",
            "platform": "reddit",
        })
    return sequence


def inject_campaigns_to_executor(campaigns: list) -> int:
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
    for camp in campaigns:
        path = camp.get("hub_path", "")
        if path in existing_paths:
            continue
        new_items.append({
            "decision_id": f"campaign_{today}_{len(new_items)}",
            "project": camp["project"],
            "type": "seo_hub",
            "title": camp.get("hub_title", ""),
            "target_path": path,
            "seo_target": camp.get("hub_keyword", ""),
            "rationale": f"Campaign: {camp.get('hub_keyword','')} ({camp.get('est_monthly_searches',0):,} searches/mo)",
            "priority_weight": 8,
            "source": "campaign_engine",
            "html_content": camp.get("html", "")[:500],  # preview only
        })

    intel["autonomous_decisions"] = new_items + existing
    intel["campaign_updated_at"] = now_iso()
    intel_file.write_text(json.dumps(intel, indent=2))
    return len(new_items)


def main():
    print("[campaign] Starting campaign engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    seo_data         = load_source("memory/seo_opportunities.json")
    monetization_data = load_source("memory/monetization_report.json")
    social_data      = load_source("memory/social_signals.json")

    all_campaigns = {}
    html_dir = MEMORY_DIR / "campaign_html"
    html_dir.mkdir(parents=True, exist_ok=True)

    campaign_queue = []

    for project, config in REPO_CONFIG.items():
        print(f"  [campaign] Building campaigns for {project}...")
        clusters = select_top_clusters(project, seo_data, max_clusters=2)

        project_campaigns = []
        for cluster in clusters:
            hub_kw = cluster.get("hub_keyword", "unknown")
            hub_path = cluster.get("hub_page_path", "/page")
            print(f"    Generating page: {hub_kw}...")

            html = generate_landing_page_html(
                cluster, project, config, monetization_data, social_data
            )

            # Save HTML locally
            slug = re.sub(r'[^a-z0-9]+', '-', hub_path.strip("/").lower()) or "page"
            html_file = html_dir / f"{project}_{slug}.html"
            html_file.write_text(html)

            campaign = {
                "project": project,
                "hub_keyword": hub_kw,
                "hub_title": cluster.get("hub_page_title", ""),
                "hub_path": hub_path,
                "difficulty": cluster.get("difficulty", "medium"),
                "est_monthly_searches": cluster.get("est_monthly_searches", 0),
                "html_path": str(html_file),
                "html": html,
                "generated_at": now_iso(),
            }
            project_campaigns.append(campaign)
            campaign_queue.append(campaign)

        sequence = build_launch_sequence(project, clusters, config)
        all_campaigns[project] = {
            "campaigns": project_campaigns,
            "launch_sequence": sequence,
        }
        print(f"    {len(project_campaigns)} landing pages | {len(sequence)} sequence steps")

    injected = inject_campaigns_to_executor(campaign_queue)

    report = {
        "generated_at": now_iso(),
        "projects": {p: {k: v for k, v in d.items() if k != "html"} for p, d in
                     {proj: {"campaigns": [{k: v for k, v in c.items() if k != "html"} for c in data["campaigns"]],
                              "launch_sequence": data["launch_sequence"]}
                      for proj, data in all_campaigns.items()}.items()},
        "total_pages_generated": sum(len(d["campaigns"]) for d in all_campaigns.values()),
        "executor_items_injected": injected,
    }

    out = MEMORY_DIR / "campaign_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[campaign] {report['total_pages_generated']} pages generated, {injected} injected into executor")
    print(f"[campaign] HTML → {html_dir}/")
    print(f"[campaign] Report → {out}")
    return report


if __name__ == "__main__":
    main()

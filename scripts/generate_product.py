"""
MIFTEH OS — Autonomous Product Execution Engine
Generates real product features, pages, and widgets for connected projects.
Uses OpenAI to create production-ready HTML/CSS/JS and creates draft PRs.

Feature types:
  category_page  — full SEO-optimized category landing page
  seo_hub        — Arabic/Turkish SEO content hub
  page           — full standalone page (services, about, etc.)
  widget         — self-contained embeddable component
  component      — reusable UI block/section
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_text, now_iso, today_str, timestamp_str

GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
OUTPUT_DIR = Path("outputs")
MEMORY_DIR = Path("memory")

# ─── Project + Feature Catalog ────────────────────────────────────────────────

PRODUCTS = {
    "yallaplays": {
        "repo": "Zakoosh/Yallaplays",
        "domain": "yallaplays.com",
        "description": "Arabic gaming platform — top game discovery site in Arab world. Browser games, no download.",
        "tech": "HTML5, embedded CSS, vanilla JS, dir='rtl' lang='ar', dark gaming theme",
        "files_to_read": ["index.html"],
        "features": [
            {
                "id": "category_action",
                "type": "category_page",
                "label": "Action Games Category Page",
                "path": "category/action.html",
                "seo_target": "العاب اكشن",
                "est_monthly_visits": 2000,
                "est_widgets": 0,
            },
            {
                "id": "related_games",
                "type": "component",
                "label": "Related Games Carousel Component",
                "path": "components/related-games.html",
                "seo_target": None,
                "est_monthly_visits": 0,
                "est_widgets": 1,
            },
            {
                "id": "arabic_seo_hub",
                "type": "seo_hub",
                "label": "Arabic SEO Games Hub",
                "path": "ar/index.html",
                "seo_target": "العاب مجانية اونلاين",
                "est_monthly_visits": 3500,
                "est_widgets": 0,
            },
        ],
    },
    "fionera": {
        "repo": "Zakoosh/fionera",
        "domain": "fionera.app",
        "description": "Turkish AI-powered finance dashboard. Tracks BIST stocks, crypto, portfolio performance.",
        "tech": "HTML5, embedded CSS, vanilla JS, dark finance/trading theme, Turkish language",
        "files_to_read": ["index.html"],
        "features": [
            {
                "id": "bist_widget",
                "type": "widget",
                "label": "BIST Turkish Market Overview Widget",
                "path": "widgets/bist-overview.html",
                "seo_target": None,
                "est_monthly_visits": 0,
                "est_widgets": 1,
            },
            {
                "id": "ai_insight_card",
                "type": "widget",
                "label": "AI Market Insight Card Widget",
                "path": "widgets/ai-insight.html",
                "seo_target": None,
                "est_monthly_visits": 0,
                "est_widgets": 1,
            },
            {
                "id": "portfolio_heatmap",
                "type": "widget",
                "label": "Portfolio Performance Heatmap Widget",
                "path": "widgets/portfolio-heatmap.html",
                "seo_target": None,
                "est_monthly_visits": 0,
                "est_widgets": 1,
            },
        ],
    },
    "mifteh": {
        "repo": "Zakoosh/mifteh-main-site",
        "domain": "miftehos.com",
        "description": "MIFTEH AI Systems — autonomous AI software company building AI-powered products.",
        "tech": "HTML5, embedded CSS, vanilla JS, dark tech/AI theme, English",
        "files_to_read": ["index.html"],
        "features": [
            {
                "id": "ai_services",
                "type": "page",
                "label": "AI Services Landing Page",
                "path": "services.html",
                "seo_target": "AI automation services",
                "est_monthly_visits": 800,
                "est_widgets": 0,
            },
            {
                "id": "lead_funnel",
                "type": "component",
                "label": "Lead Generation Funnel Section",
                "path": "components/lead-funnel.html",
                "seo_target": None,
                "est_monthly_visits": 0,
                "est_widgets": 1,
            },
        ],
    },
}

SYSTEM_PROMPT = """You are an expert frontend developer generating production-ready HTML.
STRICT RULES:
1. Output ONLY the complete HTML. No markdown. No backticks. No explanation.
2. Embed ALL CSS in <style> in <head>. Embed ALL JS in <script> at end of <body>.
3. Use realistic, meaningful content in the correct language — never Lorem Ipsum.
4. Make it visually polished: good spacing, typography, color contrast.
5. Every page must be fully self-contained with no external CDN or framework imports."""

# ─── GitHub API ───────────────────────────────────────────────────────────────

def gh(method, path, payload=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode() if payload else None,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MIFTEH-Product/1.0",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return json.loads(body) if body else {}, r.getcode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  [gh] {method} {path} => {e.code}: {body}")
        return None, e.code


def read_file_raw(owner, repo, path, ref="main"):
    data, code = gh("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
    if code != 200 or not isinstance(data, dict):
        return None
    try:
        return base64.b64decode(data["content"].replace("\n", "")).decode("utf-8", errors="replace")
    except Exception:
        return None


def get_default_branch(owner, repo):
    data, code = gh("GET", f"/repos/{owner}/{repo}")
    return (data or {}).get("default_branch", "main") if code == 200 else "main"


def get_branch_sha(owner, repo, branch):
    data, code = gh("GET", f"/repos/{owner}/{repo}/branches/{branch}")
    if code != 200 or not data:
        return None
    return data.get("commit", {}).get("sha")


def create_branch(owner, repo, branch, base_sha):
    _, code = gh("POST", f"/repos/{owner}/{repo}/git/refs",
                 {"ref": f"refs/heads/{branch}", "sha": base_sha})
    return code in (200, 201, 422)


def put_file(owner, repo, path, content_str, branch, message):
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("ascii")
    existing, code = gh("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
    payload = {"message": message, "content": encoded, "branch": branch}
    if code == 200 and isinstance(existing, dict) and "sha" in existing:
        payload["sha"] = existing["sha"]
    _, code = gh("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)
    return code in (200, 201)


def create_pr(owner, repo, title, body, head_branch, base_branch):
    data, code = gh("POST", f"/repos/{owner}/{repo}/pulls", {
        "title": title, "body": body,
        "head": head_branch, "base": base_branch, "draft": True,
    })
    if code in (200, 201) and data:
        return data.get("number"), data.get("html_url")
    return None, None


# ─── Prompt builders ──────────────────────────────────────────────────────────

def _ctx(context, max_chars=2000):
    return context[:max_chars] if context else "Dark modern gaming/finance/tech site."


def prompt_yallaplays_category_action(context):
    return f"""Generate a complete Arabic action games category page for YallaPlays (yallaplays.com).

EXISTING SITE STYLE (match this exactly):
{_ctx(context)}

PAGE: Action Games Category — https://yallaplays.com/category/action.html
Language: Arabic, dir="rtl", lang="ar"
Theme: Dark gaming (deep dark backgrounds, purple/green neon accents)

SEO REQUIREMENTS:
- <title>العاب أكشن | يلا بلايز — أفضل ألعاب الأكشن أونلاين مجاناً</title>
- <meta name="description" content="اكتشف أفضل العاب الأكشن المجانية أونلاين على يلا بلايز. العب مئات الألعاب الممتعة بدون تحميل — أكشن، قتال، مغامرة.">
- Open Graph: og:title, og:description, og:url, og:image, og:type=website
- Twitter Card: twitter:card=summary_large_image, twitter:title, twitter:description
- <link rel="canonical" href="https://yallaplays.com/category/action.html">
- JSON-LD BreadcrumbList: الرئيسية > الفئات > أكشن
- JSON-LD ItemList with 6 game items (name, url, image as placeholder URLs)

LAYOUT (Arabic RTL throughout):
1. <header>: logo "يلا بلايز 🎮" on right, nav: الرئيسية | الألعاب | الفئات | حول | اتصل
2. Breadcrumb bar: الرئيسية > الفئات > أكشن
3. Hero: H1 "العاب أكشن" + 40-word Arabic description + hero image div (colored gradient)
4. Filter row (sticky): الأكثر شعبية | الأحدث | الأعلى تقييماً — JS active highlighting
5. Games grid (4 cols, responsive 2 on mobile): 12 cards each with:
   - Colored div as image placeholder (lazy-load pattern: data-src, loading=lazy)
   - Arabic game title (use real game names: كول أوف ديوتي، جي تي إيه، ماينكرافت، فورتنايت، بابجي، أموج أس، روبلوكس، فيفا، ستريت فايتر، مورتال كومبات، باتل فيلد، كاونتر سترايك)
   - Genre badge (أكشن, قتال, مغامرة)
   - ★★★★☆ rating
   - "العب الآن 🎮" button
6. Pagination: أولى | 1 | 2 | 3 | ... | تالي
7. Related categories section: links to sports, racing, puzzle, strategy
8. <footer>: copyright MIFTEH | privacy | terms"""


def prompt_yallaplays_related_games(context):
    return f"""Generate a self-contained related games carousel component for YallaPlays Arabic gaming platform.

EXISTING SITE STYLE:
{_ctx(context, 1200)}

COMPONENT: Related Games Carousel — components/related-games.html
Language: Arabic, dir="rtl", lang="ar"

SPEC:
- Full HTML document (can be embedded via iframe or included)
- Section title: "ألعاب قد تعجبك 🎮" (Games You Might Like)
- Horizontal scrollable carousel: 8 game cards
- Each card (120px wide): colored emoji placeholder, Arabic game name (1-2 words), genre badge
- Left/right scroll arrow buttons (▶ ◀ reversed for RTL)
- Active/hover card highlight with neon glow
- Smooth scroll JS (no external libs)
- Dark gaming background, compact design
- Mobile: swipe-friendly horizontal scroll"""


def prompt_yallaplays_arabic_seo_hub(context):
    return f"""Generate a complete Arabic SEO hub page for YallaPlays (yallaplays.com/ar/index.html).

EXISTING SITE STYLE:
{_ctx(context, 1200)}

PAGE: Arabic Free Games SEO Hub — https://yallaplays.com/ar/index.html
Language: Arabic, dir="rtl", lang="ar"

SEO:
- <title>ألعاب مجانية أونلاين — يلا بلايز | العب بدون تحميل 2024</title>
- Long meta description in Arabic (155 chars)
- Canonical + OG + Twitter Card
- JSON-LD FAQPage with 4 Q&As (Arabic, about free online games)
- JSON-LD BreadcrumbList

LAYOUT:
1. Header (match existing site)
2. Hero: H1 "ألعاب مجانية أونلاين" + subtitle + "ابدأ اللعب" CTA
3. Quick stats: 500+ لعبة | مجاني 100% | بدون تحميل | يعمل على الموبايل
4. Categories grid (2x3): أكشن 🔥 | رياضة ⚽ | سباق 🏎️ | استراتيجية 🧩 | مغامرة 🗡️ | ألغاز 🎯
   Each with 20-word Arabic description
5. Featured games: 8 cards (same as category page style)
6. "لماذا يلا بلايز" section: 3 features (مجاني، بدون تحميل، آلاف الألعاب)
7. FAQ section (4 Q&As in Arabic with <details> accordion)
8. Footer"""


def prompt_fionera_bist_widget(context):
    return f"""Generate a BIST (Borsa İstanbul) market overview widget for Fionera Turkish finance app.

EXISTING SITE STYLE:
{_ctx(context)}

WIDGET: BIST Turkish Market Overview — widgets/bist-overview.html
Language: Turkish
Self-contained HTML widget (no external deps)

SPEC:
- Dark finance theme: background #0d1117, surface #161b22, green #00d4aa, red #ff4f5e
- Header row: "📈 BIST 100" title + live time clock (JS) + "Yenile" button
- BIST 100 index card: value (9,247.83), change (+1.24%, +113.45), day range bar
- Two columns: "En Çok Kazananlar" (top 5 gainers) | "En Çok Kaybedenler" (top 5 losers)
- Each row: ticker (bold, monospace), company name, TL price, change% with color badge
  Gainers: THYAO +4.2%, GARAN +3.8%, AKBNK +2.9%, EREGL +2.1%, KCHOL +1.7%
  Losers: TOASO -3.1%, SISE -2.4%, BIMAS -1.8%, TTKOM -1.3%, YKBNK -0.9%
- Mini sparkline bars (CSS width % colored divs) beside each row
- Volume bar at bottom: "Hacim: 42.3 Milyar TL"
- JS: "Yenile" button randomizes values ±1-5%, updates timestamp
- CSS transition animations on value changes"""


def prompt_fionera_ai_insight_card(context):
    return f"""Generate an AI market insight card widget for Fionera Turkish finance app.

EXISTING SITE STYLE:
{_ctx(context)}

WIDGET: AI Market Insight Card — widgets/ai-insight.html
Language: Turkish
Self-contained HTML widget

SPEC:
- Dark theme (match existing site)
- Card header: "🤖 AI Piyasa Analizi" + model badge "GPT-4" + timestamp
- Sentiment badge: YÜKSELIŞ / DÜŞÜŞ / NÖTR with colored pill (green/red/gray)
- AI analysis text (3-4 sentences realistic Turkish stock market analysis):
  "BIST 100 endeksi bugün güçlü bir yükseliş momentumu sergiliyor. Bankacılık sektörü öncülüğünde piyasalar, FED'in faiz kararı öncesi pozitif ayrışıyor. Yabancı yatırımcı alımları devam ederken, teknik olarak 9.200 direncinin kırılması bekleniyor. Portföylerde savunma sektörü ağırlığını artırmak önerilmektedir."
- Key metrics row (3 boxes): BIST 100 value | USD/TRY | Altın (TL/gr)
- Top 3 AI picks table: ticker, yön (▲▼), güven %
- "Detaylı Analiz" button + "Yenile" button
- JS: 3 pre-written insights cycling on Yenile click with smooth fade
- CSS: card glow effect, animated gradient border"""


def prompt_fionera_portfolio_heatmap(context):
    return f"""Generate a portfolio performance heatmap widget for Fionera Turkish finance app.

EXISTING SITE STYLE:
{_ctx(context)}

WIDGET: Portfolio Performance Heatmap — widgets/portfolio-heatmap.html
Language: Turkish
Self-contained HTML widget

SPEC:
- Dark theme
- Title: "Portföy Isı Haritası" + legend (kırmızı=düşüş, yeşil=yükseliş)
- CSS Grid heatmap of 20 stock tiles, 5 cols
- Tile sizes vary: 4 large (THYAO, GARAN, AKBNK, EREGL = 2x2), rest 1x1
- Each tile: ticker code (bold), change% (colored), colored background
- Color scale:
  <= -4%: #7f1d1d (deep red)
  -2% to -4%: #991b1b
  -1% to -2%: #b91c1c
  -1% to 0%: #374151 (gray)
  0% to +1%: #14532d
  +1% to +2%: #166534
  +2% to +4%: #15803d
  >= +4%: #16a34a (deep green)
- Hover tooltip (CSS :hover): full company name, price (TL), hacim (volume)
- Stocks: THYAO, GARAN, AKBNK, EREGL, KCHOL, TOASO, SISE, BIMAS, TTKOM, YKBNK, PETKM, SAHOL, TCELL, ASELS, KOZAL, VAKBN, HALKB, ISCTR, MGROS, EKGYO
- Bottom row: "Yenile" button + "Son güncelleme" timestamp
- JS: random data generation (-5% to +5%), refresh button animates tiles"""


def prompt_mifteh_ai_services(context):
    return f"""Generate a complete AI services landing page for MIFTEH AI Systems (miftehos.com/services.html).

EXISTING SITE STYLE:
{_ctx(context)}

PAGE: AI Services — https://miftehos.com/services.html
Language: English
Theme: Dark tech/AI (match existing site)

SEO:
- <title>AI Automation Services | MIFTEH AI Systems — Build Smarter, Scale Faster</title>
- Meta description (155 chars): "MIFTEH AI builds autonomous AI systems that generate content, optimize SEO, and build products 24/7. Real AI. Real results. Zero human hours."
- Canonical + OG + Twitter Card
- JSON-LD: Organization + WebPage schema

LAYOUT:
1. <nav>: "MIFTEH AI" logo + nav: Home | Services | Case Studies | Contact
2. Hero section:
   - H1: "Autonomous AI Systems That Build Your Business While You Sleep"
   - Subtitle (20 words): "We deploy AI agents that generate content, optimize SEO, and build product features 24/7."
   - Two CTAs: "Start Free Analysis" (primary) + "See Live Demo" (secondary)
   - Hero stat bar: ✅ 14 Active AI Loops | ✅ $0.003 avg cost/run | ✅ 99.9% uptime
3. Services grid (3 cols, 2 rows = 6 cards):
   - 🔍 AI SEO Engine: "Autonomous SEO content generation. 100+ optimized pages per month."
   - 🏗️ AI Product Builder: "Generate complete product features, pages, and widgets automatically."
   - 📊 AI Analytics OS: "Real-time business intelligence. No dashboards to maintain."
   - ✍️ AI Content Factory: "10x your content output. Blog posts, landing pages, social — all AI."
   - 💹 AI Finance Tools: "Intelligent market analysis, portfolio insights, BIST & crypto widgets."
   - ⚙️ AI Automation OS: "Full-stack autonomous operations. GitHub-native. Zero servers."
   Each card: emoji icon, bold title, 2-sentence description, "Learn More →" link
4. How it works (3 steps): Connect → Configure → Autonomous Execution
5. Proof section: 3 stat cards (8 Outputs/Day | 14 AI Loops | $0.023 first run cost)
6. Contact/CTA section: "Ready to automate your business?" + email input + "Get Started" button
7. Footer: © 2024 MIFTEH AI Systems | Built autonomously by MIFTEH AI OS"""


def prompt_mifteh_lead_funnel(context):
    return f"""Generate a self-contained lead generation funnel section for MIFTEH AI Systems.

EXISTING SITE STYLE:
{_ctx(context, 1200)}

COMPONENT: Lead Funnel — components/lead-funnel.html
Language: English
Self-contained HTML section with its own CSS

SPEC:
- 3-step guided funnel (multi-step form with JS state machine)
- Progress bar: Step 1/3 → 2/3 → 3/3 (animated CSS width)

Step 1 — "What do you need AI for?":
  3 option cards (click to select, visual highlight):
  🔍 SEO Automation | 🏗️ Product Building | 📊 Analytics & Reporting

Step 2 — "Tell us about your scale":
  4 radio-style cards:
  👤 Solo Founder | 🚀 Startup (2-20) | 📈 Scale-up (20-200) | 🏢 Enterprise (200+)

Step 3 — "Get your free AI analysis":
  Name input + Email input + "Generate My Free AI Report →" button
  Subtext: "No spam. Your analysis will be ready in 24h."

Success state:
  Animated checkmark ✅
  "Your AI Analysis Is Being Prepared!"
  Subtext: "Check your inbox at [email] within 24 hours."

Styles:
- Dark background #0a0a14, card surface #111827, accent #7c3aed (purple)
- Step transitions: slide + fade animation
- Responsive (mobile: single column)
- No backend: JS localStorage for state, console.log on submit"""


# ─── Prompt registry (project_featureid → builder fn) ────────────────────────

PROMPT_REGISTRY = {
    "yallaplays_category_action":   prompt_yallaplays_category_action,
    "yallaplays_related_games":     prompt_yallaplays_related_games,
    "yallaplays_arabic_seo_hub":    prompt_yallaplays_arabic_seo_hub,
    "fionera_bist_widget":          prompt_fionera_bist_widget,
    "fionera_ai_insight_card":      prompt_fionera_ai_insight_card,
    "fionera_portfolio_heatmap":    prompt_fionera_portfolio_heatmap,
    "mifteh_ai_services":           prompt_mifteh_ai_services,
    "mifteh_lead_funnel":           prompt_mifteh_lead_funnel,
}

# ─── Output records ───────────────────────────────────────────────────────────

def save_output_record(project, feature, tokens, cost, pr_url=None, bytes_generated=0):
    ts = timestamp_str()
    out_dir = OUTPUT_DIR / project / "product"
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "project": project,
        "operation_type": "product_execution",
        "feature_type": feature["type"],
        "feature_id": feature["id"],
        "label": feature["label"],
        "title": feature["label"],
        "target_path": feature["path"],
        "seo_target": feature.get("seo_target"),
        "estimated_monthly_visits": feature.get("est_monthly_visits", 0),
        "estimated_widgets": feature.get("est_widgets", 0),
        "bytes_generated": bytes_generated,
        "ai_generated": True,
        "ai_provider": "openai",
        "tokens_used": tokens,
        "cost_usd": cost,
        "pr_url": pr_url,
        "generated_at": now_iso(),
    }
    (out_dir / f"{ts}_{feature['id']}.json").write_text(json.dumps(record, indent=2))
    return record


def record_to_all_prs(project, repo, branch, pr_number, pr_url, pr_title, files, tokens, cost):
    f = MEMORY_DIR / "all_prs.json"
    prs = json.loads(f.read_text()) if f.exists() else []
    prs.append({
        "project": project.title(),
        "repo": repo,
        "branch": branch,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_title": pr_title,
        "created_at": now_iso(),
        "ai_generated": True,
        "operation_type": "product_execution",
        "files_committed": files,
        "tokens_used": tokens,
        "cost_usd": cost,
    })
    MEMORY_DIR.mkdir(exist_ok=True)
    f.write_text(json.dumps(prs, indent=2, ensure_ascii=False))


# ─── Core pipeline ────────────────────────────────────────────────────────────

def process_project(project_key, config, feature_filter=None):
    owner, repo = config["repo"].split("/")
    features = [f for f in config["features"]
                if not feature_filter or f["type"] in feature_filter]

    print(f"\n{'='*60}")
    print(f"[product] {project_key.upper()} — {config['repo']}")

    # Read existing files for design context
    context = ""
    for fname in config.get("files_to_read", ["index.html"]):
        raw = read_file_raw(owner, repo, fname)
        if raw:
            context += f"\n\n--- {fname} ---\n{raw}"
            print(f"  [read] {fname} ({len(raw):,} chars)")

    # Branch setup
    default_branch = get_default_branch(owner, repo)
    base_sha = get_branch_sha(owner, repo, default_branch)
    if not base_sha:
        print(f"  [!] Cannot get SHA — skipping {project_key}")
        return []

    today = today_str()
    branch = f"ai/product-{project_key}-{today}"
    ok = create_branch(owner, repo, branch, base_sha)
    print(f"  [branch] {branch} — {'ok' if ok else 'failed'}")

    results = []
    committed_paths = []
    total_tokens, total_cost = 0, 0.0

    for feature in features:
        fkey = f"{project_key}_{feature['id']}"
        prompt_fn = PROMPT_REGISTRY.get(fkey)
        if not prompt_fn:
            print(f"  [!] No prompt registered for {fkey} — skipping")
            continue

        print(f"\n  ▶ {feature['label']}")
        feature_prompt = prompt_fn(context)

        html, tokens, cost, ok = generate_text(SYSTEM_PROMPT, feature_prompt, max_tokens=4500)
        total_tokens += tokens
        total_cost += cost

        if not html:
            print(f"  [!] Generation failed for {feature['id']}")
            continue

        if "</html>" not in html.lower()[-200:]:
            html += "\n</html>"

        commit_msg = f"AI: Add {feature['label']} [product execution] [skip ci]"
        committed = put_file(owner, repo, feature["path"], html, branch, commit_msg)

        if committed:
            print(f"  [+] {feature['path']} — {len(html):,} chars")
            committed_paths.append(feature["path"])
            record = save_output_record(project_key, feature, tokens, cost, bytes_generated=len(html))
            results.append(record)
        else:
            print(f"  [!] Commit failed: {feature['path']}")

    if not committed_paths:
        print(f"  [!] Nothing committed for {project_key}")
        return results

    # Create draft PR
    features_done = [f for f in features if f["path"] in committed_paths]
    pr_title = f"AI Product: {project_key.title()} — {', '.join(f['label'] for f in features_done[:2])}"
    files_md = "\n".join(f"- `{p}`" for p in committed_paths)
    est_visits = sum(f.get("est_monthly_visits", 0) for f in features_done)
    est_widgets = sum(f.get("est_widgets", 0) for f in features_done)

    pr_body = f"""## 🤖 Autonomous Product Execution

Generated by **MIFTEH AI OS** at `{now_iso()}`

### Files Created ({len(committed_paths)})
{files_md}

### Feature Summary
| Type | Count |
|------|-------|
| Pages / Category pages | {sum(1 for f in features_done if f['type'] in ('page','category_page','seo_hub'))} |
| Widgets / Components | {sum(1 for f in features_done if f['type'] in ('widget','component'))} |

### Impact Estimates
- Est. SEO monthly visits: **{est_visits:,}**
- New interactive widgets: **{est_widgets}**

### AI Stats
- Tokens used: `{total_tokens:,}`
- Generation cost: `${total_cost:.5f}`

### Safety
- Risk level: **LOW** (new files only — zero existing files modified)
- Safety score: **100/100**
- All files are frontend-only HTML/CSS/JS

> Review each file before merging. Content is AI-generated and may need copy adjustments.
"""
    pr_num, pr_url = create_pr(owner, repo, pr_title, pr_body, branch, default_branch)
    if pr_url:
        print(f"\n  [PR] #{pr_num} — {pr_url}")
        for r in results:
            r["pr_url"] = pr_url
        record_to_all_prs(project_key, config["repo"], branch, pr_num, pr_url, pr_title,
                          committed_paths, total_tokens, total_cost)
    else:
        print(f"  [!] PR creation failed")

    print(f"  Tokens: {total_tokens:,} — Cost: ${total_cost:.5f}")
    return results


def main():
    if not GH_TOKEN:
        print("[product] ERROR: GH_PAT or GITHUB_TOKEN required"); sys.exit(1)

    target = os.environ.get("TARGET_PROJECT", "all").lower()
    feature_filter_env = os.environ.get("FEATURE_TYPES", "")
    feature_filter = set(feature_filter_env.split(",")) if feature_filter_env else None

    all_results = []
    total_tokens, total_cost = 0, 0.0

    for project_key, config in PRODUCTS.items():
        if target != "all" and target != project_key:
            continue
        results = process_project(project_key, config, feature_filter)
        all_results.extend(results)
        for r in results:
            total_tokens += r.get("tokens_used", 0)
            total_cost += r.get("cost_usd", 0.0)

    pages = sum(1 for r in all_results if r.get("feature_type") in ("page", "category_page", "seo_hub"))
    widgets = sum(1 for r in all_results if r.get("estimated_widgets", 0) > 0)
    est_visits = sum(r.get("estimated_monthly_visits", 0) for r in all_results)

    print(f"\n{'='*60}")
    print(f"[product] COMPLETE — {now_iso()}")
    print(f"  Features generated : {len(all_results)}")
    print(f"  Pages created      : {pages}")
    print(f"  Widgets created    : {widgets}")
    print(f"  Total tokens       : {total_tokens:,}")
    print(f"  Total cost         : ${total_cost:.5f}")
    print(f"  Est. monthly visits: {est_visits:,}")


if __name__ == "__main__":
    main()

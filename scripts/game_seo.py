"""
MIFTEH OS — Game SEO Engine
For every generated game: Arabic SEO page, English SEO page,
FAQ schema, VideoGame schema, breadcrumbs, related games,
internal links, category hubs, long-tail keywords, controls guide.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
GAMES_OUTPUT_DIR = Path("outputs/yallaplays/games")
REVIEWS_DIR = MEMORY_DIR / "reviews"
SEO_OUTPUT_DIR = Path("outputs/yallaplays/game_seo")

YALLAPLAYS_BASE_URL = "https://yallaplays.com"

RELATED_BY_TYPE = {
    "racing": ["car", "action", "survival"],
    "car": ["racing", "action", "survival"],
    "puzzle": ["brain", "kids", "idle"],
    "idle": ["puzzle", "brain", "clicker"],
    "kids": ["puzzle", "brain", "action"],
    "action": ["racing", "survival", "car"],
    "survival": ["action", "racing", "brain"],
    "brain": ["puzzle", "idle", "kids"],
}

LONG_TAIL_TEMPLATES = {
    "racing": [
        "العاب سباق سيارات مجانية اون لاين",
        "افضل العاب سباق للموبايل",
        "العاب سرعة بدون تحميل",
        "العاب سيارات اكشن للبنين",
    ],
    "car": [
        "العاب سيارات مجانية اون لاين 2025",
        "العاب قيادة سيارات للموبايل",
        "العاب سيارات بدون انترنت",
        "افضل العاب سيارات للاطفال",
    ],
    "puzzle": [
        "العاب بازل مجانية اون لاين",
        "العاب تركيز وذكاء للكبار",
        "العاب ذهنية للبنات",
        "العاب بازل بدون تحميل",
    ],
    "idle": [
        "العاب نقر وكسب نقاط",
        "العاب كاجوال للموبايل",
        "العاب قصيرة وممتعة",
        "العاب بسيطة بدون انترنت",
    ],
    "kids": [
        "العاب اطفال مجانية اون لاين",
        "العاب تعليمية للصغار",
        "العاب بنات وبنين للاطفال",
        "العاب آمنة للأطفال دون 10 سنوات",
    ],
    "action": [
        "العاب اكشن مجانية اون لاين",
        "العاب حرب وتصويب للموبايل",
        "افضل العاب اكشن عربية 2025",
        "العاب قتال بدون تحميل",
    ],
    "survival": [
        "العاب بقاء مجانية اون لاين",
        "العاب تحدي وصمود",
        "العاب موجات الاعداء",
        "العاب صعبة للمحترفين",
    ],
    "brain": [
        "العاب ذكاء وتفكير مجانية",
        "العاب تنشيط الذاكرة",
        "العاب ذهنية للبالغين",
        "العاب تركيز وانتباه",
    ],
}

FAQ_TEMPLATES = {
    "ar": [
        "هل اللعبة مجانية؟",
        "هل تعمل اللعبة على الموبايل؟",
        "هل يمكنني اللعب بدون تحميل؟",
        "كيف أتحكم في اللعبة؟",
        "هل اللعبة آمنة للأطفال؟",
    ],
    "en": [
        "Is the game free to play?",
        "Does the game work on mobile?",
        "Can I play without downloading anything?",
        "How do I control the game?",
        "Is the game safe for children?",
    ],
}


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def load_all_games():
    """Load all generated game metadata from outputs/yallaplays/games/."""
    games = []
    if not GAMES_OUTPUT_DIR.exists():
        return games
    for game_dir in GAMES_OUTPUT_DIR.iterdir():
        if not game_dir.is_dir():
            continue
        meta_file = game_dir / "metadata.json"
        if meta_file.exists():
            try:
                games.append(json.loads(meta_file.read_text()))
            except Exception:
                pass
    return games


def generate_game_faq(game_data, all_tokens, all_cost):
    """Generate Arabic + English FAQ for a game."""
    meta = game_data.get("metadata", {})
    game_type = game_data.get("game_type", "racing")
    title_ar = meta.get("title_ar", "اللعبة")
    controls_ar = meta.get("controls_ar", "الأسهم للتحرك")

    system = "Arabic/English FAQ generator for HTML5 games on YallaPlays. Return valid JSON only."
    prompt = f"""Generate FAQ content for '{title_ar}' ({game_type} game) on YallaPlays.
Controls: {controls_ar}

Return:
{{
  "faq_ar": [
    {{"q": "Arabic question", "a": "Arabic answer"}}
  ],
  "faq_en": [
    {{"q": "English question", "a": "English answer"}}
  ],
  "long_tail_keywords_ar": ["keyword1", "keyword2", "keyword3"],
  "long_tail_keywords_en": ["keyword1", "keyword2"],
  "category_hub_link": "/العاب-{game_type}",
  "internal_links_ar": [
    {{"anchor": "Arabic anchor text", "url": "/category-slug"}}
  ]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, max_tokens=600)
    all_tokens += tokens
    all_cost += cost

    if not ok or not data:
        data = {
            "faq_ar": [
                {"q": f"هل {title_ar} مجانية؟", "a": "نعم، يمكنك اللعب مجاناً وبدون أي تحميل."},
                {"q": "هل تعمل على الموبايل؟", "a": "نعم، اللعبة تعمل على جميع الأجهزة المحمولة."},
                {"q": "كيف التحكم في اللعبة؟", "a": controls_ar},
                {"q": "هل اللعبة آمنة للأطفال؟", "a": "نعم، اللعبة آمنة لجميع الأعمار."},
            ],
            "faq_en": [
                {"q": f"Is {title_ar} free to play?", "a": "Yes, play for free with no download required."},
                {"q": "Does it work on mobile?", "a": "Yes, fully optimized for mobile devices."},
                {"q": "How do I control the game?", "a": meta.get("controls_en", "Arrow keys on desktop, touch on mobile.")},
            ],
            "long_tail_keywords_ar": LONG_TAIL_TEMPLATES.get(game_type, [])[:3],
            "long_tail_keywords_en": [f"free {game_type} game online", f"best {game_type} game mobile"],
            "category_hub_link": f"/العاب-{game_type}",
            "internal_links_ar": [
                {"anchor": f"العاب {game_type} مجانية", "url": f"/العاب-{game_type}"},
                {"anchor": "جميع الألعاب", "url": "/الألعاب"},
            ],
        }
    return data, all_tokens, all_cost


def build_faq_schema(faq_items):
    """Build FAQ Page schema.org markup."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in faq_items[:10]
        ],
    }


def build_breadcrumb_schema(game_type, slug, title):
    """Build BreadcrumbList schema."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "يلا بلايز", "item": YALLAPLAYS_BASE_URL},
            {"@type": "ListItem", "position": 2, "name": f"العاب {game_type}", "item": f"{YALLAPLAYS_BASE_URL}/العاب-{game_type}"},
            {"@type": "ListItem", "position": 3, "name": title, "item": f"{YALLAPLAYS_BASE_URL}/games/{slug}"},
        ],
    }


def build_game_seo_page(game_data, faq_data, related_games):
    """Build complete SEO page data for a game."""
    meta = game_data.get("metadata", {})
    game_type = game_data.get("game_type", "racing")
    game_id = game_data.get("game_id", "")

    faq_schema_ar = build_faq_schema(faq_data.get("faq_ar", []))
    faq_schema_en = build_faq_schema(faq_data.get("faq_en", []))
    breadcrumb_ar = build_breadcrumb_schema(game_type, meta.get("slug_ar", game_id), meta.get("title_ar", ""))
    breadcrumb_en = build_breadcrumb_schema(game_type, meta.get("slug_en", game_id), meta.get("title_en", ""))

    return {
        "game_id": game_id,
        "game_type": game_type,
        "seo_ar": {
            "title": meta.get("title_ar", ""),
            "meta_description": meta.get("meta_desc_ar", meta.get("desc_ar", "")),
            "slug": meta.get("slug_ar", f"العاب-{game_type}"),
            "h1": meta.get("title_ar", ""),
            "intro_paragraph": meta.get("desc_ar", ""),
            "keywords": meta.get("keywords_ar", []) + faq_data.get("long_tail_keywords_ar", []),
            "faq": faq_data.get("faq_ar", []),
            "instructions": meta.get("instructions_ar", []),
            "controls": meta.get("controls_ar", ""),
            "internal_links": faq_data.get("internal_links_ar", []),
            "category_hub": faq_data.get("category_hub_link", f"/العاب-{game_type}"),
            "related_games": related_games[:6],
            "lang": "ar",
            "dir": "rtl",
        },
        "seo_en": {
            "title": meta.get("title_en", ""),
            "meta_description": meta.get("desc_en", ""),
            "slug": meta.get("slug_en", f"{game_type}-game"),
            "h1": meta.get("title_en", ""),
            "intro_paragraph": meta.get("desc_en", ""),
            "keywords": meta.get("keywords_en", []) + faq_data.get("long_tail_keywords_en", []),
            "faq": faq_data.get("faq_en", []),
            "instructions": meta.get("instructions_en", []),
            "controls": meta.get("controls_en", ""),
            "related_games": related_games[:6],
            "lang": "en",
            "dir": "ltr",
        },
        "schemas": {
            "video_game": game_data.get("schema", {}),
            "faq_ar": faq_schema_ar,
            "faq_en": faq_schema_en,
            "breadcrumb_ar": breadcrumb_ar,
            "breadcrumb_en": breadcrumb_en,
        },
        "long_tail_keywords_ar": faq_data.get("long_tail_keywords_ar", []),
        "long_tail_keywords_en": faq_data.get("long_tail_keywords_en", []),
        "estimated_monthly_searches": sum(
            800 for _ in faq_data.get("long_tail_keywords_ar", [])
        ),
        "generated_at": now_iso(),
    }


def generate_category_hub(game_type, games_of_type):
    """Generate category hub page data for a game type."""
    config_keywords_ar = LONG_TAIL_TEMPLATES.get(game_type, [])
    return {
        "category": game_type,
        "slug_ar": f"العاب-{game_type}",
        "slug_en": f"{game_type}-games",
        "title_ar": f"أفضل العاب {game_type} مجانية اون لاين | يلا بلايز",
        "title_en": f"Best Free {game_type.capitalize()} Games Online | Yalla Plays",
        "meta_desc_ar": f"العب أفضل العاب {game_type} المجانية على يلا بلايز. {len(games_of_type)} لعبة متاحة بدون تحميل.",
        "games": [{"game_id": g.get("game_id"), "title_ar": (g.get("metadata") or {}).get("title_ar", ""), "slug": (g.get("metadata") or {}).get("slug_ar", "")} for g in games_of_type[:20]],
        "long_tail_keywords": config_keywords_ar,
        "faq_schema": build_faq_schema([
            {"q": f"هل العاب {game_type} مجانية؟", "a": "نعم، جميع الألعاب مجانية تماماً بدون تحميل."},
            {"q": f"هل تعمل العاب {game_type} على الموبايل؟", "a": "نعم، جميع الألعاب محسّنة للأجهزة المحمولة."},
        ]),
        "game_count": len(games_of_type),
        "generated_at": now_iso(),
    }


def main():
    print("[game_seo] Starting game SEO generation...")
    all_tokens, all_cost = 0, 0.0
    SEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    games = load_all_games()
    print(f"[game_seo] Found {len(games)} games to process")

    if not games:
        print("[game_seo] No games found — run game_factory first")
        report = {"generated_at": now_iso(), "games_processed": 0, "tokens_used": 0, "cost_usd": 0.0, "ai_generated": True}
        (MEMORY_DIR / "game_seo_report.json").write_text(json.dumps(report, indent=2))
        return

    # Build related games index
    games_by_type = {}
    for g in games:
        gt = g.get("game_type", "racing")
        games_by_type.setdefault(gt, []).append(g)

    seo_pages = []
    category_hubs = {}

    for game_data in games:
        game_id = game_data.get("game_id", "")
        game_type = game_data.get("game_type", "racing")
        print(f"[game_seo] Processing {game_id}...")

        related_types = RELATED_BY_TYPE.get(game_type, ["racing", "puzzle"])
        related_games = []
        for rt in related_types:
            for rg in games_by_type.get(rt, [])[:2]:
                if rg.get("game_id") != game_id:
                    related_games.append({
                        "game_id": rg.get("game_id"),
                        "title_ar": (rg.get("metadata") or {}).get("title_ar", ""),
                        "slug_ar": (rg.get("metadata") or {}).get("slug_ar", ""),
                        "game_type": rt,
                    })

        faq_data, all_tokens, all_cost = generate_game_faq(game_data, all_tokens, all_cost)
        seo_page = build_game_seo_page(game_data, faq_data, related_games)
        seo_pages.append(seo_page)

        # Save individual game SEO
        seo_file = SEO_OUTPUT_DIR / f"seo_{game_id}.json"
        seo_file.write_text(json.dumps(seo_page, indent=2, ensure_ascii=False))

        if game_type not in category_hubs:
            category_hubs[game_type] = generate_category_hub(game_type, games_by_type.get(game_type, []))

    # Save all category hubs
    hubs_file = SEO_OUTPUT_DIR / "category_hubs.json"
    hubs_file.write_text(json.dumps(list(category_hubs.values()), indent=2, ensure_ascii=False))

    total_keywords = sum(len(p.get("long_tail_keywords_ar", [])) + len(p.get("long_tail_keywords_en", [])) for p in seo_pages)

    report = {
        "generated_at": now_iso(),
        "games_processed": len(seo_pages),
        "category_hubs": len(category_hubs),
        "total_keywords": total_keywords,
        "estimated_total_monthly_searches": sum(p.get("estimated_monthly_searches", 0) for p in seo_pages),
        "seo_pages": [
            {
                "game_id": p["game_id"],
                "game_type": p["game_type"],
                "title_ar": p["seo_ar"].get("title", ""),
                "title_en": p["seo_en"].get("title", ""),
                "keywords_count": len(p.get("long_tail_keywords_ar", [])),
                "schemas_count": len(p.get("schemas", {})),
            }
            for p in seo_pages
        ],
        "category_hub_types": list(category_hubs.keys()),
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "game_seo_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[game_seo] Done — {len(seo_pages)} SEO pages, {len(category_hubs)} hubs, {total_keywords} keywords, ${all_cost:.4f}")


if __name__ == "__main__":
    main()

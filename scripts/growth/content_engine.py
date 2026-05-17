"""
AI Content Expansion Engine
Generates SEO pages, multilingual pages, game landing pages, category pages,
structured data (JSON-LD), and related content for YallaPlays and other projects.
"""
import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.intelligence.registry import get_project
from scripts.intelligence.report_store import save, REPORTS_ROOT

REPORT_TYPE = "content"

# ──────────────────────────────────────────────────────────────────────────────
# Language data
# ──────────────────────────────────────────────────────────────────────────────

LANGS = {
    "ar": {"dir": "rtl", "label": "العربية", "locale": "ar_SA"},
    "en": {"dir": "ltr", "label": "English",  "locale": "en_US"},
    "fr": {"dir": "ltr", "label": "Français", "locale": "fr_FR"},
    "tr": {"dir": "ltr", "label": "Türkçe",   "locale": "tr_TR"},
}

GAME_CATEGORIES = {
    "action":    {"ar": "ألعاب الأكشن",   "en": "Action Games"},
    "puzzle":    {"ar": "ألعاب الألغاز",  "en": "Puzzle Games"},
    "sports":    {"ar": "ألعاب الرياضة",  "en": "Sports Games"},
    "racing":    {"ar": "ألعاب السباقات", "en": "Racing Games"},
    "strategy":  {"ar": "ألعاب الاستراتيجية", "en": "Strategy Games"},
    "adventure": {"ar": "ألعاب المغامرات", "en": "Adventure Games"},
    "arcade":    {"ar": "ألعاب الآركيد",  "en": "Arcade Games"},
    "casual":    {"ar": "ألعاب كاجوال",   "en": "Casual Games"},
    "kids":      {"ar": "ألعاب الأطفال",  "en": "Kids Games"},
    "math":      {"ar": "ألعاب الرياضيات", "en": "Math Games"},
}


# ──────────────────────────────────────────────────────────────────────────────
# Structured data generators (JSON-LD)
# ──────────────────────────────────────────────────────────────────────────────

def build_website_schema(domain: str, name: str, description: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": name,
        "url": f"https://{domain}",
        "description": description,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": f"https://{domain}/games?q={{search_term_string}}"},
            "query-input": "required name=search_term_string",
        },
    }


def build_game_schema(game: dict, domain: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "name": game.get("name", ""),
        "description": game.get("description", ""),
        "url": f"https://{domain}/games/{game.get('slug', '')}",
        "image": game.get("thumbnail", f"https://{domain}/thumbnails/{game.get('slug', '')}.png"),
        "genre": game.get("category", "Arcade"),
        "gamePlatform": "Web Browser",
        "applicationCategory": "Game",
        "operatingSystem": "Any",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Organization", "name": "YallaPlays"},
        "inLanguage": ["ar", "en"],
    }


def build_breadcrumb_schema(items: list[dict], domain: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": item["name"],
                "item": f"https://{domain}{item['path']}",
            }
            for i, item in enumerate(items)
        ],
    }


def build_faq_schema(faqs: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["question"],
                "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
            }
            for faq in faqs
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Game landing page generator
# ──────────────────────────────────────────────────────────────────────────────

def generate_game_landing_page(game: dict, domain: str, lang: str = "ar") -> dict:
    """
    Generate a complete game landing page specification.
    Returns content structure ready for Next.js page generation.
    """
    slug = game.get("slug", re.sub(r"[^a-z0-9]+", "-", game.get("name", "game").lower()))
    lang_data = LANGS.get(lang, LANGS["ar"])
    category = game.get("category", "arcade")
    cat_name = GAME_CATEGORIES.get(category, {}).get(lang, category.title())
    game_name = game.get("name", "")
    description = game.get("description", f"Play {game_name} online for free")

    title_ar = f"العب {game_name} مجاناً | يلا بلاي"
    title_en = f"Play {game_name} Free Online | YallaPlays"
    title = title_ar if lang == "ar" else title_en

    desc_ar = f"العب {game_name} مجاناً من متصفحك. لعبة {cat_name} ممتعة بدون تحميل. {description[:100]}"
    desc_en = f"Play {game_name} free online. No download required. {description[:100]}"
    meta_desc = desc_ar if lang == "ar" else desc_en

    canonical = f"https://{domain}/games/{slug}"

    schemas = [
        build_game_schema(game, domain),
        build_breadcrumb_schema([
            {"name": "الرئيسية" if lang == "ar" else "Home", "path": "/"},
            {"name": "الألعاب" if lang == "ar" else "Games", "path": "/games"},
            {"name": game_name, "path": f"/games/{slug}"},
        ], domain),
    ]

    faqs_ar = [
        {"question": f"كيف ألعب {game_name}؟", "answer": f"افتح الصفحة واضغط ابدأ — لا تحميل مطلوب."},
        {"question": f"هل {game_name} مجانية؟", "answer": "نعم، جميع ألعاب يلا بلاي مجانية 100%."},
        {"question": "هل تعمل على الجوال؟", "answer": "نعم، مُحسَّنة لجميع الأجهزة."},
    ]
    faqs_en = [
        {"question": f"How do I play {game_name}?", "answer": "Open the page and press Start — no download needed."},
        {"question": f"Is {game_name} free?", "answer": "Yes, all YallaPlays games are 100% free."},
        {"question": "Does it work on mobile?", "answer": "Yes, optimized for all devices."},
    ]
    faqs = faqs_ar if lang == "ar" else faqs_en
    schemas.append(build_faq_schema(faqs))

    return {
        "slug": slug,
        "lang": lang,
        "dir": lang_data["dir"],
        "title": title,
        "meta_description": meta_desc,
        "canonical": canonical,
        "og": {
            "title": title,
            "description": meta_desc,
            "image": game.get("thumbnail", f"https://{domain}/thumbnails/{slug}.png"),
            "type": "website",
            "url": canonical,
        },
        "schemas": schemas,
        "faqs": faqs,
        "category": category,
        "category_name": cat_name,
        "content": {
            "h1": f"العب {game_name}" if lang == "ar" else f"Play {game_name}",
            "intro": meta_desc,
            "features": game.get("features", []),
            "controls": game.get("controls", ""),
        },
        "monetization": {
            "above_fold_slot": "before_game",
            "in_game_slot": "game_pause",
            "below_fold_slot": "related_games",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Category page generator
# ──────────────────────────────────────────────────────────────────────────────

def generate_category_page(category: str, games: list[dict], domain: str, lang: str = "ar") -> dict:
    """Generate a category page specification with full SEO metadata."""
    cat_data = GAME_CATEGORIES.get(category, {"ar": category, "en": category.title()})
    cat_name = cat_data.get(lang, cat_data.get("en", category))
    count = len(games)

    title_ar = f"أفضل {cat_name} مجانية | يلا بلاي — {count} لعبة"
    title_en = f"Best Free {cat_name} | YallaPlays — {count} Games"
    title = title_ar if lang == "ar" else title_en

    desc_ar = f"العب أفضل {cat_name} مجاناً من متصفحك. {count} لعبة {cat_name} متاحة بدون تحميل على يلا بلاي."
    desc_en = f"Play the best free {cat_name} online. {count} {cat_name} available with no download on YallaPlays."
    meta_desc = desc_ar if lang == "ar" else desc_en

    canonical = f"https://{domain}/games/category/{category}"
    schemas = [
        build_breadcrumb_schema([
            {"name": "الرئيسية" if lang == "ar" else "Home", "path": "/"},
            {"name": "الألعاب" if lang == "ar" else "Games", "path": "/games"},
            {"name": cat_name, "path": f"/games/category/{category}"},
        ], domain),
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": cat_name,
            "numberOfItems": count,
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "url": f"https://{domain}/games/{g.get('slug', '')}",
                 "name": g.get("name", "")}
                for i, g in enumerate(games[:10])
            ],
        },
    ]

    return {
        "category": category,
        "category_name": cat_name,
        "lang": lang,
        "title": title,
        "meta_description": meta_desc,
        "canonical": canonical,
        "schemas": schemas,
        "game_count": count,
        "games_preview": games[:12],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Multilingual page set generator
# ──────────────────────────────────────────────────────────────────────────────

def generate_multilingual_set(page_spec: dict, domain: str, target_langs: Optional[list] = None) -> dict:
    """Generate hreflang-linked versions of a page for multiple languages."""
    langs = target_langs or ["ar", "en"]
    base_path = page_spec.get("canonical", "").replace(f"https://{domain}", "")

    hreflang_tags = [
        {"lang": l, "url": f"https://{domain}{base_path}" + (f"?lang={l}" if l != "ar" else "")}
        for l in langs
    ]
    hreflang_tags.append({"lang": "x-default", "url": f"https://{domain}{base_path}"})

    return {
        "base_page": page_spec,
        "languages": langs,
        "hreflang_tags": hreflang_tags,
        "alternate_pages": {
            l: {**page_spec, "lang": l, "dir": LANGS.get(l, {}).get("dir", "ltr")}
            for l in langs
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Batch content generation
# ──────────────────────────────────────────────────────────────────────────────

def generate_content_plan(project_id: str, games: Optional[list] = None) -> dict:
    """Generate a full content expansion plan for a project."""
    p = get_project(project_id)
    domain = p["domain"]

    sample_games = games or [
        {"name": "سنيك", "slug": "snake", "category": "arcade", "description": "لعبة الأفعى الكلاسيكية"},
        {"name": "تيتريس", "slug": "tetris", "category": "puzzle", "description": "لعبة الألغاز الشهيرة"},
        {"name": "فلابي بيرد", "slug": "flappy", "category": "casual", "description": "لعبة العصفور الطائر"},
        {"name": "باكمان", "slug": "pacman", "category": "arcade", "description": "لعبة باكمان الكلاسيكية"},
        {"name": "رسم وتلوين", "slug": "coloring", "category": "kids", "description": "ألعاب التلوين للأطفال"},
    ]

    game_pages = [generate_game_landing_page(g, domain, "ar") for g in sample_games]
    category_pages = [
        generate_category_page(cat, [g for g in sample_games if g.get("category") == cat], domain, "ar")
        for cat in set(g.get("category", "arcade") for g in sample_games)
    ]
    multilingual = [generate_multilingual_set(gp, domain) for gp in game_pages[:3]]

    report = {
        "project_id": project_id,
        "domain": domain,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_summary": {
            "game_landing_pages": len(game_pages),
            "category_pages": len(category_pages),
            "multilingual_sets": len(multilingual),
            "total_pages_to_create": len(game_pages) + len(category_pages),
        },
        "game_pages": game_pages,
        "category_pages": category_pages,
        "multilingual_sets": multilingual,
        "seo_impact": {
            "estimated_new_urls": len(game_pages) + len(category_pages),
            "estimated_indexed_keywords": len(game_pages) * 15 + len(category_pages) * 30,
            "schema_types": ["VideoGame", "BreadcrumbList", "FAQPage", "ItemList", "WebSite"],
        },
    }

    save(REPORT_TYPE, project_id, report)
    return report


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    r = generate_content_plan(pid)
    print(json.dumps({k: v for k, v in r.items() if k not in ("game_pages", "category_pages", "multilingual_sets")}, indent=2))
    print(f"\nPlan: {r['plan_summary']['total_pages_to_create']} pages to create")

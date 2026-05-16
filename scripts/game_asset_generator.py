"""
MIFTEH OS — Game Asset Generator
Generates SVG thumbnails, OG images, category banners, icons for YallaPlays.
Pure Python stdlib — no external image libraries required.
Outputs to outputs/yallaplays/assets/{game_id}/
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso

try:
    from telegram_notifier import send_system_log
except Exception:
    def send_system_log(*a, **kw): pass

MEMORY_DIR = Path("memory")
ASSETS_DIR = Path("outputs/yallaplays/assets")
CATEGORY_ASSETS_DIR = Path("outputs/yallaplays/category_assets")
ASSET_REPORT_FILE = MEMORY_DIR / "game_asset_report.json"
GAMES_DIR = Path("outputs/yallaplays/games")

# ─── Game type themes ─────────────────────────────────────────────────────────

THEMES = {
    "racing":   {"bg": "#0d1117", "bg2": "#1a2240", "accent": "#ef4444", "icon": "◇", "ar": "سباق"},
    "car":      {"bg": "#0f172a", "bg2": "#1e3a5f", "accent": "#3b82f6", "icon": "⬡", "ar": "سيارات"},
    "drift":    {"bg": "#1a0a00", "bg2": "#3d2000", "accent": "#f97316", "icon": "↻", "ar": "انجراف"},
    "action":   {"bg": "#150020", "bg2": "#2d0050", "accent": "#a855f7", "icon": "★", "ar": "أكشن"},
    "survival": {"bg": "#001a08", "bg2": "#003d15", "accent": "#22c55e", "icon": "◈", "ar": "بقاء"},
    "clicker":  {"bg": "#1a0010", "bg2": "#3d0030", "accent": "#ec4899", "icon": "◉", "ar": "نقر"},
    "idle":     {"bg": "#1a1000", "bg2": "#3d2800", "accent": "#eab308", "icon": "⬟", "ar": "خمول"},
    "puzzle":   {"bg": "#001220", "bg2": "#002d50", "accent": "#06b6d4", "icon": "◫", "ar": "ألغاز"},
    "kids":     {"bg": "#001a1a", "bg2": "#003d3d", "accent": "#14b8a6", "icon": "✦", "ar": "أطفال"},
    "brain":    {"bg": "#0a1a00", "bg2": "#1a3d00", "accent": "#84cc16", "icon": "◎", "ar": "ذكاء"},
}

DEFAULT_THEME = {"bg": "#0f172a", "bg2": "#1e3a5f", "accent": "#6366f1", "icon": "▣", "ar": "ألعاب"}

YALLAPLAYS_BRAND = "YallaPlays.com | يلا بلاي"


# ─── SVG builders ─────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """XML-escape text for SVG."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _truncate(text: str, max_len: int) -> str:
    if len(text) > max_len:
        return text[:max_len - 1] + "…"
    return text


def generate_thumbnail_svg(name_ar: str, name_en: str, game_type: str, game_id: str = "") -> str:
    """400x300 game thumbnail SVG."""
    t = THEMES.get(game_type, DEFAULT_THEME)
    name_ar = _esc(_truncate(name_ar, 22))
    name_en = _esc(_truncate(name_en, 28))
    icon = t["icon"]

    return f"""<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['bg']}"/>
      <stop offset="100%" stop-color="{t['bg2']}"/>
    </linearGradient>
    <linearGradient id="glowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['accent']}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{t['accent']}" stop-opacity="0.05"/>
    </linearGradient>
    <filter id="blur">
      <feGaussianBlur stdDeviation="8"/>
    </filter>
  </defs>
  <!-- Background -->
  <rect width="400" height="300" fill="url(#bgGrad)" rx="8"/>
  <!-- Glow circle -->
  <circle cx="200" cy="130" r="90" fill="url(#glowGrad)" filter="url(#blur)"/>
  <!-- Accent ring -->
  <circle cx="200" cy="130" r="70" fill="none" stroke="{t['accent']}" stroke-width="1.5" stroke-opacity="0.4"/>
  <circle cx="200" cy="130" r="55" fill="none" stroke="{t['accent']}" stroke-width="0.5" stroke-opacity="0.2"/>
  <!-- Central icon -->
  <text x="200" y="150" text-anchor="middle" dominant-baseline="middle"
        font-size="52" fill="{t['accent']}" opacity="0.9">{_esc(icon)}</text>
  <!-- Decorative dots -->
  <circle cx="80" cy="40" r="2" fill="{t['accent']}" opacity="0.4"/>
  <circle cx="320" cy="40" r="2" fill="{t['accent']}" opacity="0.4"/>
  <circle cx="60" cy="260" r="3" fill="{t['accent']}" opacity="0.3"/>
  <circle cx="340" cy="260" r="3" fill="{t['accent']}" opacity="0.3"/>
  <!-- Top accent bar -->
  <rect x="0" y="0" width="400" height="3" fill="{t['accent']}" rx="8" opacity="0.8"/>
  <!-- Arabic game name -->
  <text x="200" y="215" text-anchor="middle"
        font-family="'Tahoma','Arial','sans-serif'" font-size="20" font-weight="bold"
        fill="#ffffff" direction="rtl" unicode-bidi="bidi-override">{name_ar}</text>
  <!-- English subtitle -->
  <text x="200" y="242" text-anchor="middle"
        font-family="'Arial','Helvetica','sans-serif'" font-size="13"
        fill="{t['accent']}" letter-spacing="0.5">{name_en}</text>
  <!-- Brand -->
  <text x="200" y="278" text-anchor="middle"
        font-family="'Arial','Helvetica','sans-serif'" font-size="10"
        fill="#64748b">{_esc(YALLAPLAYS_BRAND)}</text>
  <!-- Category badge -->
  <rect x="14" y="14" width="72" height="22" rx="11" fill="{t['accent']}" opacity="0.15"/>
  <rect x="14" y="14" width="72" height="22" rx="11" fill="none" stroke="{t['accent']}" stroke-width="1" opacity="0.5"/>
  <text x="50" y="29" text-anchor="middle"
        font-family="'Tahoma','Arial','sans-serif'" font-size="10"
        fill="{t['accent']}" direction="rtl">{_esc(t['ar'])}</text>
</svg>"""


def generate_og_svg(name_ar: str, name_en: str, game_type: str, description_ar: str = "") -> str:
    """1200x630 OpenGraph image SVG."""
    t = THEMES.get(game_type, DEFAULT_THEME)
    name_ar = _esc(_truncate(name_ar, 30))
    name_en = _esc(_truncate(name_en, 40))
    desc_ar = _esc(_truncate(description_ar, 60)) if description_ar else ""
    icon = t["icon"]

    return f"""<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['bg']}"/>
      <stop offset="60%" stop-color="{t['bg2']}"/>
      <stop offset="100%" stop-color="{t['bg']}"/>
    </linearGradient>
    <linearGradient id="glowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['accent']}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="{t['accent']}" stop-opacity="0.02"/>
    </linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="20"/></filter>
  </defs>
  <rect width="1200" height="630" fill="url(#bgGrad)"/>
  <!-- Glow -->
  <circle cx="850" cy="315" r="250" fill="url(#glowGrad)" filter="url(#glow)"/>
  <!-- Right icon panel -->
  <circle cx="900" cy="315" r="180" fill="none" stroke="{t['accent']}" stroke-width="1.5" stroke-opacity="0.3"/>
  <circle cx="900" cy="315" r="140" fill="{t['accent']}" fill-opacity="0.07"/>
  <text x="900" y="355" text-anchor="middle" dominant-baseline="middle"
        font-size="120" fill="{t['accent']}" opacity="0.85">{_esc(icon)}</text>
  <!-- Top accent bar -->
  <rect x="0" y="0" width="1200" height="6" fill="{t['accent']}" opacity="0.9"/>
  <!-- Left content area -->
  <!-- Brand label -->
  <text x="80" y="90" font-family="'Arial','Helvetica','sans-serif'" font-size="16"
        fill="{t['accent']}" letter-spacing="3" opacity="0.8">YALLAPLAYS.COM</text>
  <!-- Arabic title -->
  <text x="80" y="260" font-family="'Tahoma','Arial','sans-serif'" font-size="64"
        font-weight="bold" fill="#ffffff" direction="rtl" unicode-bidi="bidi-override">{name_ar}</text>
  <!-- English title -->
  <text x="80" y="330" font-family="'Arial','Helvetica','sans-serif'" font-size="36"
        fill="{t['accent']}" letter-spacing="1">{name_en}</text>
  <!-- Description -->
  {f'<text x="80" y="395" font-family="Tahoma,Arial,sans-serif" font-size="22" fill="#94a3b8" direction="rtl" unicode-bidi="bidi-override">{desc_ar}</text>' if desc_ar else ''}
  <!-- Category tag -->
  <rect x="80" y="470" width="140" height="38" rx="19" fill="{t['accent']}" fill-opacity="0.15"/>
  <rect x="80" y="470" width="140" height="38" rx="19" fill="none" stroke="{t['accent']}" stroke-width="1.5" opacity="0.6"/>
  <text x="150" y="494" text-anchor="middle" font-family="Tahoma,Arial,sans-serif" font-size="16"
        fill="{t['accent']}" direction="rtl">{_esc(t['ar'])}</text>
  <!-- Bottom divider -->
  <line x1="80" y1="565" x2="700" y2="565" stroke="{t['accent']}" stroke-width="1" stroke-opacity="0.2"/>
  <text x="80" y="590" font-family="Arial,Helvetica,sans-serif" font-size="16"
        fill="#475569">العاب عربية مجانية اونلاين | Free Arabic Browser Games</text>
</svg>"""


def generate_category_banner_svg(game_type: str) -> str:
    """1200x400 category hub banner SVG."""
    t = THEMES.get(game_type, DEFAULT_THEME)
    labels = {
        "racing": "العاب سباق السيارات",
        "car": "العاب السيارات",
        "drift": "العاب الانجراف",
        "action": "العاب الأكشن",
        "survival": "العاب البقاء",
        "clicker": "العاب النقر",
        "idle": "العاب الخمول",
        "puzzle": "العاب الألغاز",
        "kids": "العاب الأطفال",
        "brain": "العاب الذكاء",
    }
    label_ar = labels.get(game_type, "يلا بلاي")
    label_en = game_type.replace("_", " ").title() + " Games"

    return f"""<svg width="1200" height="400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['bg']}"/>
      <stop offset="100%" stop-color="{t['bg2']}"/>
    </linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="25"/></filter>
  </defs>
  <rect width="1200" height="400" fill="url(#bgGrad)"/>
  <circle cx="600" cy="200" r="300" fill="{t['accent']}" fill-opacity="0.05" filter="url(#glow)"/>
  <rect x="0" y="0" width="1200" height="5" fill="{t['accent']}" opacity="0.9"/>
  <rect x="0" y="395" width="1200" height="5" fill="{t['accent']}" opacity="0.4"/>
  <text x="600" y="180" text-anchor="middle" dominant-baseline="middle"
        font-size="120" fill="{t['accent']}" opacity="0.15">{_esc(t['icon'])}</text>
  <text x="600" y="220" text-anchor="middle" font-family="Tahoma,Arial,sans-serif"
        font-size="52" font-weight="bold" fill="#ffffff" direction="rtl">{_esc(label_ar)}</text>
  <text x="600" y="280" text-anchor="middle" font-family="Arial,Helvetica,sans-serif"
        font-size="26" fill="{t['accent']}" letter-spacing="2">{_esc(label_en.upper())}</text>
  <text x="600" y="355" text-anchor="middle" font-family="Arial,Helvetica,sans-serif"
        font-size="16" fill="#64748b">{_esc(YALLAPLAYS_BRAND)}</text>
</svg>"""


def generate_icon_svg(name_ar: str, game_type: str) -> str:
    """64x64 icon SVG."""
    t = THEMES.get(game_type, DEFAULT_THEME)
    initial = name_ar[0] if name_ar else "ي"

    return f"""<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['bg2']}"/>
      <stop offset="100%" stop-color="{t['bg']}"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" fill="url(#bg)" rx="12"/>
  <rect x="0" y="0" width="64" height="2" fill="{t['accent']}" rx="12" opacity="0.8"/>
  <text x="32" y="42" text-anchor="middle" font-family="Tahoma,Arial,sans-serif"
        font-size="30" fill="{t['accent']}" font-weight="bold"
        direction="rtl">{_esc(initial)}</text>
</svg>"""


# ─── File saving ─────────────────────────────────────────────────────────────

def save_game_assets(game_id: str, metadata: dict) -> dict:
    """Generate and save all assets for a single game."""
    game_type = metadata.get("game_type", "racing")
    name_ar = metadata.get("name_ar", metadata.get("title_ar", "لعبة"))
    name_en = metadata.get("name_en", metadata.get("title_en", "Game"))
    desc_ar = metadata.get("description_ar", "")

    asset_dir = ASSETS_DIR / game_id
    asset_dir.mkdir(parents=True, exist_ok=True)

    saved = {}

    # Thumbnail
    thumb_svg = generate_thumbnail_svg(name_ar, name_en, game_type, game_id)
    (asset_dir / "thumbnail.svg").write_text(thumb_svg, encoding="utf-8")
    saved["thumbnail"] = str(asset_dir / "thumbnail.svg")

    # OG image
    og_svg = generate_og_svg(name_ar, name_en, game_type, desc_ar)
    (asset_dir / "og-image.svg").write_text(og_svg, encoding="utf-8")
    saved["og_image"] = str(asset_dir / "og-image.svg")

    # Icon
    icon_svg = generate_icon_svg(name_ar, game_type)
    (asset_dir / "icon.svg").write_text(icon_svg, encoding="utf-8")
    saved["icon"] = str(asset_dir / "icon.svg")

    # Asset manifest
    manifest = {
        "game_id": game_id,
        "game_type": game_type,
        "name_ar": name_ar,
        "name_en": name_en,
        "assets": saved,
        "generated_at": now_iso(),
    }
    (asset_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    return manifest


def save_category_banner(game_type: str) -> str:
    CATEGORY_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    banner_svg = generate_category_banner_svg(game_type)
    out_path = CATEGORY_ASSETS_DIR / f"banner_{game_type}.svg"
    out_path.write_text(banner_svg, encoding="utf-8")
    return str(out_path)


# ─── Batch runner ─────────────────────────────────────────────────────────────

def run_all_assets() -> dict:
    if not GAMES_DIR.exists():
        print("[assets] No games directory found")
        return {"games_processed": 0, "categories_processed": 0}

    game_dirs = [d for d in GAMES_DIR.iterdir() if d.is_dir()]
    results = []
    processed_types = set()

    for game_dir in sorted(game_dirs):
        meta_file = game_dir / "metadata.json"
        if not meta_file.exists():
            continue
        try:
            metadata = json.loads(meta_file.read_text())
        except Exception:
            continue

        game_id = game_dir.name
        game_type = metadata.get("game_type", "racing")
        print(f"[assets] Generating assets for {game_id} ({game_type})...")

        manifest = save_game_assets(game_id, metadata)
        results.append(manifest)
        processed_types.add(game_type)

    # Generate category banners for all game types seen
    cat_results = {}
    for gt in THEMES:
        path = save_category_banner(gt)
        cat_results[gt] = path

    report = {
        "generated_at": now_iso(),
        "games_processed": len(results),
        "categories_processed": len(cat_results),
        "game_assets": results,
        "category_banners": cat_results,
        "total_assets_generated": len(results) * 3 + len(cat_results),
    }

    MEMORY_DIR.mkdir(exist_ok=True)
    ASSET_REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[assets] Done — {len(results)} games, {len(cat_results)} category banners")
    return report


def main():
    send_system_log("workflow_started", "Game Asset Generator started", "info", {"phase": "M"})
    report = run_all_assets()
    send_system_log("workflow_completed",
                    f"Assets generated: {report['games_processed']} games, {report['categories_processed']} categories",
                    "success", {"total": report["total_assets_generated"]})


if __name__ == "__main__":
    main()

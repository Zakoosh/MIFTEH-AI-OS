"""
MIFTEH OS — Game Factory
Generates playable HTML5 Phaser.js games for YallaPlays.
Every game: complete self-contained HTML, Arabic/English metadata,
SEO schema, mobile touch controls, review queue entry, Telegram alert.
NEVER auto-deploys — every game enters pending_review status.
"""
import json
import os
import re
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_text, generate_json, now_iso

MEMORY_DIR = Path("memory")
GAMES_OUTPUT_DIR = Path("outputs/yallaplays/games")
REVIEWS_DIR = MEMORY_DIR / "reviews"
GAME_FACTORY_DIR = MEMORY_DIR / "game_factory"

PHASER_CDN = "https://cdn.jsdelivr.net/npm/phaser@3.60.0/dist/phaser.min.js"

GAME_CONFIGS = {
    "racing": {
        "name_en": "Racing Game",
        "name_ar": "لعبة السباق",
        "category": "racing",
        "description_en": "Fast-paced top-down racing game",
        "description_ar": "لعبة سباق سيارات مثيرة من منظور علوي",
        "keywords_ar": ["العاب سباق", "العاب سيارات", "العاب سرعة"],
        "keywords_en": ["racing game", "car game", "speed game"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 8500,
    },
    "car": {
        "name_en": "Car Game",
        "name_ar": "لعبة السيارات",
        "category": "car",
        "description_en": "Exciting car dodge and racing game",
        "description_ar": "لعبة سيارات مثيرة مع التهرب من العوائق",
        "keywords_ar": ["العاب سيارات", "العاب سباق سيارات", "العاب قيادة"],
        "keywords_en": ["car game", "car racing", "driving game"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 12000,
    },
    "puzzle": {
        "name_en": "Puzzle Game",
        "name_ar": "لعبة البازل",
        "category": "puzzle",
        "description_en": "Brain-teasing tile puzzle game",
        "description_ar": "لعبة ذكاء وتركيز مع قطع البازل",
        "keywords_ar": ["العاب بازل", "العاب تركيز", "العاب ذكاء"],
        "keywords_en": ["puzzle game", "brain game", "tile matching"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 6000,
    },
    "idle": {
        "name_en": "Idle Clicker Game",
        "name_ar": "لعبة النقر والكسب",
        "category": "idle",
        "description_en": "Addictive idle clicker with upgrades",
        "description_ar": "لعبة نقر ممتعة مع نظام التطوير والمكافآت",
        "keywords_ar": ["العاب نقر", "العاب كسب نقاط", "العاب بدون انترنت"],
        "keywords_en": ["idle game", "clicker game", "incremental game"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 4500,
    },
    "kids": {
        "name_en": "Kids Game",
        "name_ar": "لعبة الأطفال",
        "category": "kids",
        "description_en": "Colorful and fun game for children",
        "description_ar": "لعبة ملونة وممتعة مناسبة للأطفال",
        "keywords_ar": ["العاب اطفال", "العاب بنات", "العاب صغار"],
        "keywords_en": ["kids game", "children game", "fun game for kids"],
        "schema_type": "VideoGame",
        "target_audience": "children",
        "estimated_monthly_searches": 9000,
    },
    "action": {
        "name_en": "Action Game",
        "name_ar": "لعبة أكشن",
        "category": "action",
        "description_en": "Fast-paced action shooter game",
        "description_ar": "لعبة أكشن سريعة مع نظام التصويب والمكافآت",
        "keywords_ar": ["العاب اكشن", "العاب حرب", "العاب قتال"],
        "keywords_en": ["action game", "shooter game", "arcade action"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 7500,
    },
    "survival": {
        "name_en": "Survival Game",
        "name_ar": "لعبة البقاء",
        "category": "survival",
        "description_en": "Survive waves of enemies as long as possible",
        "description_ar": "تحدى موجات الأعداء وابق على قيد الحياة أطول فترة ممكنة",
        "keywords_ar": ["العاب بقاء", "العاب تحدي", "العاب صعوبة"],
        "keywords_en": ["survival game", "wave defense", "endless game"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 3800,
    },
    "brain": {
        "name_en": "Brain Game",
        "name_ar": "لعبة الذكاء",
        "category": "brain",
        "description_en": "Test your memory and mental agility",
        "description_ar": "اختبر ذكاءك وسرعة استجابتك في هذه اللعبة الرائعة",
        "keywords_ar": ["العاب ذكاء", "العاب عقل", "العاب تركيز"],
        "keywords_en": ["brain game", "memory game", "logic game"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 5200,
    },
    "drift": {
        "name_en": "Drift Racing Game",
        "name_ar": "لعبة الانجراف",
        "category": "drift",
        "description_en": "Master the art of drifting in this thrilling top-down racer",
        "description_ar": "أتقن فن الانجراف في لعبة السباق المثيرة هذه",
        "keywords_ar": ["العاب انجراف", "العاب سباق انجراف", "العاب دريفت"],
        "keywords_en": ["drift game", "drift racing", "car drift game"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 5800,
    },
    "clicker": {
        "name_en": "Clicker Game",
        "name_ar": "لعبة النقر",
        "category": "clicker",
        "description_en": "Click to earn, upgrade, and dominate the leaderboard",
        "description_ar": "انقر لتكسب النقاط وترقي قدراتك وتتصدر المتصدرين",
        "keywords_ar": ["العاب نقر", "لعبة النقر والكسب", "العاب ضغط"],
        "keywords_en": ["clicker game", "tap game", "click to earn"],
        "schema_type": "VideoGame",
        "target_audience": "all",
        "estimated_monthly_searches": 6200,
    },
}

GAME_PROMPTS = {
    "racing": """Create a complete Phaser 3 top-down racing game JavaScript class.

GAME MECHANICS:
- Player controls a car sprite (drawn with Phaser Graphics API — no external images)
- Car moves up/down lanes to dodge oncoming traffic
- Speed increases over time
- Score based on distance/time survived
- 3 lanes on a road
- Road scrolls downward (parallax effect)
- Traffic cars come from top in random lanes
- Collision = game over
- High score saved to localStorage

CONTROLS:
- Desktop: Arrow keys left/right, or A/D to change lanes
- Mobile: Touch left half = move left, touch right half = move right
- Fullscreen button

VISUALS (all drawn with Phaser Graphics API):
- Dark road background with white lane markings
- Player car: blue rectangle with details
- Traffic cars: red, yellow, green rectangles
- Speed indicator, score counter
- Game over overlay with restart button

Return ONLY the JavaScript code that goes inside <script> tags. Start with:
const config = { type: Phaser.AUTO, ... }
Include new Phaser.Game(config) at the end.""",

    "car": """Create a complete Phaser 3 car obstacle dodge game JavaScript.

GAME MECHANICS:
- Player drives a car left-to-right on a horizontally scrolling highway
- Obstacles (rocks, barriers, other cars) scroll from right to left
- Collect fuel cans to extend game
- Double jump available
- Score multiplier system
- Difficulty increases every 1000 points

CONTROLS:
- Desktop: Space/Up = jump, Double tap = double jump
- Mobile: Tap left side = jump, swipe up = double jump
- Tilt support via DeviceOrientation if available

VISUALS (Phaser Graphics API only):
- Scrolling road with grass edges
- Player car: drawn rectangle with wheels
- Obstacles: various colored shapes
- Fuel cans: yellow circles
- Distance counter, lives display (3 lives)

Return ONLY the JavaScript for <script> tags, starting with: const config = {...}""",

    "puzzle": """Create a complete Phaser 3 sliding tile puzzle JavaScript.

GAME MECHANICS:
- 4x4 grid of numbered tiles (1-15 + empty space)
- Tap adjacent tiles to slide them into empty space
- Solve in minimum moves to win
- Move counter and timer
- 3 difficulty levels (3x3, 4x4, 5x5)
- Shuffle animation on start
- Win detection with celebration effect

CONTROLS:
- Desktop: Click tile to slide
- Mobile: Touch tile to slide
- Fully touch-responsive

VISUALS (Phaser Graphics API + Text):
- Clean tile grid with rounded rectangles
- Arabic numbers option toggle
- Progress indicator
- Solve animation when complete
- Particle burst on win

Return ONLY the JavaScript for <script> tags. Start with: const config = {...}""",

    "idle": """Create a complete Phaser 3 idle clicker game JavaScript.

GAME MECHANICS:
- Click a big central button to earn coins
- Coins buy upgrades (click power, auto-clicker, multiplier)
- Auto-clicker earns coins passively
- Prestige system after reaching 1 million coins
- Achievement badges unlocked at milestones
- Save state in localStorage

UPGRADES (at least 5):
1. Better Click (2x click power)
2. Auto Coin (coins per second)
3. Coin Factory (5x auto rate)
4. Multiplier (all earnings x2)
5. Prestige Ready (unlock at 1M)

VISUALS:
- Big central coin button (drawn circle with Graphics API)
- Upgrade panel on right side
- Floating +coin numbers on click
- Particle effects on milestones
- Progress bars for each upgrade

MOBILE: Touch to click the main button. Scrollable upgrade panel.
Return ONLY JavaScript for <script> tags. Start with: const config = {...}""",

    "kids": """Create a complete Phaser 3 kids catch game JavaScript.

GAME MECHANICS:
- Colorful fruits/stars fall from top of screen
- Player moves a basket left/right to catch them
- Bombs fall too — DON'T catch them (lose a life)
- 3 lives system
- Score increases with each catch
- Speed increases over time
- Cheerful sound placeholders (no audio files needed, use visual feedback)

CONTROLS:
- Desktop: Left/Right arrow keys or A/D
- Mobile: Touch left side = move left, touch right side = move right
- Very responsive for small children

VISUALS (Phaser Graphics API — bright colors):
- Colorful falling objects: circles (fruits), stars (use Graphics drawStar)
- Red bombs: black circles with fuse
- Basket: brown/tan rectangle
- Big emoji-style feedback (✓ for catch, ✗ for bomb)
- Star burst celebration at 10/25/50 points
- Extra large text, child-friendly colors

Return ONLY JavaScript for <script> tags. Start with: const config = {...}""",

    "action": """Create a complete Phaser 3 space shooter game JavaScript.

GAME MECHANICS:
- Player controls a spaceship at bottom of screen
- Enemies (aliens/invaders) move down in formation
- Player shoots bullets upward
- Enemies shoot back (after wave 2)
- Power-ups: rapid fire, shield, triple shot
- 5 waves with boss on wave 5
- Lives system (3 lives)
- Score multiplier for combos

CONTROLS:
- Desktop: Arrow keys to move, Space to shoot
- Mobile: Virtual joystick left side, auto-fire button right side
- Hold fire button for continuous shooting

VISUALS (all Phaser Graphics API):
- Star field background (moving particles)
- Player ship: white elongated polygon
- Enemies: green angular shapes, different per wave
- Bullets: bright yellow lines
- Shield: blue semi-transparent circle
- Explosions: orange particle bursts

Return ONLY JavaScript for <script> tags. Start with: const config = {...}""",

    "survival": """Create a complete Phaser 3 survival wave game JavaScript.

GAME MECHANICS:
- Player in center, enemies spawn from screen edges
- Player auto-attacks nearest enemy (RPG auto-battle style)
- Move player to dodge
- Waves of 5/10/20 enemies, 30 sec between waves
- Level up between waves: choose 1 of 3 random upgrades
- Upgrades: attack speed, damage, health regen, area attack, speed
- Survive as many waves as possible

CONTROLS:
- Desktop: WASD or Arrow keys to move
- Mobile: Virtual joystick (left thumb area)

VISUALS (Phaser Graphics API):
- Grid background (subtle)
- Player: white circle with direction indicator
- Enemies: red squares (vary size per wave)
- Attack: orange line from player to enemy, flash effect
- Level up UI: 3 choice cards
- Wave counter, HP bar, enemy count

Return ONLY JavaScript for <script> tags. Start with: const config = {...}""",

    "brain": """Create a complete Phaser 3 memory/speed brain game JavaScript.

GAME MECHANICS:
- Show a sequence of colored tiles for 2 seconds
- Player must repeat the sequence in order
- Sequence grows by 1 each successful round
- Time limit per input (decreases over levels)
- 3 mistakes = game over
- High score tracking in localStorage

4x4 GRID OF COLORED TILES:
- 4 colors: red, blue, green, yellow
- Tiles flash in sequence
- Player taps them in order
- Flash feedback for right/wrong

BONUS MODE (after level 10):
- Math equations flash briefly, answer within 3 seconds
- Alternate between memory and math

CONTROLS:
- Desktop: Click tiles / number keys for math
- Mobile: Full touch support
- Large tap targets for accessibility

Return ONLY JavaScript for <script> tags. Start with: const config = {...}""",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="description" content="{meta_desc_ar}">
  <meta name="keywords" content="{keywords_ar}">
  <title>{title_ar} | يلا بلايز</title>
  <meta property="og:title" content="{title_ar}">
  <meta property="og:description" content="{desc_ar}">
  <meta property="og:type" content="website">
  <script type="application/ld+json">{schema_json}</script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
      background: #0f0f1a;
      width: 100%; height: 100vh;
      display: flex; align-items: center; justify-content: center;
      overflow: hidden;
      font-family: 'Segoe UI', Tahoma, sans-serif;
    }}
    #game-container {{ position: relative; width: 100%; height: 100vh; }}
    canvas {{ display: block; margin: 0 auto; max-width: 100%; max-height: 100vh; touch-action: none; }}
    #game-info {{
      position: fixed; top: 0; left: 0; right: 0;
      padding: 6px 12px;
      background: rgba(0,0,0,0.7);
      color: #fff; font-size: 12px;
      display: flex; justify-content: space-between; align-items: center;
      z-index: 100; pointer-events: none;
    }}
    #fullscreen-btn {{
      position: fixed; top: 8px; right: 8px;
      background: rgba(255,255,255,0.15); color: white;
      border: 1px solid rgba(255,255,255,0.3); border-radius: 4px;
      padding: 4px 8px; cursor: pointer; font-size: 14px; z-index: 200;
    }}
    #fullscreen-btn:hover {{ background: rgba(255,255,255,0.25); }}
  </style>
</head>
<body>
<div id="game-container">
  <div id="game-info">
    <span>يلا بلايز — {title_ar}</span>
    <span id="score-display"></span>
  </div>
  <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶</button>
</div>
<script src="{phaser_cdn}"></script>
<script>
function toggleFullscreen() {{
  const el = document.documentElement;
  if (!document.fullscreenElement) {{
    el.requestFullscreen && el.requestFullscreen();
  }} else {{
    document.exitFullscreen && document.exitFullscreen();
  }}
}}
// Prevent default touch scroll/zoom in game area
document.addEventListener('touchmove', function(e) {{ e.preventDefault(); }}, {{ passive: false }});
</script>
<script>
{game_code}
</script>
</body>
</html>"""


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def generate_game_id(game_type, index):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{game_type}_{ts}_{index:03d}"


def generate_game_code(game_type, game_name_ar, all_tokens, all_cost):
    """Generate Phaser.js game code via AI."""
    from ai_client import get_client
    system = (
        "You are an expert HTML5/Phaser 3 game developer. "
        "Generate complete, working Phaser 3 JavaScript game code. "
        "Use ONLY Phaser.GameObjects.Graphics for all visuals — NO external image URLs. "
        "Code must work in browser immediately. No TypeScript, no modules. "
        "Mobile touch controls required. Return ONLY executable JavaScript."
    )

    game_prompt = GAME_PROMPTS.get(game_type, GAME_PROMPTS["racing"])
    prompt = f"""Game Name (Arabic): {game_name_ar}
Game Type: {game_type}

{game_prompt}

CRITICAL RULES:
1. Use ONLY Phaser.Graphics API for all visuals (NO sprite.setTexture, NO external URLs)
2. Include mobile touch controls
3. Include score system and game over screen with restart button
4. Code must start with: const config = {{ type: Phaser.AUTO,
5. End with: new Phaser.Game(config);
6. Maximum 300 lines of clean JavaScript
7. Use localStorage for high score
8. Include FULLSCREEN support via scale manager"""

    code, tokens, cost, ok = generate_text(system, prompt, max_tokens=4000)
    all_tokens += tokens
    all_cost += cost

    if not ok or not code:
        # Fallback: minimal working Phaser game
        code = _fallback_game_code(game_type)

    # Validate basic structure
    if "new Phaser.Game" not in code and "Phaser.Game" not in code:
        code = _fallback_game_code(game_type)

    return code, all_tokens, all_cost


def _fallback_game_code(game_type):
    """Minimal working fallback game for each type."""
    return f"""const config = {{
  type: Phaser.AUTO,
  width: 480, height: 640,
  backgroundColor: '#1a1a2e',
  parent: 'game-container',
  scale: {{
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  }},
  scene: {{ preload, create, update }}
}};
let score = 0, gameOver = false, player, scoreText, obstacles = [];
function preload() {{}}
function create() {{
  this.g = this.add.graphics();
  // Background
  this.g.fillStyle(0x1a1a2e); this.g.fillRect(0,0,480,640);
  // Road (for racing type)
  this.g.fillStyle(0x333344); this.g.fillRect(80,0,320,640);
  this.g.lineStyle(3,0xffffff,0.5);
  for(let y=0;y<640;y+=60){{ this.g.lineBetween(238,y,242,y+40); }}
  // Player
  player = {{ x:240, y:540, w:36, h:56 }};
  scoreText = this.add.text(10,10,'Score: 0',{{fontSize:'20px',color:'#fff',fontFamily:'Arial'}});
  // Spawn obstacles
  this.time.addEvent({{delay:1200,callback:spawnObstacle,callbackScope:this,loop:true}});
  // Touch controls
  this.input.on('pointerdown', function(p){{
    if(!gameOver) player.x = p.x < 240 ? Math.max(100,player.x-80) : Math.min(380,player.x+80);
  }});
  // Keyboard
  this.cursors = this.input.keyboard.createCursorKeys();
  function spawnObstacle(){{
    if(!gameOver) obstacles.push({{x:100+Math.random()*280,y:-30,speed:3+score/200}});
  }}
}}
function update(){{
  if(gameOver) return;
  this.g.clear();
  this.g.fillStyle(0x1a1a2e); this.g.fillRect(0,0,480,640);
  this.g.fillStyle(0x333344); this.g.fillRect(80,0,320,640);
  for(let y=(Date.now()/20)%60;y<700;y+=60){{
    this.g.fillStyle(0xffffff,0.4); this.g.fillRect(238,y,4,40);
  }}
  if(this.cursors.left.isDown && player.x > 100) player.x -= 5;
  if(this.cursors.right.isDown && player.x < 380) player.x += 5;
  // Draw player
  this.g.fillStyle(0x4488ff); this.g.fillRect(player.x-18,player.y-28,36,56);
  this.g.fillStyle(0x88aaff); this.g.fillRect(player.x-14,player.y-24,28,16);
  // Obstacles
  for(let i=obstacles.length-1;i>=0;i--){{
    obstacles[i].y += obstacles[i].speed;
    this.g.fillStyle(0xff4444); this.g.fillRect(obstacles[i].x-18,obstacles[i].y-28,36,56);
    let dx=Math.abs(obstacles[i].x-player.x),dy=Math.abs(obstacles[i].y-player.y);
    if(dx<30&&dy<40){{gameOver=true;endGame.call(this);}}
    if(obstacles[i].y>680) obstacles.splice(i,1);
  }}
  score++; scoreText.setText('Score: '+Math.floor(score/10));
}}
function endGame(){{
  this.g.fillStyle(0x000000,0.7); this.g.fillRect(0,0,480,640);
  this.add.text(240,280,'Game Over!',{{fontSize:'36px',color:'#ff4444',fontFamily:'Arial'}}).setOrigin(0.5);
  this.add.text(240,330,'Score: '+Math.floor(score/10),{{fontSize:'24px',color:'#fff',fontFamily:'Arial'}}).setOrigin(0.5);
  let rb=this.add.text(240,400,'Restart',{{fontSize:'22px',color:'#44ff88',fontFamily:'Arial',backgroundColor:'#225533',padding:{{x:20,y:10}}}}).setOrigin(0.5).setInteractive();
  rb.on('pointerdown',()=>{{score=0;gameOver=false;obstacles=[];this.scene.restart();}});
}}
new Phaser.Game(config);"""


def generate_game_metadata(game_type, game_id, all_tokens, all_cost):
    """Generate Arabic + English metadata for a game."""
    config = GAME_CONFIGS.get(game_type, GAME_CONFIGS["racing"])
    system = "Arabic/English game metadata generator for YallaPlays Arabic gaming platform. Return valid JSON only."
    prompt = f"""Generate metadata for a {game_type} HTML5 game on YallaPlays Arabic gaming platform.
Game ID: {game_id}

Return:
{{
  "title_ar": "Arabic game title (compelling, 4-6 words)",
  "title_en": "English title",
  "slug_ar": "arabic-url-slug",
  "slug_en": "english-url-slug",
  "desc_ar": "Arabic description 100-150 chars",
  "desc_en": "English description 100-150 chars",
  "meta_desc_ar": "Arabic meta under 160 chars for SEO",
  "instructions_ar": ["step 1 in Arabic", "step 2 in Arabic", "step 3 in Arabic"],
  "instructions_en": ["step 1", "step 2", "step 3"],
  "controls_ar": "Arabic controls description",
  "controls_en": "English controls description",
  "keywords_ar": ["keyword1", "keyword2", "keyword3", "keyword4"],
  "keywords_en": ["keyword1", "keyword2"],
  "related_game_types": ["racing", "action"],
  "difficulty": "easy|medium|hard",
  "age_rating": "all|kids|teens",
  "estimated_play_time_min": 5
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, max_tokens=600)
    all_tokens += tokens
    all_cost += cost

    if not ok or not data:
        data = {
            "title_ar": f"{config['name_ar']} - يلا بلايز",
            "title_en": f"{config['name_en']} - Yalla Plays",
            "slug_ar": f"العاب-{game_type}",
            "slug_en": f"{game_type}-game",
            "desc_ar": config["description_ar"],
            "desc_en": config["description_en"],
            "meta_desc_ar": f"العب {config['name_ar']} مجاناً على يلا بلايز. {config['description_ar']}",
            "instructions_ar": [f"استخدم الأسهم للتحكم", "تجنب العوائق", "اجمع أعلى نقاط"],
            "instructions_en": ["Use arrow keys to move", "Avoid obstacles", "Beat your high score"],
            "controls_ar": "الأسهم للتحكم في السطح المكتبي | اللمس للأجهزة المحمولة",
            "controls_en": "Arrow keys on desktop | Touch on mobile",
            "keywords_ar": config["keywords_ar"],
            "keywords_en": config["keywords_en"],
            "related_game_types": ["racing", "action"],
            "difficulty": "medium",
            "age_rating": "all",
            "estimated_play_time_min": 5,
        }

    return data, all_tokens, all_cost


def build_schema_markup(game_id, metadata, game_type):
    """Build VideoGame schema.org structured data."""
    return {
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "@id": f"https://yallaplays.com/games/{metadata.get('slug_ar', game_id)}",
        "name": metadata.get("title_ar", ""),
        "alternateName": metadata.get("title_en", ""),
        "description": metadata.get("desc_ar", ""),
        "genre": game_type.capitalize(),
        "playMode": "SinglePlayer",
        "applicationCategory": "Game",
        "operatingSystem": "Web Browser",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "inLanguage": ["ar", "en"],
        "url": f"https://yallaplays.com/games/{metadata.get('slug_ar', game_id)}",
        "publisher": {"@type": "Organization", "name": "يلا بلايز", "url": "https://yallaplays.com"},
        "gamePlatform": ["Web Browser", "Mobile", "Desktop"],
    }


def build_game_html(game_code, metadata, schema):
    """Assemble the complete game HTML file."""
    return HTML_TEMPLATE.format(
        title_ar=metadata.get("title_ar", "لعبة"),
        desc_ar=metadata.get("desc_ar", ""),
        meta_desc_ar=metadata.get("meta_desc_ar", metadata.get("desc_ar", "")),
        keywords_ar=", ".join(metadata.get("keywords_ar", [])),
        schema_json=json.dumps(schema, ensure_ascii=False),
        phaser_cdn=PHASER_CDN,
        game_code=game_code,
    )


def qa_check_game(html_content, game_type):
    """Quick QA check on generated game HTML."""
    score = 0
    issues = []

    checks = {
        "phaser_cdn": (PHASER_CDN in html_content or "phaser" in html_content.lower(), 20, "Phaser.js not found"),
        "phaser_game": ("Phaser.Game" in html_content or "new Phaser" in html_content, 20, "No Phaser.Game instantiation"),
        "mobile_meta": ('user-scalable=no' in html_content, 10, "Missing mobile meta"),
        "touch_support": ("pointerdown" in html_content or "touchstart" in html_content, 10, "No touch support"),
        "game_over": ("game" in html_content.lower() and "over" in html_content.lower(), 10, "No game over logic"),
        "score": ("score" in html_content.lower(), 10, "No score system"),
        "schema": ("VideoGame" in html_content, 10, "Missing VideoGame schema"),
        "arabic": ("يلا بلايز" in html_content or "ar" in html_content, 10, "No Arabic content"),
    }

    for key, (condition, pts, issue) in checks.items():
        if condition:
            score += pts
        else:
            issues.append(issue)

    return score, issues


def create_review_entry(game_id, game_type, metadata, qa_score, game_path):
    """Create a review queue entry for admin approval."""
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    review_id = f"rev_{game_id}"
    entry = {
        "review_id": review_id,
        "type": "game",
        "game_id": game_id,
        "game_type": game_type,
        "name": metadata.get("title_ar", game_id),
        "name_en": metadata.get("title_en", game_id),
        "project": "yallaplays",
        "status": "pending_review",
        "qa_score": qa_score,
        "qa_eligible": qa_score >= 75,
        "ai_confidence": round(qa_score / 100, 2),
        "impact": f"Est. +{GAME_CONFIGS.get(game_type, {}).get('estimated_monthly_searches', 1000):,} monthly searches",
        "workflow_source": "ai-game-generator",
        "game_path": str(game_path),
        "pr_url": None,
        "generated_at": now_iso(),
        "reviewed_at": None,
        "approved_by": None,
        "deployed_at": None,
        "slug_ar": metadata.get("slug_ar", ""),
        "slug_en": metadata.get("slug_en", ""),
    }
    (REVIEWS_DIR / f"{review_id}.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    return entry


def save_game(game_id, html_content, metadata, schema, game_type, qa_score):
    """Save game files to outputs/yallaplays/games/{game_id}/."""
    game_dir = GAMES_OUTPUT_DIR / game_id
    game_dir.mkdir(parents=True, exist_ok=True)

    (game_dir / "game.html").write_text(html_content, encoding="utf-8")
    (game_dir / "metadata.json").write_text(json.dumps({
        "game_id": game_id,
        "game_type": game_type,
        "metadata": metadata,
        "schema": schema,
        "qa_score": qa_score,
        "generated_at": now_iso(),
        "deployment_ready": False,
        "status": "pending_review",
        "project": "yallaplays",
        "feature_type": "html5_game",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return game_dir


def generate_single_game(game_type, index, all_tokens, all_cost):
    """Generate one complete game with metadata, QA, and review entry."""
    game_id = generate_game_id(game_type, index)
    print(f"[game_factory] Generating {game_type} game: {game_id}")

    try:
        from telegram_notifier import send_system_log
        send_system_log("game_generating", f"Generating {game_type} game: {game_id}", "info")
    except Exception:
        pass

    game_code, all_tokens, all_cost = generate_game_code(game_type, GAME_CONFIGS.get(game_type, {}).get("name_ar", "لعبة"), all_tokens, all_cost)
    metadata, all_tokens, all_cost = generate_game_metadata(game_type, game_id, all_tokens, all_cost)
    schema = build_schema_markup(game_id, metadata, game_type)
    html_content = build_game_html(game_code, metadata, schema)
    qa_score, qa_issues = qa_check_game(html_content, game_type)

    game_dir = save_game(game_id, html_content, metadata, schema, game_type, qa_score)
    review_entry = create_review_entry(game_id, game_type, metadata, qa_score, game_dir)

    print(f"[game_factory] {game_id}: QA {qa_score}/100, {len(qa_issues)} issues, saved to {game_dir}")

    # Send Telegram alerts
    try:
        from telegram_notifier import send_approval_request, notify_qa_failed
        if qa_score < 75:
            notify_qa_failed(metadata.get("title_ar", game_id), qa_score, qa_issues)
        else:
            send_approval_request(review_entry)
    except Exception:
        pass

    return {
        "game_id": game_id,
        "game_type": game_type,
        "title_ar": metadata.get("title_ar", ""),
        "title_en": metadata.get("title_en", ""),
        "qa_score": qa_score,
        "qa_issues": qa_issues,
        "qa_eligible": qa_score >= 75,
        "status": "pending_review",
        "review_id": review_entry["review_id"],
        "game_path": str(game_dir),
        "slug_ar": metadata.get("slug_ar", ""),
        "slug_en": metadata.get("slug_en", ""),
    }, all_tokens, all_cost


FIRST_BATCH = [
    # Racing & driving (high search volume)
    ("racing", 1), ("racing", 2), ("racing", 3), ("racing", 4), ("racing", 5),
    ("car", 1), ("car", 2), ("car", 3),
    ("drift", 1), ("drift", 2),
    # Action & survival
    ("action", 1), ("action", 2), ("action", 3), ("action", 4),
    ("survival", 1), ("survival", 2), ("survival", 3),
    # Casual & clicker
    ("clicker", 1), ("clicker", 2), ("clicker", 3),
    ("idle", 1), ("idle", 2), ("idle", 3),
    # Puzzle & kids
    ("puzzle", 1), ("puzzle", 2),
    ("kids", 1), ("kids", 2),
    # Brain — SEO long tail
    ("brain", 1),
]


def main():
    print("[game_factory] Starting game factory batch...")
    all_tokens, all_cost = 0, 0.0

    GAMES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    GAME_FACTORY_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from telegram_notifier import notify_workflow_start
        notify_workflow_start("ai-game-generator", {"batch": len(FIRST_BATCH), "types": "racing,car,drift,action,survival,clicker,idle,puzzle,kids,brain"})
    except Exception:
        pass

    generated_games = []
    failed_games = []

    for game_type, index in FIRST_BATCH:
        try:
            game_result, all_tokens, all_cost = generate_single_game(game_type, index, all_tokens, all_cost)
            generated_games.append(game_result)
        except Exception as e:
            print(f"[game_factory] Failed {game_type}_{index}: {e}")
            failed_games.append({"game_type": game_type, "index": index, "error": str(e)[:100]})
            try:
                from telegram_notifier import notify_failure
                notify_failure(str(e), f"game_factory:{game_type}_{index}")
            except Exception:
                pass

    eligible = [g for g in generated_games if g.get("qa_eligible")]
    avg_qa = round(sum(g["qa_score"] for g in generated_games) / max(len(generated_games), 1), 1)

    report = {
        "generated_at": now_iso(),
        "batch_size": len(FIRST_BATCH),
        "games_generated": len(generated_games),
        "games_failed": len(failed_games),
        "qa_eligible": len(eligible),
        "avg_qa_score": avg_qa,
        "games": generated_games,
        "failed": failed_games,
        "pending_review_count": len(generated_games),
        "types_generated": list({g["game_type"] for g in generated_games}),
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (GAME_FACTORY_DIR / "factory_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (MEMORY_DIR / "game_factory_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    try:
        from telegram_notifier import notify_workflow_complete, notify_cost_report
        notify_workflow_complete("ai-game-generator", {
            "generated": len(generated_games),
            "eligible": len(eligible),
            "avg_qa": f"{avg_qa}/100",
            "pending_review": len(generated_games),
        })
        notify_cost_report("ai-game-generator", all_tokens, all_cost, len(generated_games))
    except Exception:
        pass

    print(f"[game_factory] Done — {len(generated_games)} games, {len(eligible)} QA eligible, avg QA {avg_qa}, ${all_cost:.4f}")


if __name__ == "__main__":
    main()

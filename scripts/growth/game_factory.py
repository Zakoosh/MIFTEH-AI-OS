"""
AI Game Factory
Generates HTML5 games, SVG thumbnails, metadata, categories, and
monetization-ready page layouts for YallaPlays.
"""
import hashlib
import json
import math
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.intelligence.registry import get_project
from scripts.intelligence.report_store import save, REPORTS_ROOT

REPORT_TYPE = "games"

# ──────────────────────────────────────────────────────────────────────────────
# Game templates (self-contained canvas-based HTML5 games)
# ──────────────────────────────────────────────────────────────────────────────

GAME_TEMPLATES = {

    "number_merge": {
        "name_ar": "دمج الأرقام",
        "name_en": "Number Merge",
        "category": "puzzle",
        "description_ar": "ادمج المربعات لتصل إلى 2048",
        "description_en": "Merge tiles to reach 2048",
        "difficulty": "medium",
        "play_time_min": 5,
    },

    "color_match": {
        "name_ar": "مطابقة الألوان",
        "name_en": "Color Match",
        "category": "casual",
        "description_ar": "طابق الألوان قبل نفاد الوقت",
        "description_en": "Match colors before time runs out",
        "difficulty": "easy",
        "play_time_min": 2,
    },

    "word_finder": {
        "name_ar": "البحث عن الكلمات",
        "name_en": "Word Finder",
        "category": "puzzle",
        "description_ar": "ابحث عن الكلمات المخفية",
        "description_en": "Find hidden words in the grid",
        "difficulty": "medium",
        "play_time_min": 5,
    },

    "balloon_pop": {
        "name_ar": "فقاعات المرح",
        "name_en": "Balloon Pop",
        "category": "casual",
        "description_ar": "افقع البالونات قبل أن تختفي",
        "description_en": "Pop balloons before they disappear",
        "difficulty": "easy",
        "play_time_min": 2,
    },

    "math_sprint": {
        "name_ar": "سباق الرياضيات",
        "name_en": "Math Sprint",
        "category": "math",
        "description_ar": "أجب على مسائل الرياضيات بسرعة",
        "description_en": "Answer math questions as fast as you can",
        "difficulty": "medium",
        "play_time_min": 3,
    },

    "star_catcher": {
        "name_ar": "صائد النجوم",
        "name_en": "Star Catcher",
        "category": "arcade",
        "description_ar": "اجمع النجوم وتجنب العقبات",
        "description_en": "Collect stars and avoid obstacles",
        "difficulty": "easy",
        "play_time_min": 3,
    },
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ──────────────────────────────────────────────────────────────────────────────
# SVG Thumbnail generator (no external deps)
# ──────────────────────────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    "puzzle":   ("#6366f1", "#818cf8"),
    "casual":   ("#10b981", "#34d399"),
    "arcade":   ("#f59e0b", "#fbbf24"),
    "math":     ("#3b82f6", "#60a5fa"),
    "action":   ("#ef4444", "#f87171"),
    "kids":     ("#ec4899", "#f472b6"),
    "sports":   ("#14b8a6", "#2dd4bf"),
    "strategy": ("#8b5cf6", "#a78bfa"),
    "racing":   ("#f97316", "#fb923c"),
    "adventure":("#84cc16", "#a3e635"),
}

CATEGORY_ICONS = {
    "puzzle":   "🧩", "casual":   "🎯", "arcade":   "🕹️",
    "math":     "➕", "action":   "⚡", "kids":     "🎨",
    "sports":   "⚽", "strategy": "♟️", "racing":   "🏎️", "adventure":"🗺️",
}


def generate_thumbnail_svg(game_id: str, template: dict) -> str:
    """Generate a styled SVG thumbnail for a game."""
    category = template.get("category", "arcade")
    name_en = template.get("name_en", game_id)
    name_ar = template.get("name_ar", name_en)
    icon = CATEGORY_ICONS.get(category, "🎮")
    c1, c2 = CATEGORY_COLORS.get(category, ("#6366f1", "#818cf8"))
    difficulty = template.get("difficulty", "easy")
    diff_color = {"easy": "#10b981", "medium": "#f59e0b", "hard": "#ef4444"}.get(difficulty, "#10b981")

    seed = int(hashlib.md5(game_id.encode()).hexdigest()[:6], 16)
    stars = [(
        100 + (seed * 37 * (i + 1)) % 200,
        50  + (seed * 53 * (i + 1)) % 100,
        1 + (seed * (i + 1)) % 3
    ) for i in range(8)]
    star_circles = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" opacity="0.3"/>'
        for x, y, r in stars
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="320" height="180">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{c1}"/>
      <stop offset="100%" style="stop-color:{c2}"/>
    </linearGradient>
    <linearGradient id="card" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:rgba(255,255,255,0.15)"/>
      <stop offset="100%" style="stop-color:rgba(255,255,255,0.05)"/>
    </linearGradient>
  </defs>
  <rect width="320" height="180" fill="url(#bg)" rx="12"/>
  {star_circles}
  <rect x="40" y="30" width="240" height="120" rx="10" fill="url(#card)" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
  <text x="160" y="85" text-anchor="middle" font-size="42" font-family="Arial">{icon}</text>
  <text x="160" y="112" text-anchor="middle" font-size="14" font-weight="bold" fill="white" font-family="Arial, sans-serif">{name_en}</text>
  <text x="160" y="130" text-anchor="middle" font-size="11" fill="rgba(255,255,255,0.75)" font-family="Arial, sans-serif">{name_ar}</text>
  <rect x="120" y="140" width="80" height="18" rx="9" fill="{diff_color}" opacity="0.85"/>
  <text x="160" y="152" text-anchor="middle" font-size="10" fill="white" font-family="Arial, sans-serif">{difficulty.title()}</text>
</svg>'''


# ──────────────────────────────────────────────────────────────────────────────
# HTML5 game scaffolding
# ──────────────────────────────────────────────────────────────────────────────

def generate_game_html(game_id: str, template: dict, publisher_id: str = "ca-pub-1206965892808259") -> str:
    """Generate a complete, monetization-ready HTML5 game page."""
    name_en = template.get("name_en", game_id)
    name_ar = template.get("name_ar", name_en)
    category = template.get("category", "arcade")
    desc_ar = template.get("description_ar", "")
    desc_en = template.get("description_en", "")
    slug = _slug(name_en)

    # Minimal canvas game logic for the specific type
    game_logic = _get_game_logic(game_id, template)

    return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name_ar} - يلا بلاي | {name_en} - YallaPlays</title>
  <meta name="description" content="العب {name_ar} مجاناً. {desc_ar} Play {name_en} free online.">
  <meta name="keywords" content="{name_ar}, {name_en}, {category} games, يلا بلاي, yallaplays">
  <link rel="canonical" href="https://yallaplays.com/games/{slug}">
  <meta property="og:title" content="{name_ar} | يلا بلاي">
  <meta property="og:description" content="{desc_ar}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://yallaplays.com/games/{slug}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "VideoGame",
    "name": "{name_en}",
    "description": "{desc_en}",
    "url": "https://yallaplays.com/games/{slug}",
    "genre": "{category}",
    "gamePlatform": "Web Browser",
    "offers": {{"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
  }}
  </script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={publisher_id}" crossorigin="anonymous"></script>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#0a0a14;color:white;font-family:Arial,sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center}}
    header{{width:100%;max-width:800px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}}
    .logo{{font-size:18px;font-weight:bold;color:#818cf8;text-decoration:none}}
    h1{{font-size:20px;margin:8px 0 4px;text-align:center}}
    .desc{{font-size:13px;color:#94a3b8;text-align:center;margin-bottom:12px}}
    .ad-banner{{width:100%;max-width:728px;min-height:90px;background:rgba(255,255,255,0.05);border-radius:8px;margin:8px auto;display:flex;align-items:center;justify-content:center;overflow:hidden}}
    #gameCanvas{{border-radius:12px;display:block;max-width:100%;background:#111827;cursor:pointer}}
    .controls{{margin:8px 0;font-size:12px;color:#64748b;text-align:center}}
    .score-bar{{display:flex;gap:24px;justify-content:center;margin:8px 0;font-size:14px}}
    .score-bar span{{background:rgba(255,255,255,0.1);padding:4px 16px;border-radius:8px}}
    .btn{{background:#6366f1;color:white;border:none;padding:10px 32px;border-radius:20px;cursor:pointer;font-size:15px;margin:8px;transition:0.2s}}
    .btn:hover{{background:#4f46e5}}
    .ad-side{{width:160px;min-height:600px;background:rgba(255,255,255,0.05);border-radius:8px;display:none}}
    @media(min-width:1024px){{.ad-side{{display:block}}}}
    .game-wrap{{display:flex;gap:16px;align-items:flex-start;justify-content:center;width:100%;padding:0 16px}}
    footer{{margin-top:auto;padding:16px;text-align:center;font-size:12px;color:#475569;width:100%}}
    footer a{{color:#818cf8;text-decoration:none;margin:0 8px}}
  </style>
</head>
<body>
  <header>
    <a href="/" class="logo">يلا بلاي | YallaPlays</a>
    <a href="/games" style="color:#94a3b8;font-size:13px">← كل الألعاب</a>
  </header>

  <!-- Top Ad -->
  <div class="ad-banner">
    <ins class="adsbygoogle" style="display:block;width:728px;height:90px"
      data-ad-client="{publisher_id}" data-ad-slot="top_banner" data-ad-format="horizontal"></ins>
  </div>

  <h1>{name_ar} — {name_en}</h1>
  <p class="desc">{desc_ar}</p>

  <div class="score-bar">
    <span>النقاط: <b id="score">0</b></span>
    <span>المستوى: <b id="level">1</b></span>
    <span>أفضل: <b id="best">0</b></span>
  </div>

  <div class="game-wrap">
    <!-- Side Ad (desktop) -->
    <div class="ad-side">
      <ins class="adsbygoogle" style="display:block;width:160px;height:600px"
        data-ad-client="{publisher_id}" data-ad-slot="side_left" data-ad-format="vertical"></ins>
    </div>

    <div style="text-align:center">
      <canvas id="gameCanvas" width="480" height="480"></canvas>
      <div class="controls" id="controlsHint">انقر/المس للعب • Click/Tap to play</div>
      <div style="margin-top:8px">
        <button class="btn" onclick="restartGame()">إعادة ▶ Restart</button>
      </div>
    </div>

    <!-- Side Ad right (desktop) -->
    <div class="ad-side">
      <ins class="adsbygoogle" style="display:block;width:160px;height:600px"
        data-ad-client="{publisher_id}" data-ad-slot="side_right" data-ad-format="vertical"></ins>
    </div>
  </div>

  <!-- Bottom Ad -->
  <div class="ad-banner" style="margin-top:16px">
    <ins class="adsbygoogle" style="display:block;width:728px;height:90px"
      data-ad-client="{publisher_id}" data-ad-slot="bottom_banner" data-ad-format="horizontal"></ins>
  </div>

  <footer>
    <a href="/">الرئيسية</a><a href="/games">الألعاب</a>
    <a href="/about">من نحن</a><a href="/privacy">الخصوصية</a>
    <a href="/contact">تواصل</a>
    <p style="margin-top:8px">© 2026 يلا بلاي | YallaPlays — AI Powered by MIFTEH AI OS</p>
  </footer>

  <script>
  (function(){{
    // Push all AdSense units
    try{{
      var ads = document.querySelectorAll('.adsbygoogle');
      ads.forEach(function(){{ (adsbygoogle = window.adsbygoogle || []).push({{}}); }});
    }} catch(e) {{}}
  }})();

  {game_logic}
  </script>
</body>
</html>'''


def _get_game_logic(game_id: str, template: dict) -> str:
    """Return appropriate JavaScript game logic for the game type."""
    category = template.get("category", "arcade")

    if game_id == "star_catcher" or category == "arcade":
        return _star_catcher_logic()
    elif game_id == "balloon_pop" or game_id == "color_match":
        return _balloon_pop_logic()
    elif game_id == "math_sprint" or category == "math":
        return _math_sprint_logic()
    else:
        return _generic_puzzle_logic()


def _star_catcher_logic() -> str:
    return '''
const canvas=document.getElementById('gameCanvas'),ctx=canvas.getContext('2d');
let score=0,level=1,best=parseInt(localStorage.getItem('sc_best')||0),running=false;
let player={x:240,y:420,r:20,speed:5},stars=[],bombs=[],frame=0;
function rnd(a,b){return Math.random()*(b-a)+a}
function spawnStar(){stars.push({x:rnd(30,450),y:-20,r:12,speed:rnd(1.5,2.5+level*0.3),color:`hsl(${rnd(40,60)},100%,60%)`})}
function spawnBomb(){if(level>1)bombs.push({x:rnd(30,450),y:-20,r:14,speed:rnd(2,3+level*0.4)})}
function drawCircle(o,color){ctx.beginPath();ctx.arc(o.x,o.y,o.r,0,Math.PI*2);ctx.fillStyle=color;ctx.fill()}
function collide(a,b){return Math.hypot(a.x-b.x,a.y-b.y)<a.r+b.r-4}
function update(){
  if(!running)return;
  frame++;
  if(frame%60===0)spawnStar();
  if(frame%120===0)spawnBomb();
  stars=stars.filter(s=>{s.y+=s.speed;if(collide(s,player)){score+=10;document.getElementById('score').textContent=score;if(score>best){best=score;localStorage.setItem('sc_best',best);document.getElementById('best').textContent=best;}return false;}return s.y<500;});
  bombs=bombs.filter(b=>{b.y+=b.speed;if(collide(b,player)){endGame();return false;}return b.y<500;});
  level=1+Math.floor(score/100);
  document.getElementById('level').textContent=level;
}
function draw(){
  ctx.clearRect(0,0,480,480);
  ctx.fillStyle='#0f172a';ctx.fillRect(0,0,480,480);
  stars.forEach(s=>drawCircle(s,s.color));
  bombs.forEach(b=>{ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle='#ef4444';ctx.fill();ctx.fillStyle='white';ctx.font='16px Arial';ctx.textAlign='center';ctx.fillText('💣',b.x,b.y+5);});
  ctx.beginPath();ctx.arc(player.x,player.y,player.r,0,Math.PI*2);ctx.fillStyle='#818cf8';ctx.fill();
  ctx.fillStyle='white';ctx.font='18px Arial';ctx.textAlign='center';ctx.fillText('🚀',player.x,player.y+6);
  if(!running){ctx.fillStyle='rgba(0,0,0,0.6)';ctx.fillRect(0,0,480,480);ctx.fillStyle='white';ctx.font='bold 28px Arial';ctx.textAlign='center';ctx.fillText(score>0?'انتهت اللعبة!':'ابدأ اللعب!',240,220);ctx.font='18px Arial';ctx.fillStyle='#818cf8';ctx.fillText('انقر للبدأ • Click to Start',240,260);}
}
function loop(){update();draw();requestAnimationFrame(loop);}
function endGame(){running=false;}
function restartGame(){score=0;level=1;stars=[];bombs=[];frame=0;document.getElementById('score').textContent=0;document.getElementById('level').textContent=1;running=true;}
canvas.addEventListener('mousemove',e=>{let r=canvas.getBoundingClientRect();player.x=e.clientX-r.left;});
canvas.addEventListener('touchmove',e=>{e.preventDefault();let r=canvas.getBoundingClientRect();player.x=e.touches[0].clientX-r.left;},{passive:false});
canvas.addEventListener('click',()=>{if(!running)restartGame();});
loop();'''


def _balloon_pop_logic() -> str:
    return '''
const canvas=document.getElementById('gameCanvas'),ctx=canvas.getContext('2d');
let score=0,best=parseInt(localStorage.getItem('bp_best')||0),running=false,balloons=[],frame=0;
function rnd(a,b){return Math.random()*(b-a)+a}
function spawnBalloon(){balloons.push({x:rnd(40,440),y:490,r:rnd(20,35),speed:rnd(1,2.5),color:`hsl(${rnd(0,360)},80%,60%)`,pop:false,popFrame:0});}
function draw(){
  ctx.clearRect(0,0,480,480);ctx.fillStyle='#0f172a';ctx.fillRect(0,0,480,480);
  balloons.forEach(b=>{
    if(b.pop){ctx.font='28px Arial';ctx.textAlign='center';ctx.fillText('💥',b.x,b.y);return;}
    ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle=b.color;ctx.fill();
    ctx.beginPath();ctx.moveTo(b.x,b.y+b.r);ctx.lineTo(b.x+5,b.y+b.r+15);ctx.strokeStyle=b.color;ctx.lineWidth=2;ctx.stroke();
  });
  if(!running){ctx.fillStyle='rgba(0,0,0,0.6)';ctx.fillRect(0,0,480,480);ctx.fillStyle='white';ctx.font='bold 26px Arial';ctx.textAlign='center';ctx.fillText(score>0?'انتهت اللعبة! '+score+' نقطة':'افقع البالونات!',240,220);ctx.font='16px Arial';ctx.fillStyle='#818cf8';ctx.fillText('انقر للبدأ',240,258);}
}
function update(){
  if(!running)return;frame++;
  if(frame%50===0)spawnBalloon();
  balloons=balloons.filter(b=>{
    if(b.pop){b.popFrame++;return b.popFrame<15;}
    b.y-=b.speed;
    if(b.y+b.r<0){running=false;return false;}
    return true;
  });
}
function popAt(x,y){
  balloons.forEach(b=>{if(!b.pop&&Math.hypot(x-b.x,y-b.y)<b.r+5){b.pop=true;score+=10;document.getElementById('score').textContent=score;if(score>best){best=score;localStorage.setItem('bp_best',best);document.getElementById('best').textContent=best;}}});
}
canvas.addEventListener('click',e=>{if(!running){score=0;balloons=[];frame=0;document.getElementById('score').textContent=0;running=true;return;}let r=canvas.getBoundingClientRect();popAt(e.clientX-r.left,e.clientY-r.top);});
canvas.addEventListener('touchstart',e=>{e.preventDefault();let r=canvas.getBoundingClientRect(),t=e.touches[0];if(!running){score=0;balloons=[];frame=0;running=true;return;}popAt(t.clientX-r.left,t.clientY-r.top);},{passive:false});
function restartGame(){score=0;balloons=[];frame=0;document.getElementById('score').textContent=0;running=true;}
function loop(){update();draw();requestAnimationFrame(loop);}
loop();'''


def _math_sprint_logic() -> str:
    return '''
const canvas=document.getElementById('gameCanvas'),ctx=canvas.getContext('2d');
let score=0,best=parseInt(localStorage.getItem('ms_best')||0),running=false,timer=30,q={},frame=0,input='',feedback='';
function newQ(){
  const ops=['+','-','×'];const op=ops[Math.floor(Math.random()*ops.length)];
  let a=Math.floor(Math.random()*12)+1,b=Math.floor(Math.random()*12)+1;
  if(op==='-'&&a<b)[a,b]=[b,a];
  const ans=op==='+'?a+b:op==='-'?a-b:a*b;
  q={a,b,op,ans};input='';
}
function draw(){
  ctx.clearRect(0,0,480,480);ctx.fillStyle='#0f172a';ctx.fillRect(0,0,480,480);
  if(!running){ctx.fillStyle='white';ctx.font='bold 26px Arial';ctx.textAlign='center';ctx.fillText(score>0?`انتهى! ${score} نقطة`:'سباق الرياضيات',240,200);ctx.font='16px Arial';ctx.fillStyle='#818cf8';ctx.fillText('انقر للبدأ',240,240);return;}
  // Timer bar
  ctx.fillStyle='#1e293b';ctx.fillRect(40,20,400,16);
  ctx.fillStyle=timer>10?'#10b981':'#ef4444';ctx.fillRect(40,20,400*(timer/30),16);
  ctx.fillStyle='white';ctx.font='14px Arial';ctx.textAlign='center';ctx.fillText(`${timer}s`,240,33);
  // Question
  ctx.font='bold 52px Arial';ctx.textAlign='center';ctx.fillStyle='white';
  ctx.fillText(`${q.a} ${q.op} ${q.b} = ?`,240,200);
  // Input box
  ctx.fillStyle='rgba(255,255,255,0.1)';ctx.beginPath();ctx.roundRect(160,230,160,50,10);ctx.fill();
  ctx.fillStyle='white';ctx.font='bold 28px Arial';ctx.fillText(input||'_',240,264);
  // Feedback
  if(feedback){ctx.font='bold 22px Arial';ctx.fillStyle=feedback==='✓'?'#10b981':'#ef4444';ctx.fillText(feedback,240,310);}
}
function update(){if(!running||frame%60!==0)return;timer--;document.getElementById('score').textContent=score;if(timer<=0){running=false;if(score>best){best=score;localStorage.setItem('ms_best',best);document.getElementById('best').textContent=best;}}}
function keyPress(k){
  if(!running)return;
  if(k>='0'&&k<='9'&&input.length<4)input+=k;
  else if(k==='Backspace')input=input.slice(0,-1);
  else if(k==='Enter'||k==='-'){
    const ans=parseInt(input);
    if(ans===q.ans){score+=10;feedback='✓';newQ();}
    else{score=Math.max(0,score-5);feedback='✗';input='';}
    document.getElementById('score').textContent=score;
    setTimeout(()=>feedback='',600);
  }
}
document.addEventListener('keydown',e=>keyPress(e.key));
canvas.addEventListener('click',()=>{if(!running){score=0;timer=30;frame=0;running=true;newQ();}});
function restartGame(){score=0;timer=30;frame=0;running=true;newQ();}
function loop(){frame++;update();draw();requestAnimationFrame(loop);}
loop();'''


def _generic_puzzle_logic() -> str:
    return _star_catcher_logic()


# ──────────────────────────────────────────────────────────────────────────────
# Metadata generator
# ──────────────────────────────────────────────────────────────────────────────

def generate_metadata(game_id: str, template: dict, domain: str) -> dict:
    slug = _slug(template.get("name_en", game_id))
    return {
        "id": game_id,
        "slug": slug,
        "name_ar": template["name_ar"],
        "name_en": template["name_en"],
        "category": template["category"],
        "description_ar": template["description_ar"],
        "description_en": template["description_en"],
        "difficulty": template.get("difficulty", "easy"),
        "play_time_min": template.get("play_time_min", 3),
        "tags": [template["category"], "html5", "free", "online", "yallaplays"],
        "url": f"https://{domain}/games/{slug}",
        "thumbnail": f"https://{domain}/thumbnails/{slug}.svg",
        "schema_type": "VideoGame",
        "mobile_ready": True,
        "monetization_ready": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Factory: generate a batch of games
# ──────────────────────────────────────────────────────────────────────────────

def generate_game(game_id: str, project_id: str, publisher_id: str = "ca-pub-1206965892808259") -> dict:
    """Generate a complete game: HTML + SVG thumbnail + metadata."""
    template = GAME_TEMPLATES.get(game_id)
    if not template:
        raise ValueError(f"Unknown game template: {game_id}")

    p = get_project(project_id)
    domain = p["domain"]

    html = generate_game_html(game_id, template, publisher_id)
    thumbnail_svg = generate_thumbnail_svg(game_id, template)
    metadata = generate_metadata(game_id, template, domain)
    slug = metadata["slug"]

    # Save outputs
    out_dir = REPORTS_ROOT / "games" / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{slug}.html").write_text(html)
    (out_dir / f"{slug}.svg").write_text(thumbnail_svg)

    result = {
        "game_id": game_id,
        "slug": slug,
        "metadata": metadata,
        "html_path": str(out_dir / f"{slug}.html"),
        "thumbnail_path": str(out_dir / f"{slug}.svg"),
        "html_size": len(html),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def generate_batch(project_id: str, game_ids: Optional[list] = None, publisher_id: str = "ca-pub-1206965892808259") -> dict:
    """Generate multiple games and save a batch report."""
    ids = game_ids or list(GAME_TEMPLATES.keys())
    results = []
    errors = []

    for gid in ids:
        try:
            results.append(generate_game(gid, project_id, publisher_id))
        except Exception as e:
            errors.append({"game_id": gid, "error": str(e)})

    report = {
        "project_id": project_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested": len(ids),
        "generated": len(results),
        "errors": len(errors),
        "games": [r["metadata"] for r in results],
        "error_details": errors,
        "total_html_bytes": sum(r.get("html_size", 0) for r in results),
    }
    save(REPORT_TYPE, project_id, report)
    return report


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    r = generate_batch(pid)
    print(json.dumps({k: v for k, v in r.items() if k != "games"}, indent=2))
    print(f"\nGenerated {r['generated']} games in memory/reports/games/{pid}/")

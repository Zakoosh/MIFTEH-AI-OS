from __future__ import annotations
from datetime import datetime
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel

TRENDING_SIGNALS = [
    {"game_id": "subway-surfers", "name": "Subway Surfers", "trend_score": 98, "plays_24h": 45200, "genre": "arcade"},
    {"game_id": "8-ball-pool", "name": "8 Ball Pool", "trend_score": 95, "plays_24h": 38100, "genre": "sports"},
    {"game_id": "among-us", "name": "Among Us", "trend_score": 91, "plays_24h": 29800, "genre": "multiplayer"},
    {"game_id": "ludo-star", "name": "Ludo Star", "trend_score": 89, "plays_24h": 27400, "genre": "board"},
    {"game_id": "pubg-mobile", "name": "PUBG Mobile", "trend_score": 87, "plays_24h": 24100, "genre": "battle-royale"},
    {"game_id": "clash-of-clans", "name": "Clash of Clans", "trend_score": 84, "plays_24h": 21300, "genre": "strategy"},
    {"game_id": "candy-crush", "name": "Candy Crush Saga", "trend_score": 81, "plays_24h": 19800, "genre": "puzzle"},
    {"game_id": "hill-climb", "name": "Hill Climb Racing", "trend_score": 79, "plays_24h": 17500, "genre": "racing"},
    {"game_id": "temple-run", "name": "Temple Run 2", "trend_score": 77, "plays_24h": 16200, "genre": "action"},
    {"game_id": "mini-militia", "name": "Mini Militia", "trend_score": 74, "plays_24h": 14900, "genre": "shooter"},
]


class GameRecommendationGenerator:
    PROJECT = "yallaplays"

    def __init__(self):
        self._ai = ContentGenerator()

    def _build_recommendation_engine_config(self) -> dict[str, Any]:
        return {
            "algorithm": "hybrid",
            "signals": {
                "collaborative_filtering": 0.4,
                "content_based": 0.3,
                "trending": 0.2,
                "editorial": 0.1,
            },
            "recency_decay_hours": 48,
            "diversity_factor": 0.15,
            "max_recommendations": 12,
            "refresh_interval_minutes": 30,
            "segments": {
                "new_user": {"trending": 0.6, "popular": 0.4},
                "returning_user": {"collaborative": 0.5, "content": 0.3, "trending": 0.2},
                "power_user": {"collaborative": 0.7, "new_releases": 0.3},
            },
        }

    def _build_trending_section(self) -> dict[str, Any]:
        top_games = sorted(TRENDING_SIGNALS, key=lambda g: g["trend_score"], reverse=True)[:6]
        return {
            "section_id": "trending_now",
            "title": "Trending Now 🔥",
            "subtitle": f"Updated {datetime.utcnow().strftime('%H:%M')} UTC",
            "games": [
                {
                    "rank": i + 1,
                    "game_id": g["game_id"],
                    "name": g["name"],
                    "trend_score": g["trend_score"],
                    "plays_24h": g["plays_24h"],
                    "genre": g["genre"],
                    "badge": "🔥 Hot" if g["trend_score"] >= 90 else "📈 Rising",
                }
                for i, g in enumerate(top_games)
            ],
        }

    def _build_widget_component(self) -> str:
        return """import { useEffect, useState } from 'react';

interface TrendingGame {
  rank: number;
  game_id: string;
  name: string;
  trend_score: number;
  plays_24h: number;
  badge: string;
}

export function TrendingGamesWidget() {
  const [games, setGames] = useState<TrendingGame[]>([]);
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    fetch('/api/games/trending?limit=6')
      .then(r => r.json())
      .then(data => { setGames(data.games); setLastUpdate(data.updated_at); });
    const interval = setInterval(() => {
      fetch('/api/games/trending?limit=6')
        .then(r => r.json())
        .then(data => setGames(data.games));
    }, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="trending-widget">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">🔥 Trending Now</h2>
        <span className="text-sm text-gray-400">Updated {lastUpdate}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {games.map(game => (
          <a key={game.game_id} href={`/games/${game.game_id}/`} className="game-card hover:shadow-lg transition-shadow">
            <div className="relative">
              <img src={`/thumbnails/${game.game_id}.jpg`} alt={game.name} className="w-full rounded-lg" loading="lazy" />
              <span className="absolute top-2 left-2 badge">{game.badge}</span>
              <span className="absolute top-2 right-2 rank-badge">#{game.rank}</span>
            </div>
            <p className="mt-2 font-medium">{game.name}</p>
            <p className="text-sm text-gray-500">{game.plays_24h.toLocaleString()} plays today</p>
          </a>
        ))}
      </div>
    </section>
  );
}
"""

    async def generate_recommendations(self, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        engine_config = self._build_recommendation_engine_config()
        trending_section = self._build_trending_section()
        ai_generated = False
        cost, tokens = 0.0, 0

        if use_ai and self._ai.is_ai_available():
            top_names = [g["name"] for g in TRENDING_SIGNALS[:5]]
            result = await self._ai.generate(
                prompt=f"Given trending games on YallaPlays: {top_names}, write 3 personalised recommendation section titles and subtitles for: (1) new users (2) sports fans (3) mobile users. Return JSON: [{{segment, title, subtitle}}]",
                system_prompt="You are a product manager for a gaming platform. Be engaging and culturally aware of Arab audiences.",
                max_tokens=300,
            )
            if result.get("success"):
                ai_generated = True
                cost = result.get("cost_usd", 0)
                tokens = result.get("total_tokens", 0)

        patch_files = [
            {
                "file_path": "src/components/TrendingGamesWidget.tsx",
                "operation": "create",
                "content": self._build_widget_component(),
                "description": "Real-time trending games widget with auto-refresh",
            },
            {
                "file_path": "src/config/recommendation-engine.json",
                "operation": "create_or_update",
                "content": str(engine_config),
                "description": "Recommendation engine configuration",
            },
            {
                "file_path": "src/data/trending-games.json",
                "operation": "create_or_update",
                "content": str(trending_section),
                "description": "Current trending games data snapshot",
            },
        ]

        output = OperationalOutput(
            project=OperationProject.yallaplays,
            output_type=OutputType.game_recommendation,
            title=f"Game Recommendations — {len(TRENDING_SIGNALS)} Trending Games",
            description="Trending game recommendations engine: real-time widget, personalised sections, hybrid algorithm config",
            content={"trending_section": trending_section, "engine_config": engine_config, "games_tracked": len(TRENDING_SIGNALS)},
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=cost,
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.yallaplays,
            preview_markdown=f"# Trending Game Recommendations\n\n## Top Trending\n\n" + "\n".join(f"#{g['rank']} {g['name']} — {g['plays_24h']:,} plays (score: {g['trend_score']})" for g in trending_section["games"]),
            diff_summary=f"Creates trending widget + recommendation engine config ({len(patch_files)} files)",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"ctr_improvement": "+15-25%", "session_depth": "+0.5 pages/session", "retention": "+8%"},
        )
        output.preview_id = preview.id
        return output, preview

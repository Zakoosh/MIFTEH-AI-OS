from __future__ import annotations
from datetime import datetime
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel
from ...providers.market_data_provider import TwelveDataProvider, POPULAR_SYMBOLS

MARKET_SECTORS = ["Technology", "Energy", "Financials", "Healthcare", "Consumer Discretionary", "Industrials", "Real Estate", "Utilities"]
MENA_INDICES = ["Tadawul (TASI)", "Dubai Financial Market (DFM)", "Abu Dhabi Securities Exchange (ADX)", "Egypt EGX30", "Kuwait Stock Exchange (KSE)"]
TEMPLATE_INSIGHTS = [
    {
        "id": "weekly_outlook",
        "title": "Weekly Market Outlook",
        "type": "analysis",
        "template": "Markets this week are influenced by {macro_factor}. Key levels to watch on {index}: support at {support}, resistance at {resistance}. Sentiment is {sentiment} with volume {volume_trend}.",
        "tags": ["macro", "technical", "weekly"],
    },
    {
        "id": "sector_rotation",
        "title": "Sector Rotation Analysis",
        "type": "strategy",
        "template": "Capital is rotating from {outflow_sector} into {inflow_sector}. This typically signals {implication}. Monitor {watchlist_tickers} for entry opportunities.",
        "tags": ["sectors", "rotation", "strategy"],
    },
    {
        "id": "earnings_preview",
        "title": "Earnings Season Preview",
        "type": "event",
        "template": "This week's key earnings: {company_list}. Consensus expects {eps_direction} EPS vs last quarter. Watch for guidance on {key_metric}.",
        "tags": ["earnings", "fundamental", "event"],
    },
    {
        "id": "technical_setup",
        "title": "Technical Setup of the Week",
        "type": "technical",
        "template": "{ticker} is forming a {pattern} pattern on the {timeframe} chart. Target: {target}, Stop: {stop}. Confluence with {indicator} at {level}.",
        "tags": ["technical", "chart", "setup"],
    },
]


class MarketInsightGenerator:
    PROJECT = "fionera"

    def __init__(self):
        self._ai = ContentGenerator()
        self._market = TwelveDataProvider()

    def _build_insight_template(self, insight_config: dict) -> dict[str, Any]:
        placeholders = {
            "macro_factor": "Federal Reserve rate expectations",
            "index": "Tadawul (TASI)",
            "support": "11,200",
            "resistance": "11,850",
            "sentiment": "cautiously bullish",
            "volume_trend": "above 30-day average",
            "outflow_sector": "Technology",
            "inflow_sector": "Energy",
            "implication": "a risk-off rotation into defensive names",
            "watchlist_tickers": "ARAMCO, SABIC, STC",
            "company_list": "Saudi Aramco, stc, Al Rajhi Bank",
            "eps_direction": "flat to slightly higher",
            "key_metric": "forward guidance and dividend policy",
            "ticker": "2222.SR (Aramco)",
            "pattern": "ascending triangle",
            "timeframe": "daily",
            "target": "SAR 32.50",
            "stop": "SAR 29.80",
            "indicator": "200-day EMA",
            "level": "SAR 30.20",
        }
        content = insight_config["template"]
        for k, v in placeholders.items():
            content = content.replace(f"{{{k}}}", v)
        return {
            "insight_id": insight_config["id"],
            "title": insight_config["title"],
            "type": insight_config["type"],
            "content": content,
            "tags": insight_config["tags"],
            "generated_at": datetime.utcnow().isoformat(),
            "is_ai_enhanced": False,
            "disclaimer": "This is for informational purposes only and does not constitute financial advice.",
            "market_context": {
                "indices_covered": MENA_INDICES[:3],
                "sectors_covered": MARKET_SECTORS[:4],
                "time_horizon": "1 week",
            },
        }

    def _render_insight_card_component(self) -> str:
        return """import { Badge } from '@/components/ui/badge';
import { BookOpen, TrendingUp, AlertCircle } from 'lucide-react';

const typeIcons = { analysis: BookOpen, strategy: TrendingUp, event: AlertCircle, technical: TrendingUp };
const typeColors = { analysis: 'bg-blue-50 text-blue-700', strategy: 'bg-purple-50 text-purple-700', event: 'bg-orange-50 text-orange-700', technical: 'bg-green-50 text-green-700' };

export function InsightCard({ insight }: { insight: MarketInsight }) {
  const Icon = typeIcons[insight.type] || BookOpen;
  return (
    <article className="insight-card rounded-xl p-5 bg-white border shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2 rounded-lg ${typeColors[insight.type] || ''}`}><Icon size={16} /></div>
        <span className="text-xs text-gray-400">{new Date(insight.generated_at).toLocaleDateString()}</span>
      </div>
      <h3 className="font-semibold text-lg mb-2">{insight.title}</h3>
      <p className="text-gray-600 text-sm leading-relaxed">{insight.content}</p>
      <div className="flex flex-wrap gap-1 mt-3">
        {insight.tags.map(tag => <Badge key={tag} variant="secondary" className="text-xs">#{tag}</Badge>)}
      </div>
      <p className="text-xs text-gray-400 mt-3 italic">{insight.disclaimer}</p>
    </article>
  );
}
"""

    async def _enrich_with_live_prices(self, insights: list[dict]) -> None:
        """Injects live MENA + global prices into the market context block when available."""
        if not self._market.is_configured():
            return
        symbols = POPULAR_SYMBOLS["mena_stocks"][:3] + POPULAR_SYMBOLS["global"][:2]
        try:
            prices = await self._market.get_batch_prices(symbols)
            live_data = {p["symbol"]: p["price"] for p in prices if p.get("source") != "mock"}
            if live_data:
                for ins in insights:
                    ins.setdefault("market_context", {})["live_prices"] = live_data
                    ins["market_context"]["prices_source"] = "twelve_data"
                    ins["market_context"]["prices_at"] = datetime.utcnow().isoformat()
        except Exception:
            pass

    async def generate_market_insights(self, count: int = 4, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        insights = [self._build_insight_template(cfg) for cfg in TEMPLATE_INSIGHTS[:count]]
        ai_generated = False
        cost, tokens = 0.0, 0

        await self._enrich_with_live_prices(insights)

        if use_ai and self._ai.is_ai_available():
            result = await self._ai.generate(
                prompt=f"Generate a concise weekly market outlook for MENA investors (Tadawul, DFM). Include: macro outlook, top sector pick, key risk to watch. Keep under 120 words. Add Arabic-market-specific context.",
                system_prompt="You are a senior MENA markets analyst writing for Arabic-speaking retail investors. Be factual, balanced, and accessible. Include a disclaimer.",
                max_tokens=400,
            )
            if result.get("success") and result.get("text"):
                insights[0]["content"] = result["text"]
                insights[0]["is_ai_enhanced"] = True
                ai_generated = True
                cost = result.get("cost_usd", 0)
                tokens = result.get("total_tokens", 0)

        patch_files = [
            {"file_path": "src/components/insights/InsightCard.tsx", "operation": "create", "content": self._render_insight_card_component(), "description": "Market insight card component"},
            {"file_path": "src/data/insights/latest.json", "operation": "create_or_update", "content": str({"insights": insights, "generated_at": datetime.utcnow().isoformat(), "count": len(insights)}), "description": "Latest market insights data"},
        ]

        output = OperationalOutput(
            project=OperationProject.fionera,
            output_type=OutputType.market_insight,
            title=f"Market Insights — {len(insights)} Summaries",
            description=f"MENA market insights: weekly outlook, sector rotation, earnings preview, technical setup",
            content={"insights": insights, "indices": MENA_INDICES, "sectors": MARKET_SECTORS},
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=cost,
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.fionera,
            preview_markdown="# Market Insights Preview\n\n" + "\n\n".join(f"## {ins['title']}\n{ins['content'][:200]}..." for ins in insights),
            diff_summary=f"Generates {len(insights)} market insights + InsightCard component",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"user_retention": "+12%", "avg_session_duration": "+45s", "premium_conversions": "+3%"},
        )
        output.preview_id = preview.id
        return output, preview

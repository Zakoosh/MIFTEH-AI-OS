from __future__ import annotations
from datetime import datetime
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel
from ...providers.market_data_provider import TwelveDataProvider, POPULAR_SYMBOLS

WIDGET_CONFIGS = {
    "price_ticker": {
        "name": "Live Price Ticker",
        "description": "Real-time price display with change indicators",
        "data_refresh_seconds": 10,
        "supports": ["stocks", "crypto", "commodities", "forex"],
        "features": ["price", "change_pct", "volume", "sparkline"],
    },
    "portfolio_summary": {
        "name": "Portfolio Summary Card",
        "description": "Compact portfolio overview with P&L",
        "data_refresh_seconds": 30,
        "features": ["total_value", "day_pnl", "total_pnl_pct", "allocation_chart"],
    },
    "market_movers": {
        "name": "Market Movers",
        "description": "Top gainers and losers for the session",
        "data_refresh_seconds": 60,
        "features": ["top_gainers", "top_losers", "most_active", "sector_heatmap"],
    },
    "economic_calendar": {
        "name": "Economic Calendar Widget",
        "description": "Upcoming economic events with impact indicators",
        "data_refresh_seconds": 3600,
        "features": ["event_name", "country", "impact_level", "actual_vs_forecast"],
    },
    "sentiment_gauge": {
        "name": "Market Sentiment Gauge",
        "description": "Fear & Greed index and social sentiment",
        "data_refresh_seconds": 300,
        "features": ["fear_greed_index", "social_mentions", "news_sentiment", "options_put_call"],
    },
}


class FinanceWidgetGenerator:
    PROJECT = "fionera"

    def __init__(self):
        self._ai = ContentGenerator()
        self._market = TwelveDataProvider()

    def _render_price_ticker_component(self) -> str:
        return """import { useEffect, useState } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';

interface TickerItem { symbol: string; price: number; change: number; change_pct: number; volume: string; }

export function PriceTicker({ symbols }: { symbols: string[] }) {
  const [tickers, setTickers] = useState<TickerItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPrices = () => {
      fetch(`/api/market/prices?symbols=${symbols.join(',')}`)
        .then(r => r.json())
        .then(data => { setTickers(data.tickers); setLoading(false); })
        .catch(() => setLoading(false));
    };
    fetchPrices();
    const interval = setInterval(fetchPrices, 10000);
    return () => clearInterval(interval);
  }, [symbols]);

  if (loading) return <div className="ticker-skeleton animate-pulse h-12" />;

  return (
    <div className="price-ticker flex gap-6 overflow-x-auto py-2">
      {tickers.map(t => (
        <div key={t.symbol} className="ticker-item flex items-center gap-2 whitespace-nowrap">
          <span className="font-bold text-sm">{t.symbol}</span>
          <span className="font-mono">{t.price.toLocaleString()}</span>
          <span className={`flex items-center text-sm ${t.change_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {t.change_pct >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
            {Math.abs(t.change_pct).toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  );
}
"""

    def _render_portfolio_widget(self) -> str:
        return """import { PieChart, TrendingUp, TrendingDown } from 'lucide-react';

interface PortfolioData { total_value: number; day_pnl: number; day_pnl_pct: number; total_pnl: number; total_pnl_pct: number; }

export function PortfolioSummaryCard({ data }: { data: PortfolioData }) {
  const isPositiveDay = data.day_pnl >= 0;
  const isPositiveTotal = data.total_pnl >= 0;

  return (
    <div className="portfolio-card rounded-xl p-6 bg-white shadow-sm border">
      <div className="flex justify-between items-start mb-4">
        <h3 className="font-semibold text-gray-600">Portfolio Value</h3>
        <PieChart size={18} className="text-gray-400" />
      </div>
      <p className="text-3xl font-bold mb-1">${data.total_value.toLocaleString()}</p>
      <div className="flex gap-4 mt-3">
        <div className={`flex items-center gap-1 text-sm ${isPositiveDay ? 'text-green-500' : 'text-red-500'}`}>
          {isPositiveDay ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <span>Today: {isPositiveDay ? '+' : ''}{data.day_pnl_pct.toFixed(2)}%</span>
        </div>
        <div className={`flex items-center gap-1 text-sm ${isPositiveTotal ? 'text-green-500' : 'text-red-500'}`}>
          <span>Total: {isPositiveTotal ? '+' : ''}{data.total_pnl_pct.toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}
"""

    def _render_market_movers(self) -> str:
        return """import { ArrowUp, ArrowDown } from 'lucide-react';

interface Mover { symbol: string; name: string; change_pct: number; volume: string; }
interface MarketMoversProps { gainers: Mover[]; losers: Mover[]; }

export function MarketMovers({ gainers, losers }: MarketMoversProps) {
  return (
    <div className="market-movers grid grid-cols-2 gap-4">
      <div>
        <h4 className="font-semibold text-green-600 mb-2 flex items-center gap-1"><ArrowUp size={16}/>Top Gainers</h4>
        {gainers.slice(0,5).map(g => (
          <div key={g.symbol} className="flex justify-between py-1 border-b border-gray-50">
            <div><p className="font-medium text-sm">{g.symbol}</p><p className="text-xs text-gray-500">{g.name}</p></div>
            <span className="text-green-500 font-mono text-sm">+{g.change_pct.toFixed(2)}%</span>
          </div>
        ))}
      </div>
      <div>
        <h4 className="font-semibold text-red-500 mb-2 flex items-center gap-1"><ArrowDown size={16}/>Top Losers</h4>
        {losers.slice(0,5).map(l => (
          <div key={l.symbol} className="flex justify-between py-1 border-b border-gray-50">
            <div><p className="font-medium text-sm">{l.symbol}</p><p className="text-xs text-gray-500">{l.name}</p></div>
            <span className="text-red-500 font-mono text-sm">{l.change_pct.toFixed(2)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

    async def _fetch_seed_prices(self) -> dict:
        """Fetch live seed prices for widget defaults; returns empty dict if unavailable."""
        if not self._market.is_configured():
            return {}
        symbols = POPULAR_SYMBOLS["mena_stocks"][:2] + POPULAR_SYMBOLS["global"][:2] + POPULAR_SYMBOLS["crypto"][:1]
        try:
            prices = await self._market.get_batch_prices(symbols)
            return {p["symbol"]: p["price"] for p in prices}
        except Exception:
            return {}

    async def generate_widgets(self, widget_types: list[str] | None = None, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        targets = widget_types or list(WIDGET_CONFIGS.keys())
        ai_generated = False
        cost, tokens = 0.0, 0
        seed_prices = await self._fetch_seed_prices()

        if use_ai and self._ai.is_ai_available():
            result = await self._ai.generate(
                prompt="Suggest 2 additional finance widget improvements for an Arabic-speaking investment platform (Fionera). Focus on: Islamic finance compatibility, Arabic RTL layout, MENA market data. Return JSON: [{widget_name, description, key_features}]",
                system_prompt="You are a fintech product designer with expertise in MENA markets and Islamic finance.",
                max_tokens=300,
            )
            if result.get("success"):
                ai_generated = True
                cost = result.get("cost_usd", 0)
                tokens = result.get("total_tokens", 0)

        patch_files = [
            {"file_path": "src/components/widgets/PriceTicker.tsx", "operation": "create", "content": self._render_price_ticker_component(), "description": "Live price ticker with 10s refresh"},
            {"file_path": "src/components/widgets/PortfolioSummaryCard.tsx", "operation": "create", "content": self._render_portfolio_widget(), "description": "Portfolio P&L summary card"},
            {"file_path": "src/components/widgets/MarketMovers.tsx", "operation": "create", "content": self._render_market_movers(), "description": "Top gainers/losers widget"},
            {"file_path": "src/config/widgets.json", "operation": "create_or_update", "content": str({k: v for k, v in WIDGET_CONFIGS.items() if k in targets}), "description": "Widget configuration registry"},
        ]

        output = OperationalOutput(
            project=OperationProject.fionera,
            output_type=OutputType.finance_widget,
            title=f"Finance Widgets — {len(targets)} Components",
            description=f"Production-ready finance widgets: {', '.join(targets[:3])}{'...' if len(targets) > 3 else ''}",
            content={"widgets": {k: WIDGET_CONFIGS[k] for k in targets if k in WIDGET_CONFIGS}, "total_widgets": len(targets), "seed_prices": seed_prices, "prices_source": "twelve_data" if seed_prices else "none"},
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=cost,
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.fionera,
            preview_markdown=f"# Finance Widgets — {len(targets)} Components\n\n" + "\n".join(f"## {WIDGET_CONFIGS.get(t, {}).get('name', t)}\n{WIDGET_CONFIGS.get(t, {}).get('description', '')}" for t in targets if t in WIDGET_CONFIGS),
            diff_summary=f"Creates {len(patch_files)} finance widget components",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"user_engagement": "+20%", "data_freshness": "10s refresh", "portfolio_visibility": "improved"},
        )
        output.preview_id = preview.id
        return output, preview

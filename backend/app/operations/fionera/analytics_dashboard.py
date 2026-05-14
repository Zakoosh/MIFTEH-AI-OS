from __future__ import annotations
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel

DASHBOARD_WIDGETS = [
    {"id": "portfolio_chart", "type": "line_chart", "title": "Portfolio Performance", "description": "Equity curve with benchmark overlay", "priority": "critical"},
    {"id": "asset_allocation", "type": "donut_chart", "title": "Asset Allocation", "description": "Portfolio breakdown by asset class and sector", "priority": "critical"},
    {"id": "risk_metrics", "type": "metrics_grid", "title": "Risk Metrics", "description": "Beta, Sharpe ratio, max drawdown, volatility", "priority": "high"},
    {"id": "pl_calendar", "type": "heatmap", "title": "P&L Calendar", "description": "Daily P&L heatmap (like GitHub contribution graph)", "priority": "high"},
    {"id": "top_movers", "type": "ranked_list", "title": "Portfolio Movers", "description": "Best and worst performers today", "priority": "high"},
    {"id": "transaction_log", "type": "data_table", "title": "Recent Transactions", "description": "Paginated transaction history with search", "priority": "medium"},
    {"id": "news_feed", "type": "feed", "title": "Portfolio News", "description": "News relevant to held positions", "priority": "medium"},
]

DASHBOARD_LAYOUT = {
    "grid_columns": 12,
    "rows": [
        {"widgets": ["portfolio_chart", "asset_allocation"], "cols": [8, 4]},
        {"widgets": ["risk_metrics", "pl_calendar", "top_movers"], "cols": [4, 4, 4]},
        {"widgets": ["transaction_log", "news_feed"], "cols": [7, 5]},
    ],
    "responsive_breakpoints": {"mobile": 1, "tablet": 6, "desktop": 12},
}


class AnalyticsDashboardGenerator:
    PROJECT = "fionera"

    def __init__(self):
        self._ai = ContentGenerator()

    def _render_portfolio_chart(self) -> str:
        return """'use client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useState } from 'react';

const PERIODS = ['1W', '1M', '3M', '6M', 'YTD', '1Y', 'ALL'];

export function PortfolioPerformanceChart({ data, benchmark }: { data: ChartPoint[]; benchmark: ChartPoint[]; }) {
  const [period, setPeriod] = useState('1M');

  return (
    <div className="chart-container bg-white rounded-xl p-5 shadow-sm border">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold">Portfolio Performance</h3>
        <div className="flex gap-1">
          {PERIODS.map(p => (
            <button key={p} onClick={() => setPeriod(p)} className={`px-2 py-1 text-xs rounded ${period === p ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100'}`}>{p}</button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
          <ReferenceLine y={0} stroke="#e5e7eb" />
          <Line type="monotone" dataKey="portfolio" stroke="#3b82f6" strokeWidth={2} dot={false} name="Portfolio" />
          <Line type="monotone" dataKey="benchmark" stroke="#9ca3af" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Benchmark" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
"""

    def _render_pnl_heatmap(self) -> str:
        return """'use client';
import { Tooltip } from '@/components/ui/tooltip';

const getColor = (pnl: number) => {
  if (pnl > 3) return 'bg-green-600';
  if (pnl > 1) return 'bg-green-400';
  if (pnl > 0) return 'bg-green-200';
  if (pnl < -3) return 'bg-red-600';
  if (pnl < -1) return 'bg-red-400';
  if (pnl < 0) return 'bg-red-200';
  return 'bg-gray-100';
};

export function PnLCalendar({ data }: { data: { date: string; pnl_pct: number }[] }) {
  return (
    <div className="pnl-calendar bg-white rounded-xl p-5 shadow-sm border">
      <h3 className="font-semibold mb-4">Daily P&L</h3>
      <div className="grid grid-cols-7 gap-1">
        {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d => (
          <div key={d} className="text-center text-xs text-gray-400 pb-1">{d}</div>
        ))}
        {data.map(day => (
          <Tooltip key={day.date} content={`${day.date}: ${day.pnl_pct > 0 ? '+' : ''}${day.pnl_pct.toFixed(2)}%`}>
            <div className={`aspect-square rounded-sm ${getColor(day.pnl_pct)} cursor-default`} />
          </Tooltip>
        ))}
      </div>
      <div className="flex justify-between items-center mt-3 text-xs text-gray-400">
        <span>Loss</span>
        <div className="flex gap-1">{['bg-red-600','bg-red-400','bg-red-200','bg-gray-100','bg-green-200','bg-green-400','bg-green-600'].map(c => <div key={c} className={`w-4 h-4 rounded-sm ${c}`} />)}</div>
        <span>Gain</span>
      </div>
    </div>
  );
}
"""

    def _render_risk_metrics_grid(self) -> str:
        return """interface RiskMetric { label: string; value: string; description: string; trend: 'up' | 'down' | 'neutral'; }

export function RiskMetricsGrid({ metrics }: { metrics: RiskMetric[] }) {
  return (
    <div className="risk-metrics bg-white rounded-xl p-5 shadow-sm border">
      <h3 className="font-semibold mb-4">Risk Metrics</h3>
      <div className="grid grid-cols-2 gap-3">
        {metrics.map(m => (
          <div key={m.label} className="metric-item p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 mb-1">{m.label}</p>
            <p className="text-xl font-bold">{m.value}</p>
            <p className="text-xs text-gray-400 mt-1">{m.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

    async def generate_dashboard_improvements(self, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        ai_generated = False
        cost, tokens = 0.0, 0

        if use_ai and self._ai.is_ai_available():
            result = await self._ai.generate(
                prompt="Suggest 2 analytics dashboard improvements specifically valuable for MENA retail investors. Consider: Islamic finance screening indicators, MENA market hours, Arabic RTL support, halal portfolio compliance score. Return JSON: [{feature, description, value_proposition}]",
                system_prompt="You are a fintech product manager specialising in GCC retail investment platforms.",
                max_tokens=300,
            )
            if result.get("success"):
                ai_generated = True
                cost = result.get("cost_usd", 0)
                tokens = result.get("total_tokens", 0)

        patch_files = [
            {"file_path": "src/components/analytics/PortfolioPerformanceChart.tsx", "operation": "create", "content": self._render_portfolio_chart(), "description": "Portfolio equity curve with period selector"},
            {"file_path": "src/components/analytics/PnLCalendar.tsx", "operation": "create", "content": self._render_pnl_heatmap(), "description": "GitHub-style daily P&L heatmap"},
            {"file_path": "src/components/analytics/RiskMetricsGrid.tsx", "operation": "create", "content": self._render_risk_metrics_grid(), "description": "Risk metrics display: Beta, Sharpe, drawdown"},
            {"file_path": "src/config/dashboard-layout.json", "operation": "create_or_update", "content": str(DASHBOARD_LAYOUT), "description": "Dashboard grid layout configuration"},
        ]

        output = OperationalOutput(
            project=OperationProject.fionera,
            output_type=OutputType.analytics_dashboard,
            title=f"Analytics Dashboard — {len(DASHBOARD_WIDGETS)} Widgets",
            description="Portfolio analytics dashboard: performance chart, P&L heatmap, risk metrics, asset allocation, movers",
            content={"widgets": DASHBOARD_WIDGETS, "layout": DASHBOARD_LAYOUT},
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=cost,
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.fionera,
            preview_markdown="# Analytics Dashboard\n\n## Widgets\n\n" + "\n".join(f"- [{w['priority'].upper()}] **{w['title']}**: {w['description']}" for w in DASHBOARD_WIDGETS),
            diff_summary=f"Creates {len(patch_files)} analytics dashboard components",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"session_duration": "+2min", "feature_adoption": "+40%", "premium_retention": "+15%"},
        )
        output.preview_id = preview.id
        return output, preview

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from ..providers.request_manager import RequestManager
from ..providers.provider_health import ProviderHealthMonitor
from ..providers.schemas import (
    ProviderStatusResponse, ProviderHealthResponse,
    CostResponse, TestProviderRequest, TestProviderResponse, RoutingResponse,
)

router = APIRouter(prefix="/providers", tags=["providers"])
manager = RequestManager()
health_monitor = ProviderHealthMonitor()


@router.get("/status", response_model=ProviderStatusResponse)
async def get_status():
    health = health_monitor.get_cached_health()
    routing = manager.get_routing_info()
    configured = len([h for h in health if h.get("is_configured")])
    return ProviderStatusResponse(
        providers=health,
        active_provider=routing.get("active_provider", "mock"),
        fallback_chain=routing.get("fallback_chain", []),
        total_providers=len(health),
        configured_providers=configured,
    )


@router.get("/health", response_model=ProviderHealthResponse)
async def get_health():
    health = await health_monitor.check_all()
    return ProviderHealthResponse(
        overall=health_monitor.get_overall_status(),
        providers=health,
        last_check=__import__("datetime").datetime.utcnow().isoformat(),
        avg_latency_ms=health_monitor.compute_avg_latency(),
    )


@router.get("/costs", response_model=CostResponse)
async def get_costs(period: str = "24h"):
    summary = manager.get_cost_summary(period)
    return CostResponse(
        period=summary["period"],
        total_cost_usd=summary["total_cost_usd"],
        total_requests=summary["total_requests"],
        total_tokens=summary["total_tokens"],
        by_provider=summary["by_provider"],
        budget_remaining_usd=summary["budget_remaining_usd"],
    )


@router.post("/test", response_model=TestProviderResponse)
async def test_provider(request: TestProviderRequest):
    result = await manager.execute(
        prompt=request.prompt,
        task_type="test",
        max_tokens=request.max_tokens,
    )
    return TestProviderResponse(
        provider=result.get("provider", request.provider),
        model=result.get("model", "unknown"),
        response=result.get("response", ""),
        latency_ms=result.get("latency_ms", 0.0),
        tokens_used=result.get("total_tokens", 0),
        cost_usd=result.get("cost_usd", 0.0),
        success=result.get("success", False),
        error=result.get("error"),
    )


@router.get("/routing", response_model=RoutingResponse)
async def get_routing():
    routing = manager.get_routing_info()
    return RoutingResponse(**routing)

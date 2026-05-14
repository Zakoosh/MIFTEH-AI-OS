from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class ProviderStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    providers: list[dict]
    active_provider: str
    fallback_chain: list[str]
    total_providers: int
    configured_providers: int


class ProviderHealthResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    overall: str
    providers: list[dict]
    last_check: str
    avg_latency_ms: float


class CostResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    period: str
    total_cost_usd: float
    total_requests: int
    total_tokens: int
    by_provider: list[dict]
    budget_remaining_usd: float


class TestProviderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    provider: str = "mock"
    prompt: str = "Hello, are you available?"
    max_tokens: int = 100


class TestProviderResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    provider: str
    model: str
    response: str
    latency_ms: float
    tokens_used: int
    cost_usd: float
    success: bool
    error: str | None = None


class RoutingResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    active_provider: str
    fallback_chain: list[str]
    routing_rules: list[dict]
    last_fallback: dict | None = None

from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class ProviderType(str, Enum):
    openai = "openai"
    gemini = "gemini"
    anthropic = "anthropic"
    mock = "mock"


class ProviderStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unavailable = "unavailable"
    unknown = "unknown"


class ProviderConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    provider_type: ProviderType
    model: str
    enabled: bool = True
    priority: int = 1
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 30
    max_retries: int = 3
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None
    task_type: str = "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderHealth(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    provider: str
    status: ProviderStatus = ProviderStatus.unknown
    last_check: datetime = Field(default_factory=datetime.utcnow)
    success_rate_24h: float = 100.0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    is_configured: bool = False
    model: str = ""


class CostSummary(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    period: str
    provider: str
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    breakdown: dict[str, float] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class RoutingRule(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    condition: str
    target_provider: str
    fallback_provider: str
    priority: int = 1
    enabled: bool = True
    description: str = ""


class FallbackEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    original_provider: str
    fallback_provider: str
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    latency_ms: float = 0.0

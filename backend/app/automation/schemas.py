from pydantic import BaseModel, Field
from typing import Optional


class ScheduleRequest(BaseModel):
    mission_id: str = Field(..., description="Mission identifier to run")
    project_id: str = Field(..., description="Workspace project identifier")
    interval_minutes: int = Field(..., description="Interval between runs")
    enabled: bool = Field(default=True, description="Whether the schedule is active")
    max_retries: int = Field(default=2, description="Retry limit for failed runs")
    cooldown_minutes: int = Field(default=5, description="Cooldown after each run")
    agent_limit: int = Field(default=0, description="Max mission agents to run. 0 means all.")


class ToggleTaskRequest(BaseModel):
    enabled: Optional[bool] = Field(
        default=None,
        description="Set enabled state. If omitted, the current state is toggled.",
    )

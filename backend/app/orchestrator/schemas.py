from pydantic import BaseModel, Field


class RunCycleRequest(BaseModel):
    dry_run: bool = Field(
        default=True,
        description="Keep the cycle advisory-only. Autonomous execution is not supported.",
    )
    max_missions: int = Field(
        default=5,
        description="Maximum recommended missions to select for this cycle.",
    )
    include_blocked: bool = Field(
        default=False,
        description="Include blocked recommendations in cycle output.",
    )

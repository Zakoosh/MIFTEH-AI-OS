from pydantic import BaseModel, Field


class RunPipelineRequest(BaseModel):
    preview_only: bool = Field(default=True)
    limit: int = Field(default=5, ge=1, le=50)

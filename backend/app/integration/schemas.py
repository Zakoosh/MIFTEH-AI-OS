from pydantic import BaseModel, Field


class IntegrationQuery(BaseModel):
    max_files: int = Field(default=2000, ge=1, le=10000)

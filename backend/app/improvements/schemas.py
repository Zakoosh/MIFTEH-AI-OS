from pydantic import BaseModel, Field


class ImprovementQuery(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)

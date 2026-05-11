from pydantic import BaseModel, Field


class ProductionQuery(BaseModel):
    limit: int = Field(default=5, ge=1, le=25)
    preview_only: bool = Field(default=True)

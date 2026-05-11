from pydantic import BaseModel, Field
from typing import Optional


class ExecutiveQuery(BaseModel):
    project_id: Optional[str] = Field(default=None, description="Optional project filter")

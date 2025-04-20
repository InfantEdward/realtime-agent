from typing import Optional
from pydantic import BaseModel, Field


class AppConfigModel(BaseModel):
    LOG_LEVEL: str = Field(default="INFO")
    LOG_DIR: Optional[str] = None
    EXC_INFO: bool = Field(default=False)
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    # Additional app-level config fields can be added here

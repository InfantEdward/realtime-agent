from typing import List, Callable, Optional, Dict
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    REALTIME_MODEL: str
    TURN_DETECTION_CONFIG: Dict[str, str]
    INPUT_AUDIO_TRANSCRIPT_CONFIG: Dict[str, str]
    INPUT_AUDIO_TRANSCRIPT_PREFIX: str = ""
    OUTPUT_AUDIO_TRANSCRIPT_PREFIX: str = ""
    INPUT_OUTPUT_TRANSCRIPTS_SEP: str = "\n\n\n"
    TOOL_CHOICE: Optional[str] = "auto"
    LOG_REALTIME_EVENTS: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    LOG_DIR: Optional[str] = None
    EXC_INFO: bool = Field(default=False)
    INSTRUCTIONS: Optional[str] = None
    TOOL_LIST: List[Callable] = Field(default_factory=list)

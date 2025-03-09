from typing import List, Callable, Optional, Dict, ClassVar, Union
from pydantic import BaseModel, Field, field_validator


class ConfigModel(BaseModel):
    REALTIME_MODEL: str
    TEMPERATURE: float
    VOICE: Optional[str] = None
    TURN_DETECTION_CONFIG: Dict[str, Union[str, int, float, bool]]
    INPUT_AUDIO_TRANSCRIPT_CONFIG: Dict[str, str]
    TOOL_CHOICE: Optional[str] = "auto"
    INITIAL_USER_MESSAGE: Optional[str] = None
    LOG_LEVEL: str = Field(default="INFO")
    LOG_DIR: Optional[str] = None
    EXC_INFO: bool = Field(default=False)
    INSTRUCTIONS: Optional[str] = None
    TOOL_LIST: List[Callable] = Field(default_factory=list)
    TOOL_SCHEMA_LIST: Optional[List[Dict[str, str]]] = None

    ACCEPTABLE_VOICES: ClassVar[set] = {
        "alloy",
        "ash",
        "ballad",
        "coral",
        "echo",
        "sage",
        "shimmer",
        "verse",
    }

    @field_validator("VOICE")
    def validate_voice(cls, v):
        if v is not None and v not in cls.ACCEPTABLE_VOICES:
            raise ValueError(f"VOICE must be one of {cls.ACCEPTABLE_VOICES}")
        return v

from typing import List, Optional, Dict, ClassVar, Union
from pydantic import BaseModel, Field, field_validator
from app.utils.tool_types import UserTool, RouteTool


class ConfigModel(BaseModel):
    name: str
    description: Optional[str] = None
    REALTIME_MODEL: str
    TEMPERATURE: float
    VOICE: Optional[str] = None
    TURN_DETECTION_CONFIG: Dict[str, Union[str, int, float, bool]]
    INPUT_AUDIO_TRANSCRIPT_CONFIG: Dict[str, str]
    TOOL_CHOICE: Optional[str] = "auto"
    INITIAL_USER_MESSAGE: Optional[str] = None
    INSTRUCTIONS: Optional[str] = None
    SWITCH_CONTEXT: Optional[str] = None
    SWITCH_USER_MESSAGE: Optional[str] = None
    SWITCH_NOTIFICATION_MESSAGE: Optional[str] = None
    TOOL_NAMES: Optional[List[str]] = None
    TOOL_LIST: List[Union[UserTool, RouteTool]] = Field(default_factory=list)
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

    @field_validator("TEMPERATURE")
    def validate_temperature(cls, v):
        if not (0.6 <= v <= 1.2):
            raise ValueError("TEMPERATURE must be within the range [0.6, 1.2]")
        return v

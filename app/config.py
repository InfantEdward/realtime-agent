import json
import os
from dotenv import load_dotenv
from app.models.config import ConfigModel
from app.user_tools import obtener_clima


load_dotenv()


config = ConfigModel(
    REALTIME_MODEL=os.getenv("REALTIME_MODEL"),
    TURN_DETECTION_CONFIG=json.loads(os.getenv("TURN_DETECTION_CONFIG")),
    INPUT_AUDIO_TRANSCRIPT_CONFIG=json.loads(
        os.getenv("INPUT_AUDIO_TRANSCRIPT_CONFIG")
    ),
    INPUT_AUDIO_TRANSCRIPT_PREFIX=os.getenv(
        "INPUT_AUDIO_TRANSCRIPT_PREFIX", ""
    ),
    OUTPUT_AUDIO_TRANSCRIPT_PREFIX=os.getenv(
        "OUTPUT_AUDIO_TRANSCRIPT_PREFIX", ""
    ),
    INPUT_OUTPUT_TRANSCRIPTS_SEP=os.getenv(
        "INPUT_OUTPUT_TRANSCRIPTS_SEP", "\n\n\n"
    ),
    TOOL_CHOICE=os.getenv("TOOL_CHOICE", "auto"),
    LOG_REALTIME_EVENTS=os.getenv("LOG_REALTIME_EVENTS", "false").lower()
    == "true",
    LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO").upper(),
    LOG_DIR=os.getenv("LOG_DIR", ""),
    EXC_INFO=os.getenv("EXC_INFO", "False").lower() == "true",
    INSTRUCTIONS="Eres un amable asistente.",
    TOOL_LIST=[obtener_clima],
)

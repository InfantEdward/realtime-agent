import json
import os
from dotenv import load_dotenv
from app.models.config_model import ConfigModel
from app.user_tools import obtener_clima


load_dotenv()


config = ConfigModel(
    REALTIME_MODEL=os.getenv("REALTIME_MODEL"),
    TEMPERATURE=float(os.getenv("TEMPERATURE")),
    VOICE=os.getenv("VOICE"),
    TURN_DETECTION_CONFIG=json.loads(os.getenv("TURN_DETECTION_CONFIG")),
    INPUT_AUDIO_TRANSCRIPT_CONFIG=json.loads(
        os.getenv("INPUT_AUDIO_TRANSCRIPT_CONFIG")
    ),
    TOOL_CHOICE=os.getenv("TOOL_CHOICE", "auto"),
    INITIAL_USER_MESSAGE=None,  # ¡Hola!
    LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO").upper(),
    LOG_DIR=os.getenv("LOG_DIR", ""),
    EXC_INFO=os.getenv("EXC_INFO", "False").lower() == "true",
    INSTRUCTIONS="Eres un amable asistente.",
    TOOL_LIST=[obtener_clima],
    TOOL_SCHEMA_LIST=None,
)

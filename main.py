import os
import json
from dotenv import load_dotenv
from src.utils.logging.log_utils import CustomLogger
from user_tools import obtener_clima
from openai import AsyncOpenAI
from src.agent.agent import RealtimeAgent
from src.audio.audio_handler import RealtimeAudioHandler
from src.frontend.frontend import RealtimeFrontend


load_dotenv()

TOOL_LIST = [obtener_clima]

if __name__ == "__main__":

    INSTRUCTIONS = "Eres un amable asistente."

    REALTIME_MODEL = os.getenv("REALTIME_MODEL")
    TURN_DETECTION_CONFIG = json.loads(os.getenv("TURN_DETECTION_CONFIG"))
    INPUT_AUDIO_TRANSCRIPT_CONFIG = json.loads(
        os.getenv("INPUT_AUDIO_TRANSCRIPT_CONFIG")
    )
    INPUT_AUDIO_TRANSCRIPT_PREFIX = os.getenv("INPUT_AUDIO_TRANSCRIPT_PREFIX")
    OUTPUT_AUDIO_TRANSCRIPT_PREFIX = os.getenv(
        "OUTPUT_AUDIO_TRANSCRIPT_PREFIX"
    )
    INPUT_OUTPUT_TRANSCRIPTS_SEP = os.getenv("INPUT_OUTPUT_TRANSCRIPTS_SEP")
    TOOL_CHOICE = os.getenv("TOOL_CHOICE")
    LOG_REALTIME_EVENTS = os.getenv("LOG_REALTIME_EVENTS").lower() == "true"

    logger = CustomLogger(__name__)
    realtime_agent = RealtimeAgent(
        model=REALTIME_MODEL,
        client=AsyncOpenAI(),
        turn_detection=TURN_DETECTION_CONFIG,
        system_prompt=INSTRUCTIONS,  # Optional
        input_audio_transcription=INPUT_AUDIO_TRANSCRIPT_CONFIG,  # Optional
        input_audio_transcription_prefix=INPUT_AUDIO_TRANSCRIPT_PREFIX,  # Optional
        output_audio_transcription_prefix=OUTPUT_AUDIO_TRANSCRIPT_PREFIX,  # Optional
        input_output_transcripts_sep=INPUT_OUTPUT_TRANSCRIPTS_SEP,  # Optional
        tools=TOOL_LIST,  # Optional
        tool_choice=TOOL_CHOICE,  # Optional
        logger=logger,  # Optional
        log_events=LOG_REALTIME_EVENTS,  # Optional
    )
    audio_handler = RealtimeAudioHandler(realtime_agent=realtime_agent)
    app = RealtimeFrontend(
        realtime_agent=realtime_agent,
        audio_handler=audio_handler,
        logger=logger,
    )
    app.run()

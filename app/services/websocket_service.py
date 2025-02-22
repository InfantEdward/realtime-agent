import asyncio
import uuid
import base64

from typing import Dict
from starlette.websockets import WebSocketState
from fastapi import WebSocket

from openai import AsyncOpenAI

from app.config import config
from app.models.agent import OpenAIRealtimeAgent
from app.utils.logging import CustomLogger

logger = CustomLogger(__name__)


class WebsocketService:

    def __init__(self):
        self.active_sessions: Dict[str, OpenAIRealtimeAgent] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self.session_websockets: Dict[str, WebSocket] = {}

    async def start_session(self):
        """
        Creates a RealtimeAgent and spawns a background task to read agent.connect().
        """
        session_id = str(uuid.uuid4())
        logger.info(f"Creating session {session_id}")

        agent = OpenAIRealtimeAgent(
            model=config.REALTIME_MODEL,
            client=AsyncOpenAI(),
            turn_detection=config.TURN_DETECTION_CONFIG,
            system_prompt=config.INSTRUCTIONS,
            input_audio_transcription=config.INPUT_AUDIO_TRANSCRIPT_CONFIG,
            input_audio_transcription_prefix=config.INPUT_AUDIO_TRANSCRIPT_PREFIX,
            output_audio_transcription_prefix=config.OUTPUT_AUDIO_TRANSCRIPT_PREFIX,
            input_output_transcripts_sep=config.INPUT_OUTPUT_TRANSCRIPTS_SEP,
            tools=config.TOOL_LIST,
            tool_choice=config.TOOL_CHOICE,
            logger=logger,
            log_events=config.LOG_REALTIME_EVENTS,
        )
        self.active_sessions[session_id] = agent

        task = asyncio.create_task(
            self.consume_agent_events(session_id, agent)
        )
        self.agent_tasks[session_id] = task

        return {"session_id": session_id}

    async def stop_session(self, session_id: str):
        """
        Stops an existing session and closes the WebSocket if open.
        """
        logger.info(f"Stopping session {session_id}")

        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.agent_tasks:
            self.agent_tasks[session_id].cancel()
            del self.agent_tasks[session_id]
        if session_id in self.session_websockets:
            ws = self.session_websockets[session_id]
            if ws.client_state != WebSocketState.DISCONNECTED:
                await ws.close()
            del self.session_websockets[session_id]

        return {"status": "Session stopped"}

    async def handle_websocket(self, websocket, session_id: str):
        """
        - Accept the WebSocket
        - Check for valid session
        - Wait for agent.get_connection()
        - Forward 'audio_chunk' messages to the agent
        - On disconnect, clean up
        """
        logger.info(f"WebSocket connected for session_id={session_id}")
        await websocket.accept()

        if session_id not in self.active_sessions:
            logger.error(f"No such session {session_id}")
            await websocket.send_json(
                {"type": "error", "message": "Invalid session_id"}
            )
            await websocket.close()
            return

        # Keep track of this WebSocket
        self.session_websockets[session_id] = websocket

        agent = self.active_sessions[session_id]
        connection = await agent.get_connection()
        logger.info(
            f"Realtime connection established for session {session_id}"
        )

        try:
            while True:
                msg = await websocket.receive_json()
                msg_type = msg.get("type")

                if msg_type == "audio_chunk":
                    raw_pcm = base64.b64decode(msg["audio"])
                    # Just append => indefinite partial transcripts
                    await connection.input_audio_buffer.append(
                        audio=base64.b64encode(raw_pcm).decode("utf-8")
                    )
                    logger.debug(
                        f"Appended {len(raw_pcm)} bytes of PCM for session {session_id}"
                    )

                elif msg_type == "disconnect":
                    logger.info("Client requested disconnect.")
                    break

        finally:
            # Cleanup
            if self.session_websockets.get(session_id) == websocket:
                del self.session_websockets[session_id]
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
            logger.info(f"WebSocket closed for session {session_id}")

    async def consume_agent_events(
        self, session_id: str, agent: OpenAIRealtimeAgent
    ):
        """
        Reads events from agent.connect() in a background task:
         - session.created
         - session.updated
         - transcript_delta
         - audio_delta
        Sends them to the user's WebSocket if connected.
        """
        logger.info(f"consume_agent_events -> start for session {session_id}")
        async for evt_type, payload in agent.connect():
            logger.info(f"Session {session_id} => Event: {evt_type}")

            ws = self.session_websockets.get(session_id)
            if ws:
                if evt_type == "transcript_delta":
                    await ws.send_json(
                        {"type": "transcript_delta", "text": payload}
                    )
                elif evt_type == "audio_delta":
                    # payload.delta is base64 audio
                    audio_b64 = payload.delta
                    await ws.send_json(
                        {
                            "type": "audio_delta",
                            "audio": audio_b64,
                            "item_id": payload.item_id,
                        }
                    )

        logger.info(f"consume_agent_events -> ended for session {session_id}")

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
            temperature=config.TEMPERATURE,
            voice=config.VOICE,
            turn_detection=config.TURN_DETECTION_CONFIG,
            system_prompt=config.INSTRUCTIONS,
            input_audio_transcript_config=config.INPUT_AUDIO_TRANSCRIPT_CONFIG,
            tools=config.TOOL_LIST,
            tool_schema_list=config.TOOL_SCHEMA_LIST,
            tool_choice=config.TOOL_CHOICE,
            initial_user_message=config.INITIAL_USER_MESSAGE,
            logger=logger,
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
        realtime_connection = await agent.check_connection()
        if not realtime_connection:
            logger.error(f"Failed to get connection for session {session_id}")
            await websocket.send_json(
                {"type": "error", "message": "Failed to get connection"}
            )
            await websocket.close()
            return
        logger.info(
            f"Realtime connection established for session {session_id}"
        )

        try:
            while True:
                msg = await websocket.receive_json()
                msg_type = msg.get("type")

                match msg_type:
                    case "audio_chunk":
                        raw_pcm = base64.b64decode(msg["audio"])
                        decoded_audio = base64.b64encode(raw_pcm).decode(
                            "utf-8"
                        )
                        await agent.send_audio(audio_b64=decoded_audio)
                        logger.debug(
                            f"Appended {len(raw_pcm)} bytes of PCM for session {session_id}"
                        )
                    case "user_input":
                        text = msg.get("text")
                        await agent.send_message(
                            text=text, message_type="user"
                        )
                    case "disconnect":
                        logger.info("Client requested disconnect.")
                        break
                    case "user_interrupt":
                        logger.info("Client interrupted the conversation.")
                        duration_ms = msg.get("duration_ms")
                        item_id = msg.get("item_id")
                        logger.info(
                            f"Truncating assistant audio at {duration_ms}ms for item_id {item_id}"
                        )
                        await agent.truncate_assistant_audio(
                            audio_end_ms=duration_ms, item_id=item_id
                        )
                    case _:
                        logger.warning(f"Unhandled message type: {msg_type}")

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
                match evt_type:
                    case "input_audio_transcript":
                        await ws.send_json(
                            {"type": "input_audio_transcript", "text": payload}
                        )
                    case "response_audio_transcript_delta":
                        await ws.send_json(
                            {
                                "type": "response_audio_transcript_delta",
                                "text": payload,
                            }
                        )
                    case "response_text_delta":
                        await ws.send_json(
                            {"type": "response_text_delta", "text": payload}
                        )
                    case "audio_delta":
                        # payload.delta is base64 audio
                        audio_b64 = payload.delta
                        await ws.send_json(
                            {
                                "type": "audio_delta",
                                "audio": audio_b64,
                                "item_id": payload.item_id,
                            }
                        )
                    case "user_audio_started":
                        await ws.send_json({"type": "user_audio_started"})
                    case _:
                        logger.warning(f"Unhandled event type: {evt_type}")

        logger.info(f"consume_agent_events -> ended for session {session_id}")

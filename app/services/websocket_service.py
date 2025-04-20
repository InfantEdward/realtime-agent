import asyncio
import uuid
import base64
from typing import Dict
from starlette.websockets import WebSocketState
from fastapi import WebSocket
from app.config import get_agent_configs
from app.services.agent import OpenAIRealtimeAgent
from app.utils.logging import CustomLogger
from app.utils.openai_utils import get_client
import app.route_tool as route_tool_module

logger = CustomLogger(__name__)


class WebsocketService:
    def __init__(self):
        # session_id -> {agent_name: agent_instance}
        self.active_sessions: Dict[str, Dict[str, OpenAIRealtimeAgent]] = {}
        # session_id -> {agent_name: task}
        self.agent_tasks: Dict[str, Dict[str, asyncio.Task]] = {}
        # session_id -> websocket
        self.session_websockets: Dict[str, WebSocket] = {}
        # session_id -> current agent name
        self.session_current_agent: Dict[str, str] = {}
        # cache agent configs by name
        self.agent_configs = {
            agent.name: agent for agent in get_agent_configs()
        }
        self.client = get_client()

    async def start_session(self):
        session_id = str(uuid.uuid4())
        logger.info(f"Creating session {session_id}")
        self.active_sessions[session_id] = {}
        self.agent_tasks[session_id] = {}
        agent_names = list(self.agent_configs.keys())
        if not agent_names:
            raise RuntimeError("No agents configured")
        default_agent = agent_names[0]
        self.session_current_agent[session_id] = default_agent
        # Instantiate the default agent
        await self._ensure_agent(session_id, default_agent)
        # Return session_id and default_agent for frontend
        return {"session_id": session_id, "default_agent": default_agent}

    async def stop_session(self, session_id: str):
        logger.info(f"Stopping session {session_id}")
        if session_id in self.active_sessions:
            for agent in self.active_sessions[session_id].values():
                try:
                    await agent.close()
                except Exception as e:
                    logger.warning(f"Error closing agent connection: {e}")
            del self.active_sessions[session_id]
        if session_id in self.agent_tasks:
            for task in self.agent_tasks[session_id].values():
                task.cancel()
            del self.agent_tasks[session_id]
        # Safely remove and close websocket if present
        ws = self.session_websockets.pop(session_id, None)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.close()
            except RuntimeError as e:
                logger.warning(
                    f"Error closing websocket during stop_session: {e}"
                )
        if session_id in self.session_current_agent:
            del self.session_current_agent[session_id]
        return {"status": "Session stopped"}

    async def _ensure_agent(self, session_id: str, agent_name: str):
        if agent_name in self.active_sessions[session_id]:
            return self.active_sessions[session_id][agent_name]
        cfg = self.agent_configs[agent_name]
        agent = OpenAIRealtimeAgent(
            model=cfg.REALTIME_MODEL,
            client=self.client,
            temperature=cfg.TEMPERATURE,
            voice=cfg.VOICE,
            turn_detection=cfg.TURN_DETECTION_CONFIG,
            system_prompt=cfg.INSTRUCTIONS,
            switch_prompt=cfg.SWITCH_CONTEXT,
            input_audio_transcript_config=cfg.INPUT_AUDIO_TRANSCRIPT_CONFIG,
            tools=cfg.TOOL_LIST,
            tool_schema_list=cfg.TOOL_SCHEMA_LIST,
            tool_choice=cfg.TOOL_CHOICE,
            initial_user_message=cfg.INITIAL_USER_MESSAGE,
            switch_user_message=cfg.SWITCH_USER_MESSAGE,
            switch_notification_message=cfg.SWITCH_NOTIFICATION_MESSAGE,
            logger=logger,
        )
        self.active_sessions[session_id][agent_name] = agent
        # Start background event consumer for this agent
        task = asyncio.create_task(
            self.consume_agent_events(session_id, agent_name, agent)
        )
        self.agent_tasks[session_id][agent_name] = task
        return agent

    async def handle_websocket(self, websocket, session_id: str):
        logger.info(f"WebSocket connected for session_id={session_id}")
        await websocket.accept()
        # Send agent_switched event for consistency with frontend expectations
        default_agent = self.session_current_agent.get(session_id)
        await websocket.send_json(
            {
                "type": "agent_switched",
                "agent_name": default_agent,
                "session_id": session_id,
            }
        )
        if session_id not in self.active_sessions:
            logger.error(f"No such session {session_id}")
            await websocket.send_json(
                {"type": "error", "message": "Invalid session_id"}
            )
            await websocket.close()
            return
        self.session_websockets[session_id] = websocket
        try:
            # Loop until session is stopped or websocket is closed
            while (
                session_id in self.active_sessions
                and websocket.client_state == WebSocketState.CONNECTED
            ):
                try:
                    msg = await websocket.receive_json()
                except Exception as e:
                    logger.info(
                        f"Session {session_id} websocket receive exception: {e}"
                    )
                    break
                msg_type = msg.get("type")
                agent_name = msg.get(
                    "agent_name"
                ) or self.session_current_agent.get(session_id)
                if not agent_name or agent_name not in self.agent_configs:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown or missing agent: {agent_name}",
                        }
                    )
                    continue
                # Guard against session being stopped concurrently
                if session_id not in self.active_sessions:
                    logger.info(
                        f"Session {session_id} removed before ensuring agent, exiting loop"
                    )
                    break
                try:
                    agent = await self._ensure_agent(session_id, agent_name)
                except KeyError:
                    logger.info(
                        f"Session {session_id} no longer active in _ensure_agent, exiting loop"
                    )
                    break
                if msg_type == "switch_agent":
                    self.session_current_agent[session_id] = agent_name
                    await websocket.send_json(
                        {
                            "type": "agent_switched",
                            "agent_name": agent_name,
                            "session_id": session_id,
                        }
                    )
                else:
                    match msg_type:
                        case "audio_chunk":
                            raw_pcm = base64.b64decode(msg["audio"])
                            decoded_audio = base64.b64encode(raw_pcm).decode(
                                "utf-8"
                            )
                            await agent.send_audio(audio_b64=decoded_audio)
                            logger.debug(
                                f"Appended {len(raw_pcm)} bytes of PCM for session {session_id} agent {agent_name}"
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
                            try:
                                await agent.truncate_assistant_audio(
                                    audio_end_ms=duration_ms, item_id=item_id
                                )
                            except Exception as e:
                                logger.warning(f"Error truncating audio: {e}")
                        case _:
                            logger.warning(
                                f"Unhandled message type: {msg_type}"
                            )
        finally:
            # Cancel all agent event tasks for this session to avoid background errors
            if session_id in self.agent_tasks:
                for task in self.agent_tasks[session_id].values():
                    task.cancel()
                del self.agent_tasks[session_id]
            if self.session_websockets.get(session_id) == websocket:
                del self.session_websockets[session_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except RuntimeError as e:
                    logger.warning(f"Error closing websocket in cleanup: {e}")
            logger.info(f"WebSocket closed for session {session_id}")

    async def consume_agent_events(
        self, session_id: str, agent_name: str, agent: OpenAIRealtimeAgent
    ):
        logger.info(
            f"consume_agent_events -> start for session {session_id} agent {agent_name}"
        )
        async for evt_type, payload in agent.connect():
            logger.info(
                f"Session {session_id} [{agent_name}] => Event: {evt_type}"
            )
            ws = self.session_websockets.get(session_id)
            if ws and self.session_current_agent.get(session_id) == agent_name:
                try:
                    match evt_type:
                        case "input_audio_transcript":
                            await ws.send_json(
                                {
                                    "type": "input_audio_transcript",
                                    "text": payload,
                                }
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
                                {
                                    "type": "response_text_delta",
                                    "text": payload,
                                }
                            )
                        case "audio_delta":
                            audio_b64 = getattr(payload, "delta", None)
                            if not audio_b64 or not isinstance(audio_b64, str):
                                logger.error(
                                    f"audio_delta: No valid audio data for agent {agent_name} (type={type(audio_b64)}, "
                                    f"value={audio_b64})"
                                )
                                await ws.send_json(
                                    {
                                        "type": "error",
                                        "message": f"No valid audio data for agent {agent_name}",
                                    }
                                )
                            else:
                                logger.info(
                                    f"audio_delta: Sending {len(audio_b64)} bytes for agent {agent_name}"
                                )
                                await ws.send_json(
                                    {
                                        "type": "audio_delta",
                                        "audio": audio_b64,
                                        "item_id": getattr(
                                            payload, "item_id", None
                                        ),
                                    }
                                )
                        case "user_audio_started":
                            await ws.send_json({"type": "user_audio_started"})
                        case (
                            "response.content_part.done"
                            | "response.output_item.done"
                            | "response.done"
                        ):
                            logger.info(
                                f"Event type: {evt_type} (no frontend action)"
                            )
                        case "agent_switched":
                            # Use TARGET_AGENT_FIELD from route_tool_module.schema_params
                            schema_params = getattr(
                                route_tool_module, "schema_params", {}
                            )
                            target_agent_field = schema_params.get(
                                "TARGET_AGENT_FIELD", "target_agent"
                            )
                            target_agent = payload["params"].get(
                                target_agent_field
                            )
                            input_item = payload["input_item"]
                            output_item = payload["output_item"]
                            previous_agent = self.session_current_agent.get(
                                session_id
                            )
                            if (
                                not target_agent
                                or target_agent not in self.agent_configs
                            ):
                                logger.error(
                                    f"Invalid target_agent in agent_switched event: {target_agent}"
                                )
                                output_item["output"] = (
                                    f"Invalid target_agent: {target_agent}"
                                )
                                # Notify the previous agent about the error
                                await self.active_sessions[session_id][
                                    previous_agent
                                ].notify_switch(
                                    input_item=input_item,
                                    output_item=output_item,
                                    request_response=True,
                                )
                                await ws.send_json(
                                    {
                                        "type": "error",
                                        "message": f"Invalid target_agent: {target_agent}",
                                    }
                                )
                            else:
                                await self._ensure_agent(
                                    session_id, target_agent
                                )
                                self.session_current_agent[session_id] = (
                                    target_agent
                                )
                                await ws.send_json(
                                    {
                                        "type": "agent_switched",
                                        "agent_name": target_agent,
                                        "session_id": session_id,
                                    }
                                )
                                # Notify the previous agent of the switch
                                await self.active_sessions[session_id][
                                    previous_agent
                                ].notify_switch(
                                    input_item=input_item,
                                    output_item=output_item,
                                    request_response=False,
                                )
                                new_agent = self.active_sessions[session_id][
                                    target_agent
                                ]
                                await new_agent.update_agent_instructions(
                                    arguments=payload["params"],
                                )
                        case "error":
                            logger.error(f"Agent error event: {payload}")
                            await ws.send_json(
                                {"type": "error", "message": str(payload)}
                            )
                        case _:
                            await ws.send_json(
                                {
                                    "type": "unhandled_event",
                                    "event": evt_type,
                                    "payload": str(payload),
                                }
                            )
                except Exception as e:
                    logger.error(f"Error sending event to frontend: {e}")
                    await ws.send_json({"type": "error", "message": str(e)})
        logger.info(
            f"consume_agent_events -> ended for session {session_id} agent {agent_name}"
        )

import asyncio
from typing import Any, Callable, Dict, List, Optional
from logging import Logger
from openai import AsyncOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection
from app.utils.logging import CustomLogger
from app.utils.openai_utils import (
    get_tool_call_results,
    send_tool_call_results,
    create_user_message_item,
    send_user_message,
)
from app.utils.tool_utils import (
    validate_schema_list,
    get_tool_schema_from_tool,
)


class OpenAIRealtimeAgent:

    def __init__(
        self,
        model: str,
        client: Optional[AsyncOpenAI] = None,
        temperature: Optional[float] = None,
        voice: Optional[str] = None,
        turn_detection: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        input_audio_transcript_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Callable]] = None,
        tool_schema_list: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        initial_user_message: Optional[str] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.voice = voice
        self.client = client or AsyncOpenAI()
        self.turn_detection = turn_detection
        self.system_prompt = system_prompt
        self.connection: Optional[AsyncRealtimeConnection] = None
        self.session = None
        self.connected = asyncio.Event()

        self.logger = logger or CustomLogger(__name__)

        self.input_audio_transcript_config = input_audio_transcript_config
        self.tools = self.build_tools(tools, tool_schema_list)
        self._tools_callables = tools
        self.tool_choice = tool_choice
        self.initial_user_message = initial_user_message

    async def connect(self):
        async with self.client.beta.realtime.connect(model=self.model) as conn:
            self.connection = conn
            self.connected.set()

            # If you want to set session params:
            update_params = {}
            if self.temperature:
                update_params["temperature"] = self.temperature
            if self.voice:
                update_params["voice"] = self.voice
            if self.turn_detection:
                update_params["turn_detection"] = self.turn_detection
            if self.system_prompt:
                update_params["instructions"] = self.system_prompt
            if self.input_audio_transcript_config:
                update_params["input_audio_transcription"] = (
                    self.input_audio_transcript_config
                )
            if self.tools:
                update_params["tools"] = self.tools
                update_params["tool_choice"] = self.tool_choice

            if update_params:
                await conn.session.update(session=update_params)

            if self.initial_user_message:
                await self.send_message(self.initial_user_message, "user")

            response_audio_items: Dict[str, str] = {}
            response_text_items: Dict[str, str] = {}
            input_transcript = None

            async for event in conn:
                self.logger.info("Event type: " + event.type)
                self.logger.debug(f"Event: {str(event)}")
                evt_type = event.type

                match evt_type:
                    case "session.created":
                        self.session = event.session
                    case "session.updated":
                        self.session = event.session
                    case "response.audio.delta":
                        yield ("audio_delta", event)
                    case (
                        "conversation.item.input_audio_transcription.completed"
                    ):
                        input_transcript = getattr(event, "transcript", "")
                        yield ("input_audio_transcript", input_transcript)
                    case "response.audio_transcript.delta":
                        old_text = response_audio_items.get(event.item_id, "")
                        new_text = old_text + event.delta
                        response_audio_items[event.item_id] = new_text
                        yield ("response_audio_transcript_delta", new_text)
                    case "response.text.delta":
                        old_text = response_text_items.get(event.item_id, "")
                        new_text = old_text + event.delta
                        response_text_items[event.item_id] = new_text
                        yield ("response_text_delta", new_text)
                    case "response.function_call_arguments.done":
                        input_item, output_item = await get_tool_call_results(
                            event=event,
                            tool_list=self._tools_callables or [],
                            logger=self.logger,
                        )
                        await send_tool_call_results(
                            input_item, output_item, conn, self.logger
                        )
                    case "input_audio_buffer.speech_started":
                        yield ("user_audio_started", event)
                    case "input_audio_buffer.speech_stopped":
                        yield ("user_audio_stopped", event)
                    case _:
                        yield (evt_type, event)

    async def send_audio(self, audio_b64: str) -> None:
        """
        Processes an audio chunk that has been encoded to a base64 UTF-8 string.

        Parameters:
            audio_b64 (str): Base64-encoded audio data as a UTF-8 string.
        """
        await self.connection.input_audio_buffer.append(audio=audio_b64)

    async def check_connection(self) -> bool:
        await self.connected.wait()
        if not self.connection:
            raise RuntimeError("Connection not established.")
        return True

    async def send_message(self, text: str, message_type: str) -> None:
        """
        Sends a message to the server.

        Parameters:
            text (str): The text of the message.
            type (str): The type of the message.
        """
        if message_type == "user":
            user_item = create_user_message_item(
                input_text=text, logger=self.logger
            )
            await send_user_message(
                conversation_item=user_item,
                connection=self.connection,
                logger=self.logger,
            )

    async def truncate_assistant_audio(
        self, audio_end_ms: int, item_id: str
    ) -> None:
        """
        Truncates the assistant's audio buffer.
        """
        await self.connection.conversation.item.truncate(
            audio_end_ms=audio_end_ms,
            content_index=0,
            item_id=item_id,
        )

    @staticmethod
    def build_tools(
        callable_tools: Optional[List[Callable]] = None,
        tool_schema_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if tool_schema_list and validate_schema_list(tool_schema_list):
            return tool_schema_list
        elif callable_tools:
            return [get_tool_schema_from_tool(t) for t in callable_tools]
        return []

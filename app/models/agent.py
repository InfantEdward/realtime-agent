import asyncio
from typing import Any, Callable, Dict, List, Optional
from logging import Logger
from openai import AsyncOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection
from app.utils.logging import CustomLogger
from app.utils.openai_utils import (
    get_tool_call_results,
    send_tool_call_results,
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
        turn_detection: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        input_audio_transcription: Optional[Dict[str, Any]] = None,
        input_audio_transcription_prefix: str = "",
        output_audio_transcription_prefix: str = "",
        input_output_transcripts_sep: str = "\n\n\n",
        tools: Optional[List[Callable]] = None,
        tool_schema_list: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        logger: Optional[Logger] = None,
        log_events: bool = False,
    ) -> None:
        self.model = model
        self.client = client or AsyncOpenAI()
        self.turn_detection = turn_detection
        self.system_prompt = system_prompt
        self.connection: Optional[AsyncRealtimeConnection] = None
        self.session = None
        self.connected = asyncio.Event()

        self.logger = logger or CustomLogger(__name__)
        self.log_events = log_events

        self.input_audio_transcription = input_audio_transcription
        self.input_audio_transcription_prefix = (
            input_audio_transcription_prefix
        )
        self.output_audio_transcription_prefix = (
            output_audio_transcription_prefix
        )
        self.input_output_transcripts_sep = input_output_transcripts_sep

        self.tools = self.build_tools(tools, tool_schema_list)
        self._tools_callables = tools
        self.tool_choice = tool_choice

    async def connect(self):
        async with self.client.beta.realtime.connect(model=self.model) as conn:
            self.connection = conn
            self.connected.set()

            # If you want to set session params:
            update_params = {}
            if self.turn_detection:
                update_params["turn_detection"] = self.turn_detection
            if self.system_prompt:
                update_params["instructions"] = self.system_prompt
            if self.input_audio_transcription:
                update_params["input_audio_transcription"] = (
                    self.input_audio_transcription
                )
            if self.tools:
                update_params["tools"] = self.tools
                update_params["tool_choice"] = self.tool_choice

            if update_params:
                await conn.session.update(session=update_params)

            response_audio_items: Dict[str, str] = {}
            response_text_items: Dict[str, str] = {}
            input_transcript = None

            async for event in conn:
                self.logger.info("Event type: " + event.type)
                if self.log_events:
                    self.logger.info(f"Event: {str(event)}")
                evt_type = event.type

                if evt_type == "session.created":
                    self.session = event.session
                    continue
                if evt_type == "session.updated":
                    self.session = event.session
                    continue
                if evt_type == "response.audio.delta":
                    yield ("audio_delta", event)

                if (
                    evt_type
                    == "conversation.item.input_audio_transcription.completed"
                ):
                    input_transcript = getattr(event, "transcript", "")

                if evt_type == "response.audio_transcript.delta":
                    old_text = response_audio_items.get(event.item_id, "")
                    new_text = old_text + event.delta
                    response_audio_items[event.item_id] = new_text

                    if input_transcript:
                        combined = (
                            self.input_audio_transcription_prefix
                            + input_transcript
                            + self.input_output_transcripts_sep
                            + self.output_audio_transcription_prefix
                            + new_text
                        )
                        yield ("transcript_delta", combined)
                    else:
                        yield ("transcript_delta", new_text)

                if evt_type == "response.text.delta":
                    old_text = response_text_items.get(event.item_id, "")
                    new_text = old_text + event.delta
                    response_text_items[event.item_id] = new_text
                    yield ("transcript_delta", new_text)

                if evt_type == "response.function_call_arguments.done":
                    input_item, output_item = await get_tool_call_results(
                        event=event,
                        tool_list=self._tools_callables or [],
                        logger=self.logger,
                    )
                    await send_tool_call_results(
                        input_item, output_item, conn, self.logger
                    )

    async def get_connection(self) -> AsyncRealtimeConnection:
        await self.connected.wait()
        if not self.connection:
            raise RuntimeError("Connection not established.")
        return self.connection

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

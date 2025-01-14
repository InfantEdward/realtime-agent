from typing import Any, Callable, Dict, List, Optional
from logging import Logger
import asyncio
from openai import AsyncOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection
from src.utils.logging.log_utils import CustomLogger
from src.utils.openai.openai_utils import (
    get_tool_call_results,
    send_tool_call_results,
)
from src.utils.tools.tool_utils import (
    get_tool_schema_from_tool,
    validate_schema_list,
)


class RealtimeAgent:
    def __init__(
        self,
        model: str,
        client: AsyncOpenAI,
        turn_detection: Dict[str, Any] = None,
        system_prompt: Optional[str] = None,
        input_audio_transcription: Optional[Dict[str, Any]] = None,
        input_audio_transcription_prefix: Optional[str] = "",
        output_audio_transcription_prefix: Optional[str] = "",
        input_output_transcripts_sep: Optional[str] = "\n\n\n",
        tools: Optional[List[Callable]] = None,
        tool_schema_list: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        logger: Optional[Logger] = None,
        log_events: Optional[bool] = False,
    ) -> None:
        self.model = model
        self.client = client
        self.turn_detection = turn_detection
        self.system_prompt = system_prompt
        self.connection = None
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
        self.session_created_callback: Optional[Callable[[str], None]] = None

    async def connect(self):
        async with self.client.beta.realtime.connect(
            model=self.model,
        ) as conn:
            self.connection = conn
            self.connected.set()

            update_params = {}
            update_params_list = [
                self.turn_detection,
                self.input_audio_transcription,
                self.system_prompt,
                self.tools,
            ]
            update_params_names = [
                "turn_detection",
                "input_audio_transcription",
                "instructions",
                "tools",
            ]

            if self.tools:
                update_params["tool_choice"] = self.tool_choice

            for param, name in zip(update_params_list, update_params_names):
                if param:
                    update_params[name] = param

            if update_params:
                await conn.session.update(
                    session=update_params,
                )

            response_audio_items: dict[str, Any] = {}
            response_text_items: dict[str, Any] = {}
            input_transcript = None

            async for event in conn:
                self.logger.info("Event type: " + event.type)
                if self.log_events:
                    self.logger.info("Event: " + str(event))
                if event.type == "session.created":
                    self.session = event.session
                    if self.session_created_callback:
                        self.session_created_callback(self.session.id)
                    continue
                if event.type == "session.updated":
                    self.session = event.session
                    continue
                if event.type == "response.audio.delta":
                    yield ("audio_delta", event)
                if (
                    event.type
                    == "conversation.item.input_audio_transcription.completed"
                ):
                    try:
                        input_transcript = event.transcript
                    except KeyError:
                        input_transcript = None
                    continue

                if event.type == "response.audio_transcript.delta":
                    try:
                        text = response_audio_items[event.item_id]
                    except KeyError:
                        response_audio_items[event.item_id] = event.delta
                    else:
                        response_audio_items[event.item_id] = (
                            text + event.delta
                        )
                    if input_transcript:
                        yield (
                            "transcript_delta",
                            self.input_audio_transcription_prefix
                            + input_transcript
                            + self.input_output_transcripts_sep
                            + self.output_audio_transcription_prefix
                            + response_audio_items[event.item_id],
                        )
                    else:
                        yield (
                            "transcript_delta",
                            self.output_audio_transcription_prefix
                            + response_audio_items[event.item_id],
                        )

                if event.type == "response.text.delta":
                    try:
                        text = response_text_items[event.item_id]
                    except KeyError:
                        response_text_items[event.item_id] = event.delta
                    else:
                        response_text_items[event.item_id] = text + event.delta

                    yield (
                        "transcript_delta",
                        response_text_items[event.item_id],
                    )

                if event.type == "response.function_call_arguments.done":
                    input_item, output_item = await get_tool_call_results(
                        event=event,
                        tool_list=self._tools_callables,
                        logger=self.logger,
                    )
                    await send_tool_call_results(
                        input_item=input_item,
                        output_item=output_item,
                        connection=conn,
                        logger=self.logger,
                    )

    async def get_connection(self) -> AsyncRealtimeConnection:
        await self.connected.wait()
        assert self.connection is not None
        return self.connection

    def set_session_created_callback(
        self, callback: Callable[[str], None]
    ) -> None:
        self.session_created_callback = callback

    @staticmethod
    def build_tools(
        callable_tools: Optional[List[Callable]] = None,
        tool_schema_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if tool_schema_list:
            if validate_schema_list(tool_schema_list):
                return tool_schema_list
            else:
                return []

        tools = []
        if callable_tools:
            for tool in callable_tools:
                tool_schema = get_tool_schema_from_tool(tool)
                tools.append(tool_schema)
        return tools

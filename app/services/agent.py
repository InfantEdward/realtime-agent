import asyncio
from typing import Any, Tuple, Dict, List, Optional, Union
from logging import Logger
from openai import AsyncOpenAI
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection
from app.utils.logging import CustomLogger
from app.utils.openai_utils import (
    send_tool_call_results,
    send_tool_call_results_without_response_request,
    create_user_message_item,
    send_user_message,
    extract_event_details,
    create_tool_input_output_items,
)
from app.utils.tool_utils import (
    validate_schema_list,
    get_tool_schema_from_tool,
    find_tool_by_name,
    handle_user_tool_call,
    handle_route_tool_call,
    format_string,
)
from app.utils.tool_types import UserTool, RouteTool


class OpenAIRealtimeAgent:

    def __init__(
        self,
        model: str,
        client: Optional[AsyncOpenAI] = None,
        temperature: Optional[float] = None,
        voice: Optional[str] = None,
        turn_detection: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        switch_prompt: Optional[str] = "",
        input_audio_transcript_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Union[UserTool, RouteTool]]] = None,
        tool_schema_list: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        initial_user_message: Optional[str] = None,
        switch_user_message: Optional[str] = None,
        switch_notification_message: Optional[str] = "Agent switched",
        logger: Optional[Logger] = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.voice = voice
        self.client = client or AsyncOpenAI()
        self.turn_detection = turn_detection
        self.system_prompt = system_prompt
        self.switch_prompt = switch_prompt
        self.connection: Optional[AsyncRealtimeConnection] = None
        self.session = None
        self.connected = asyncio.Event()
        self.logger = logger or CustomLogger(__name__)
        self.input_audio_transcript_config = input_audio_transcript_config
        self.tool_objects = tools or []
        self.tool_choice = tool_choice
        self.initial_user_message = initial_user_message
        self.switch_user_message = switch_user_message
        self.switch_notification_message = switch_notification_message
        self.tool_schema_list, self.tool_map = self.build_tools(
            self.tool_objects, tool_schema_list
        )

    async def _handle_user_tool(
        self,
        tool: UserTool,
        arguments: str,
        call_id: str,
        conn: AsyncRealtimeConnection,
    ) -> None:
        result_str = await handle_user_tool_call(
            tool_obj=tool,
            arguments=arguments,
            logger=self.logger,
        )
        input_item, output_item = create_tool_input_output_items(
            call_id=call_id,
            tool_name=tool.name,
            arguments=arguments,
            tool_output=result_str,
            logger=self.logger,
        )
        await send_tool_call_results(
            input_item=input_item,
            output_item=output_item,
            connection=conn,
            logger=self.logger,
        )

    async def _handle_route_tool(
        self,
        tool: RouteTool,
        arguments: str,
        call_id: str,
        agent_switch_message: str,
        conn: AsyncRealtimeConnection,
    ) -> Dict[str, Any]:
        (
            result_str,
            parsed_args,
            passed_arg_validation,
        ) = await handle_route_tool_call(
            tool_obj=tool,
            arguments=arguments,
            agent_switch_message=agent_switch_message,
            logger=self.logger,
        )
        if not passed_arg_validation:
            input_item, output_item = create_tool_input_output_items(
                call_id=call_id,
                tool_name=tool.name,
                arguments=arguments,
                tool_output=result_str,
                logger=self.logger,
            )
            await send_tool_call_results(
                input_item=input_item,
                output_item=output_item,
                connection=conn,
                logger=self.logger,
            )

            return None
        return parsed_args

    async def notify_switch(
        self, input_item: str, output_item: str, request_response: bool
    ) -> None:
        """
        Notify the server about a switch in the agent.
        """
        if request_response:
            await send_tool_call_results(
                input_item=input_item,
                output_item=output_item,
                connection=self.connection,
                logger=self.logger,
            )
        else:
            await send_tool_call_results_without_response_request(
                input_item=input_item,
                output_item=output_item,
                connection=self.connection,
                logger=self.logger,
            )

    async def update_agent_instructions(
        self, arguments: Dict[str, Any]
    ) -> None:
        # Ensure connection is established before updating session
        await self.connected.wait()
        if not self.connection:
            self.logger.error(
                "Cannot update instructions: connection not established"
            )
            return
        if self.switch_prompt:
            self.logger.info("Updating agent instructions")
            formatted_switch_prompt = format_string(
                self.switch_prompt, arguments
            )
            updated_instructions = (
                self.system_prompt + "\n" + formatted_switch_prompt
            )
            await self.connection.session.update(
                session={"instructions": updated_instructions}
            )
            if self.switch_user_message:
                await self.send_message(
                    text=self.switch_user_message, message_type="user"
                )

    async def connect(self):
        async with self.client.beta.realtime.connect(model=self.model) as conn:
            self.connection = conn
            self.connected.set()

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
            if self.tool_schema_list:
                update_params["tools"] = self.tool_schema_list
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
                        call_id, tool_name, arguments = extract_event_details(
                            event=event, logger=self.logger
                        )
                        tool = find_tool_by_name(
                            tools=self.tool_objects,
                            tool_name=tool_name,
                            logger=self.logger,
                        )
                        if isinstance(tool, UserTool):
                            await self._handle_user_tool(
                                tool=tool,
                                arguments=arguments,
                                call_id=call_id,
                                conn=conn,
                            )
                        elif isinstance(tool, RouteTool):
                            parsed_args = await self._handle_route_tool(
                                tool=tool,
                                arguments=arguments,
                                call_id=call_id,
                                agent_switch_message=self.switch_notification_message,
                                conn=conn,
                            )
                            input_item, output_item = (
                                create_tool_input_output_items(
                                    call_id=call_id,
                                    tool_name=tool.name,
                                    arguments=arguments,
                                    tool_output=self.switch_notification_message,
                                    logger=self.logger,
                                )
                            )
                            payload = {
                                "input_item": input_item,
                                "output_item": output_item,
                                "params": parsed_args,
                            }
                            yield ("agent_switched", payload)
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
        await self.connected.wait()
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
        tool_objs: Optional[List[Union[UserTool, RouteTool]]],
        schema_list: Optional[List[Dict[str, Any]]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Union[UserTool, RouteTool]]]:
        """
        Build the JSON-schema list for the API and a name->tool object map.
        """
        # Determine schema list: prefer provided schema_list, else use
        # tool.schema or derive from func
        if schema_list and validate_schema_list(schema_list):
            tool_schemas = schema_list
        else:
            tool_schemas = []
            for t in tool_objs or []:
                if getattr(t, "schema", None) is not None:
                    tool_schemas.append(t.schema)
                else:
                    schema = get_tool_schema_from_tool(t.func)
                    t.schema = (
                        schema  # Set the schema attribute on the tool object
                    )
                    tool_schemas.append(schema)
        # Build lookup map
        tool_map = {t.name: t for t in (tool_objs or [])}
        return tool_schemas, tool_map

    async def close(self) -> None:
        """
        Closes the connection to the server.
        """
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.connected.clear()
        else:
            self.logger.warning(
                "Connection already closed or not established."
            )

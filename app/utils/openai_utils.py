import json
import asyncio
from logging import Logger
from typing import Callable, List, Tuple

from openai.types.beta.realtime.realtime_server_event import (
    RealtimeServerEvent,
)
from openai.types.beta.realtime.conversation_item_param import (
    ConversationItemParam,
)
from openai.types.beta.realtime.conversation_item_content_param import (
    ConversationItemContentParam,
)
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection


def extract_event_details(
    event: RealtimeServerEvent, logger: Logger
) -> Tuple[str, str, str]:
    """
    Extracts details from a RealtimeServerEvent.
    """
    try:
        logger.info("Extracting tool call details from event")
        arguments = event.arguments
        call_id = event.call_id
        tool_name = event.name
        return call_id, tool_name, arguments
    except Exception as e:
        logger.error(f"Error extracting tool call details from event: {e}")
        return None, None, None


def create_user_message_item(
    input_text: str, logger: Logger
) -> ConversationItemParam:
    """
    Creates a user message item.
    """
    try:
        content = ConversationItemContentParam(
            text=input_text, type="input_text"
        )
        logger.debug(f"Creating user message item: {input_text}")
        return ConversationItemParam(
            type="message",
            role="user",
            content=[content],
            status="completed",
        )
    except Exception as e:
        logger.error(f"Error creating user message item: {e}")
        return None


async def send_user_message(
    conversation_item: ConversationItemParam,
    connection: AsyncRealtimeConnection,
    logger: Logger,
) -> None:
    """
    Sends a user message to the server.
    """
    try:
        logger.info("Sending user message to server")
        await connection.conversation.item.create(item=conversation_item)
        await connection.response.create()
        logger.info("User message sent to server")
    except Exception as e:
        logger.error(f"Error sending user message to server: {e}")


def create_tool_input_output_items(
    call_id: str,
    tool_name: str,
    arguments: str,
    tool_output: str,
    logger: Logger,
) -> Tuple[ConversationItemParam, ConversationItemParam]:
    """
    Creates input and output items for a tool call.
    """
    try:
        logger.info(f"Creating items for tool: {tool_name}")
        input_item = ConversationItemParam(
            type="function_call",
            status="completed",
            call_id=call_id,
            name=tool_name,
            arguments=arguments,
        )
        output_item = ConversationItemParam(
            type="function_call_output",
            call_id=call_id,
            output=tool_output,
        )
        return input_item, output_item
    except Exception as e:
        logger.error(f"Error creating items: {e}")
        return None, None


async def get_tool_call_results(
    event: RealtimeServerEvent, tool_list: List[Callable], logger: Logger
) -> Tuple[ConversationItemParam, ConversationItemParam]:
    """
    Gets the results of a tool call.
    """
    call_id, tool_name, arguments = extract_event_details(event, logger)
    if not call_id or not tool_name or not arguments:
        return None, None
    try:
        result_str = "No matching tool found"
        for tool in tool_list:
            if tool.__name__ == tool_name:
                logger.info(f"Calling tool: {tool.__name__}")
                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**json.loads(arguments))
                else:
                    result = tool(**json.loads(arguments))
                result_str = str(result)
                break
    except Exception as e:
        logger.error(
            f"An error occurred while calling the tool: {tool_name}. Error: {e}"
        )
        result_str = f"Error: {e}"

    input_item, output_item = create_tool_input_output_items(
        call_id, tool_name, arguments, result_str, logger
    )
    return input_item, output_item


async def send_tool_call_results(
    input_item: ConversationItemParam,
    output_item: ConversationItemParam,
    connection: AsyncRealtimeConnection,
    logger: Logger,
) -> None:
    """
    Sends the results of a tool call to the server.
    """
    try:
        logger.info("Sending tool call results to server")
        await connection.conversation.item.create(item=input_item)
        await connection.conversation.item.create(item=output_item)
        logger.info("Tool call results sent to server")
        await connection.response.create()
    except Exception as e:
        logger.error(f"Error sending tool call results to server: {e}")

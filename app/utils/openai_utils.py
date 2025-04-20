from logging import Logger
from typing import Tuple

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
from openai import AsyncOpenAI


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


def create_tool_input_item(
    call_id: str,
    tool_name: str,
    arguments: str,
    logger: Logger,
) -> ConversationItemParam:
    """
    Creates an input item for a tool call.
    """
    try:
        logger.debug(f"Creating input item for tool call ID: {call_id}")
        return ConversationItemParam(
            type="function_call",
            status="completed",
            call_id=call_id,
            name=tool_name,
            arguments=arguments,
        )
    except Exception as e:
        logger.error(f"Error creating input item: {e}")
        return None


def create_tool_output_item(
    call_id: str,
    tool_output: str,
    logger: Logger,
) -> ConversationItemParam:
    """
    Creates an output item for a tool call.
    """
    try:
        logger.debug(f"Creating output item for tool call ID: {call_id}")
        return ConversationItemParam(
            type="function_call_output",
            call_id=call_id,
            output=tool_output,
        )
    except Exception as e:
        logger.error(f"Error creating output item: {e}")
        return None


def create_tool_input_output_items(
    call_id: str,
    tool_name: str,
    arguments: str,
    tool_output: str,
    logger: Logger,
) -> Tuple[ConversationItemParam, ConversationItemParam]:
    """
    Creates input and output items for a tool call by calling the respective functions.
    """
    input_item = create_tool_input_item(
        call_id=call_id,
        tool_name=tool_name,
        arguments=arguments,
        logger=logger,
    )
    output_item = create_tool_output_item(
        call_id=call_id, tool_output=tool_output, logger=logger
    )
    return input_item, output_item


async def send_tool_call_results(
    input_item: ConversationItemParam,
    output_item: ConversationItemParam,
    connection: AsyncRealtimeConnection,
    logger: Logger,
) -> None:
    """
    Sends the results of a tool call to the server and requests a response.
    """
    try:
        logger.info("Sending tool call results to server")
        await connection.conversation.item.create(item=input_item)
        await connection.conversation.item.create(item=output_item)
        logger.info("Tool call results sent to server")
        await connection.response.create()
        logger.info("Tool call response request sent to server")
    except Exception as e:
        logger.error(f"Error sending tool call results to server: {e}")


async def send_tool_call_results_without_response_request(
    input_item: ConversationItemParam,
    output_item: ConversationItemParam,
    connection: AsyncRealtimeConnection,
    logger: Logger,
) -> None:
    """
    Sends the results of a tool call to the server without requesting a response.
    """
    try:
        logger.info("Sending tool call results to server")
        await connection.conversation.item.create(item=input_item)
        await connection.conversation.item.create(item=output_item)
        logger.info("Tool call results sent to server.")
    except Exception as e:
        logger.error(f"Error sending tool call results to server: {e}")


def get_client() -> AsyncOpenAI:
    """
    Returns an instance of the OpenAI client.
    """
    try:
        client = AsyncOpenAI()
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to create OpenAI client: {e}")

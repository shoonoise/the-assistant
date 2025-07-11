"""
Telegram messaging activities for Temporal workflows.

This module provides Temporal activities for sending messages via Telegram.
Activities are atomic, idempotent operations that can be retried by Temporal.
"""

import logging
from dataclasses import dataclass

from temporalio import activity

from the_assistant.integrations.telegram.telegram_client import TelegramClient
from the_assistant.utils.config import (
    get_telegram_token,
)

logger = logging.getLogger(__name__)


@dataclass
class SendMessageInput:
    user_id: int
    chat_id: int
    text: str
    parse_mode: str = "Markdown"


@dataclass
class SendFormattedMessageInput:
    user_id: int
    chat_id: int
    title: str
    content: str
    parse_mode: str = "Markdown"


@activity.defn
async def send_message(
    input: SendMessageInput,
) -> bool:
    """
    Activity to send a text message to a Telegram chat.

    Args:
        input: SendMessageInput containing user_id, chat_id, text, and parse_mode

    Returns:
        True if the message was sent successfully

    Raises:
        ValueError: If telegram token is not configured
        Exception: If message sending fails
    """
    logger.info(f"Sending message to chat {input.chat_id} for user {input.user_id}")

    token = get_telegram_token()
    client = TelegramClient(token, user_id=input.user_id)

    return await client.send_message(
        chat_id=input.chat_id,
        text=input.text,
        parse_mode=input.parse_mode,
    )


@activity.defn
async def send_formatted_message(
    input: SendFormattedMessageInput,
) -> bool:
    """
    Activity to send a formatted message with title and content.

    Args:
        input: SendFormattedMessageInput containing user_id, chat_id, title, content, and parse_mode

    Returns:
        True if the message was sent successfully

    Raises:
        ValueError: If telegram token is not configured
        Exception: If message sending fails
    """
    logger.info(f"Sending formatted message to chat {input.chat_id}: {input.title}")

    # Format the message with title and content
    if input.parse_mode == "Markdown":
        formatted_text = f"**{input.title}**\n\n{input.content}"
    elif input.parse_mode == "HTML":
        formatted_text = f"<b>{input.title}</b>\n\n{input.content}"
    else:
        formatted_text = f"{input.title}\n\n{input.content}"

    return await send_message(
        SendMessageInput(
            user_id=input.user_id,
            chat_id=input.chat_id,
            text=formatted_text,
            parse_mode=input.parse_mode,
        )
    )

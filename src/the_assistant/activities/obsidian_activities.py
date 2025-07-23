"""
Obsidian vault activities for Temporal workflows.

This module provides Temporal activities for interacting with Obsidian vaults.
Activities are atomic, idempotent operations that can be retried by Temporal.
"""

import logging
from dataclasses import dataclass

from temporalio import activity

from the_assistant.integrations.obsidian.obsidian_client import ObsidianClient
from the_assistant.models import (
    NoteFilters,
)
from the_assistant.models.obsidian import NoteList
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ScanVaultNotesInput:
    user_id: int
    filters: NoteFilters | None = None


@activity.defn
async def scan_vault_notes(input: ScanVaultNotesInput) -> NoteList:
    """
    Activity to scan vault for notes with optional tag filtering.

    Args:
        input: ScanVaultNotesInput containing user_id and optional filters

    Returns:
        List of ObsidianNote objects matching the filters

    Raises:
        Exception: If vault operation fails
    """
    vault_path = str(get_settings().obsidian_vault_path)

    logger.info(f"Scanning vault at {vault_path} for user_id={input.user_id}")

    client = ObsidianClient(vault_path, user_id=input.user_id)

    return await client.get_notes(input.filters)

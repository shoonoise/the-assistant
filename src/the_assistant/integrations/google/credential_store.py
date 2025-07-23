"""
Credential store for Google OAuth2 credentials.
"""

import json
import logging
from abc import ABC, abstractmethod

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]

from ...db import UserService, get_user_service

logger = logging.getLogger(__name__)


class CredentialStore(ABC):
    """Abstract interface for storing Google OAuth2 credentials."""

    @abstractmethod
    async def get(self, user_id: int) -> Credentials | None:
        """Get credentials for a user."""
        pass

    @abstractmethod
    async def save(self, user_id: int, credentials: Credentials) -> None:
        """Save credentials for a user."""
        pass

    @abstractmethod
    async def delete(self, user_id: int) -> None:
        """Delete credentials for a user."""
        pass


class PostgresCredentialStore(CredentialStore):
    """Credential store backed by :class:`UserService`."""

    def __init__(self, encryption_key: str, user_service: UserService | None = None):
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key.encode())
        self.user_service = user_service or get_user_service()

    async def get(self, user_id: int) -> Credentials | None:
        """Get credentials for a user."""
        enc = await self.user_service.get_google_credentials(user_id)

        if not enc:
            logger.info(f"No credentials found for user {user_id}")
            return None

        try:
            decrypted_data = self.fernet.decrypt(enc.encode())
            creds_dict = json.loads(decrypted_data.decode())
            credentials = Credentials.from_authorized_user_info(creds_dict)
            return credentials
        except Exception as decrypt_error:
            logger.error(
                f"Failed to decrypt credentials for user {user_id}: {decrypt_error}"
            )
            return None

    async def save(self, user_id: int, credentials: Credentials) -> None:
        """Save credentials for a user."""
        creds_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        creds_json = json.dumps(creds_dict)
        encrypted_data = self.fernet.encrypt(creds_json.encode()).decode()

        await self.user_service.set_google_credentials(user_id, encrypted_data)
        logger.info(f"Saved credentials for user {user_id}")

    async def delete(self, user_id: int) -> None:
        """Delete credentials for a user."""
        await self.user_service.set_google_credentials(user_id, None)
        logger.info(f"Deleted credentials for user {user_id}")

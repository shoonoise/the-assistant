"""
Credential store for Google OAuth2 credentials.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import asyncpg
from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]

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
    """Postgres implementation of credential store with Fernet encryption."""

    def __init__(self, database_url: str, encryption_key: str):
        self.database_url = database_url
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key.encode())

    async def get(self, user_id: int) -> Credentials | None:
        """Get credentials for a user."""
        conn = await asyncpg.connect(self.database_url)

        try:
            row = await conn.fetchrow(
                "SELECT google_credentials_enc FROM users WHERE id = $1", user_id
            )

            if not row or not row["google_credentials_enc"]:
                logger.info(f"No credentials found for user {user_id}")
                return None

            # Decrypt credentials
            encrypted_data = row["google_credentials_enc"]
            logger.info(
                f"Found encrypted credentials for user {user_id}, length: {len(encrypted_data)}"
            )

            try:
                decrypted_data = self.fernet.decrypt(encrypted_data.encode())
                creds_dict = json.loads(decrypted_data.decode())
                logger.info(f"Successfully decrypted credentials for user {user_id}")

                credentials = Credentials.from_authorized_user_info(creds_dict)
                logger.info(f"Created credentials object for user {user_id}")
                logger.info(f"  - valid: {credentials.valid}")
                logger.info(f"  - expired: {credentials.expired}")
                logger.info(f"  - has_token: {bool(credentials.token)}")
                logger.info(f"  - has_refresh_token: {bool(credentials.refresh_token)}")
                logger.info(f"  - scopes: {credentials.scopes}")
                return credentials

            except Exception as decrypt_error:
                logger.error(
                    f"Failed to decrypt credentials for user {user_id}: {decrypt_error}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            return None
        finally:
            await conn.close()

    async def save(self, user_id: int, credentials: Credentials) -> None:
        """Save credentials for a user."""
        conn = await asyncpg.connect(self.database_url)

        try:
            # Convert credentials to dict
            creds_dict = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            }

            # Encrypt credentials
            creds_json = json.dumps(creds_dict)
            encrypted_data = self.fernet.encrypt(creds_json.encode()).decode()

            # Save to database
            await conn.execute(
                """
                UPDATE users
                SET google_credentials_enc = $1, google_creds_updated_at = $2
                WHERE id = $3
            """,
                encrypted_data,
                datetime.now(UTC),
                user_id,
            )

            logger.info(f"Saved credentials for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to save credentials for user {user_id}: {e}")
            raise
        finally:
            await conn.close()

    async def delete(self, user_id: int) -> None:
        """Delete credentials for a user."""
        conn = await asyncpg.connect(self.database_url)

        try:
            await conn.execute(
                """
                UPDATE users
                SET google_credentials_enc = NULL, google_creds_updated_at = NULL
                WHERE id = $1
            """,
                user_id,
            )

            logger.info(f"Deleted credentials for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to delete credentials for user {user_id}: {e}")
            raise
        finally:
            await conn.close()

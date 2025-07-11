#!/usr/bin/env python3
"""
Database initialization script for the_assistant.
Creates the database and tables with proper schema.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg
from cryptography.fernet import Fernet

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize the database and tables for the_assistant."""

    def __init__(self, database_url: str, encryption_key: str):
        """
        Initialize the database initializer.
        
        Args:
            database_url: URL for the database connection
            encryption_key: Key for encrypting sensitive data
        """
        self.database_url = database_url
        self.encryption_key = encryption_key
        # Validate encryption key
        try:
            self.fernet = Fernet(encryption_key.encode())
        except Exception as e:
            logger.error(f"Invalid encryption key: {e}")
            raise ValueError(f"Invalid encryption key: {e}")

    async def create_database_if_not_exists(self) -> None:
        """Create the_assistant database if it doesn't exist."""
        # Extract connection parameters from the URL
        # Example URL: postgresql://temporal:temporal@localhost:5432/the_assistant
        parts = self.database_url.split("/")
        db_name = parts[-1]
        base_url = "/".join(parts[:-1]) + "/postgres"  # Connect to default postgres database
        
        logger.info(f"Checking if database {db_name} exists...")
        
        # Connect to default postgres database
        conn = await asyncpg.connect(base_url)
        
        try:
            # Check if the_assistant database exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            
            if not result:
                logger.info(f"Creating database {db_name}...")
                await conn.execute(f"CREATE DATABASE {db_name}")
                logger.info("Database created successfully")
            else:
                logger.info(f"Database {db_name} already exists")
        finally:
            await conn.close()

    async def create_users_table(self) -> None:
        """Create users table with proper schema."""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            logger.info("Creating users table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id                      SERIAL PRIMARY KEY,
                    auth_provider           TEXT NOT NULL,
                    external_id             TEXT NOT NULL,
                    username                TEXT,
                    first_name              TEXT,
                    last_name               TEXT,
                    registered_at           TIMESTAMPTZ DEFAULT now(),
                    
                    -- Google auth
                    google_credentials_enc  TEXT,
                    google_creds_updated_at TIMESTAMPTZ,
                    
                    created_at              TIMESTAMPTZ DEFAULT now(),
                    updated_at              TIMESTAMPTZ DEFAULT now(),
                    
                    UNIQUE(auth_provider, external_id)
                );
                
                -- Index for faster lookups by auth provider and external ID
                CREATE INDEX IF NOT EXISTS idx_users_auth_external ON users(auth_provider, external_id);
                
                -- Index for faster lookups by username
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                
                -- Index for updated_at to help with finding recently modified records
                CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);
            """)
            logger.info("Users table created successfully")
        finally:
            await conn.close()

    async def create_user_settings_table(self) -> None:
        """Create user_settings table with proper schema."""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            logger.info("Creating user_settings table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id         SERIAL PRIMARY KEY,
                    user_id    INT NOT NULL,
                    key        TEXT NOT NULL,
                    value_json TEXT,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now(),
                    
                    UNIQUE(user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                -- Index for faster lookups by user_id
                CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);
                -- Index for faster lookups by key
                CREATE INDEX IF NOT EXISTS idx_user_settings_key ON user_settings(key);
                -- Index for faster lookups by user_id and key combination
                CREATE INDEX IF NOT EXISTS idx_user_settings_user_key ON user_settings(user_id, key);
                -- Index for updated_at to help with finding recently modified settings
                CREATE INDEX IF NOT EXISTS idx_user_settings_updated_at ON user_settings(updated_at);
            """)
            logger.info("User settings table created successfully")
        finally:
            await conn.close()

    async def run(self) -> None:
        """Run the complete initialization process."""
        logger.info("Starting database initialization...")
        
        try:
            await self.create_database_if_not_exists()
            await self.create_users_table()
            await self.create_user_settings_table()
            
            logger.info("Database initialization completed successfully!")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize the_assistant database")
    parser.add_argument(
        "--database-url", 
        default=os.getenv("DATABASE_URL", "postgresql://temporal:temporal@localhost:5432/the_assistant"),
        help="Database URL (default: from DATABASE_URL env var)"
    )
    parser.add_argument(
        "--encryption-key",
        default=os.getenv("DB_ENCRYPTION_KEY"),
        help="Encryption key for sensitive data (default: from DB_ENCRYPTION_KEY env var)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Validate encryption key
    if not args.encryption_key:
        logger.error("DB_ENCRYPTION_KEY is required")
        parser.print_help()
        sys.exit(1)
    
    try:
        initializer = DatabaseInitializer(args.database_url, args.encryption_key)
        await initializer.run()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
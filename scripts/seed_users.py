#!/usr/bin/env python3
"""
Seed script to create the_assistant database and populate users table.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
from cryptography.fernet import Fernet

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    def __init__(self, database_url: str, encryption_key: str):
        self.database_url = database_url
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key.encode())

    async def create_database_if_not_exists(self) -> None:
        """Create the_assistant database if it doesn't exist."""
        # Connect to default postgres database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="temporal",
            password="temporal",
            database="temporal"
        )
        
        try:
            # Check if the_assistant database exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = 'the_assistant'"
            )
            
            if not result:
                logger.info("Creating the_assistant database...")
                await conn.execute("CREATE DATABASE the_assistant")
                logger.info("Database created successfully")
            else:
                logger.info("Database the_assistant already exists")
        finally:
            await conn.close()

    async def create_users_table(self) -> None:
        """Create users table if it doesn't exist."""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id                      SERIAL PRIMARY KEY,
                    auth_provider           TEXT NOT NULL,
                    external_id             TEXT NOT NULL,
                    username                TEXT,
                    first_name              TEXT,
                    last_name               TEXT,
                    registered_at           TIMESTAMPTZ,
                    preferred_briefing_time TIME,
                    timezone                TEXT,
                    
                    -- Google auth
                    google_credentials_enc  TEXT,
                    google_creds_updated_at TIMESTAMPTZ,
                    google_calendar_id      TEXT,
                    
                    created_at              TIMESTAMPTZ DEFAULT now(),
                    updated_at              TIMESTAMPTZ DEFAULT now(),
                    
                    UNIQUE(auth_provider, external_id)
                );
            """)
            logger.info("Users table created/verified successfully")
        finally:
            await conn.close()

    async def create_user_settings_table(self) -> None:
        """Create user_settings table if it doesn't exist."""
        conn = await asyncpg.connect(self.database_url)

        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    id         SERIAL PRIMARY KEY,
                    user_id    INT NOT NULL,
                    key        TEXT NOT NULL,
                    value_json TEXT,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now(),
                    UNIQUE(user_id, key)
                );
                """
            )
            logger.info("User settings table created/verified successfully")
        finally:
            await conn.close()

    async def seed_users(self, users_file: str = "users.json") -> None:
        """Seed users from JSON file."""
        if not os.path.exists(users_file):
            logger.error(f"Users file {users_file} not found")
            return

        with open(users_file, 'r') as f:
            users_data = json.load(f)

        conn = await asyncpg.connect(self.database_url)
        
        try:
            for user_data in users_data:
                # Check if user already exists
                existing = await conn.fetchrow(
                    "SELECT id FROM users WHERE auth_provider = $1 AND external_id = $2",
                    user_data["auth_provider"],
                    user_data["external_id"]
                )
                
                if existing:
                    logger.info(f"User {user_data['external_id']} already exists, skipping")
                    continue
                
                # Parse datetime string
                registered_at = None
                if user_data.get("registered_at"):
                    try:
                        registered_at = datetime.fromisoformat(user_data["registered_at"])
                    except ValueError:
                        logger.warning(f"Invalid datetime format: {user_data['registered_at']}")
                
                # Parse time string
                preferred_briefing_time = None
                if user_data.get("preferred_briefing_time"):
                    try:
                        preferred_briefing_time = datetime.strptime(user_data["preferred_briefing_time"], "%H:%M").time()
                    except ValueError:
                        logger.warning(f"Invalid time format: {user_data['preferred_briefing_time']}")
                
                # Insert new user
                await conn.execute("""
                    INSERT INTO users (
                        auth_provider, external_id, username, first_name, last_name,
                        registered_at, preferred_briefing_time, timezone
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                    user_data["auth_provider"],
                    user_data["external_id"],
                    user_data.get("username"),
                    user_data.get("first_name"),
                    user_data.get("last_name"),
                    registered_at,
                    preferred_briefing_time,
                    user_data.get("timezone")
                )
                
                logger.info(f"Created user {user_data['external_id']}")
            
            logger.info("User seeding completed")
        finally:
            await conn.close()

    async def run(self) -> None:
        """Run the complete seeding process."""
        logger.info("Starting database seeding...")
        
        await self.create_database_if_not_exists()
        await self.create_users_table()
        await self.create_user_settings_table()
        await self.seed_users()
        
        logger.info("Seeding completed successfully!")


async def main():
    """Main entry point."""
    # Get configuration from environment
    database_url = os.getenv(
        "DATABASE_URL", 
        "postgresql://temporal:temporal@localhost:5432/the_assistant"
    )
    
    encryption_key = os.getenv("DB_ENCRYPTION_KEY")
    if not encryption_key:
        logger.error("DB_ENCRYPTION_KEY is required")
        raise SystemExit(1)
    
    seeder = DatabaseSeeder(database_url, encryption_key)
    await seeder.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 
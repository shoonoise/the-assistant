#!/usr/bin/env python3
"""
Database initialization script using Alembic migrations.
Creates the database and runs migrations to set up the schema.
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize the database using Alembic migrations."""

    def __init__(self, database_url: str):
        """
        Initialize the database initializer.
        
        Args:
            database_url: URL for the database connection
        """
        self.database_url = database_url
        self.sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def create_database_if_not_exists(self) -> None:
        """Create the database if it doesn't exist."""
        # Extract connection parameters from the URL
        parts = self.database_url.split("/")
        db_name = parts[-1]
        # Connect to default postgres database
        base_url = "/".join(parts[:-1]).replace("postgresql+asyncpg://", "postgresql://") + "/postgres"
        
        logger.info(f"Checking if database {db_name} exists...")
        
        try:
            conn = await asyncpg.connect(base_url)
            try:
                # Check if database exists
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
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise

    def run_migrations(self) -> None:
        """Run Alembic migrations to set up the schema."""
        logger.info("Running Alembic migrations...")
        
        try:
            # Set up Alembic configuration
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", self.sync_database_url)
            
            # Run migrations
            command.upgrade(alembic_cfg, "head")
            logger.info("Migrations completed successfully")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    async def run(self) -> None:
        """Run the complete initialization process."""
        logger.info("Starting database initialization with migrations...")
        
        try:
            await self.create_database_if_not_exists()
            self.run_migrations()
            
            logger.info("Database initialization completed successfully!")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize database using Alembic migrations")
    parser.add_argument(
        "--database-url", 
        default=None,
        help="Database URL (default: from settings)"
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
    
    # Get database URL
    if args.database_url:
        database_url = args.database_url
    else:
        settings = get_settings()
        database_url = settings.database_url
    
    try:
        initializer = DatabaseInitializer(database_url)
        await initializer.run()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
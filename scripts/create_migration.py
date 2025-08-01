#!/usr/bin/env python3
"""
Create Alembic migration with proper database connection handling.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


def get_database_url(local: bool = False) -> str:
    """Get database URL from environment variables."""
    # Default values matching docker-compose
    db_user = os.getenv("POSTGRES_USER", "temporal")
    db_password = os.getenv("POSTGRES_PASSWORD", "temporal")
    db_host = "localhost" if local else os.getenv("POSTGRES_HOST", "postgresql")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "the_assistant")
    
    # Check if DATABASE_URL is set directly
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if local:
            database_url = database_url.replace("postgresql:5432", "localhost:5432")
        # Convert async URL to sync for Alembic
        return database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def main() -> None:
    """Create migration with proper database URL handling."""
    parser = argparse.ArgumentParser(description="Create Alembic migration")
    parser.add_argument(
        "--message", "-m",
        required=True,
        help="Migration message"
    )
    parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="Auto-generate migration from model changes"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost instead of docker hostname"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = get_database_url(args.local)
    
    # Set environment variable for Alembic
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    
    print(f"Using database URL: {database_url}")
    
    # Build alembic command
    cmd_parts = ["uv", "run", "alembic", "revision"]
    
    if args.autogenerate:
        cmd_parts.append("--autogenerate")
    
    cmd_parts.extend(["-m", args.message])
    
    print(f"Running: {' '.join(cmd_parts)}")
    result = subprocess.run(cmd_parts)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
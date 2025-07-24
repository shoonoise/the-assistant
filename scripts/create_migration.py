#!/usr/bin/env python3
"""
Create Alembic migration with proper database connection handling.
"""

import argparse
import os
import sys
from pathlib import Path
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from the_assistant.settings import get_settings


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
    
    # Get database URL and adjust for local development
    settings = get_settings()
    database_url = settings.database_url
    
    if args.local:
        # Replace docker hostname with localhost for local development
        database_url = database_url.replace("postgresql:5432", "localhost:5432")
    
    # Convert async URL to sync for Alembic
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Set environment variable for Alembic
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    
    # Build alembic command
    cmd_parts = ["uv", "run", "alembic", "revision"]
    
    if args.autogenerate:
        cmd_parts.append("--autogenerate")
    
    cmd_parts.extend(["-m", args.message])
    
    result = subprocess.run(cmd_parts)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Comprehensive migration management script for The Assistant.
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


def run_alembic_command(cmd_parts: list[str], database_url: str) -> int:
    """Run an alembic command with proper environment setup."""
    # Set environment variable for Alembic
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = database_url
    
    print(f"Using database URL: {database_url}")
    print(f"Running: {' '.join(cmd_parts)}")
    
    result = subprocess.run(cmd_parts, env=env)
    return result.returncode


def create_migration(message: str, autogenerate: bool, local: bool) -> int:
    """Create a new migration."""
    database_url = get_database_url(local)
    
    cmd_parts = ["uv", "run", "alembic", "revision"]
    if autogenerate:
        cmd_parts.append("--autogenerate")
    cmd_parts.extend(["-m", message])
    
    return run_alembic_command(cmd_parts, database_url)


def apply_migrations(target: str, local: bool) -> int:
    """Apply migrations to target revision."""
    database_url = get_database_url(local)
    cmd_parts = ["uv", "run", "alembic", "upgrade", target]
    return run_alembic_command(cmd_parts, database_url)


def show_current(local: bool) -> int:
    """Show current migration version."""
    database_url = get_database_url(local)
    cmd_parts = ["uv", "run", "alembic", "current"]
    return run_alembic_command(cmd_parts, database_url)


def show_history(local: bool) -> int:
    """Show migration history."""
    database_url = get_database_url(local)
    cmd_parts = ["uv", "run", "alembic", "history"]
    return run_alembic_command(cmd_parts, database_url)


def downgrade_migration(target: str, local: bool) -> int:
    """Downgrade to target revision."""
    database_url = get_database_url(local)
    cmd_parts = ["uv", "run", "alembic", "downgrade", target]
    return run_alembic_command(cmd_parts, database_url)


def main() -> None:
    """Main migration management interface."""
    parser = argparse.ArgumentParser(
        description="Manage database migrations for The Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new migration with auto-detection
  python scripts/manage_migrations.py create --message "add_user_preferences" --autogenerate --local
  
  # Apply all pending migrations
  python scripts/manage_migrations.py apply --local
  
  # Show current migration status
  python scripts/manage_migrations.py current --local
  
  # Show migration history
  python scripts/manage_migrations.py history --local
  
  # Downgrade one migration
  python scripts/manage_migrations.py downgrade -1 --local
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create migration
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument(
        "--message", "-m",
        required=True,
        help="Migration message"
    )
    create_parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="Auto-generate migration from model changes"
    )
    create_parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost instead of docker hostname"
    )
    
    # Apply migrations
    apply_parser = subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument(
        "--target", "-t",
        default="head",
        help="Target revision (default: head)"
    )
    apply_parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost instead of docker hostname"
    )
    
    # Show current
    current_parser = subparsers.add_parser("current", help="Show current migration version")
    current_parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost instead of docker hostname"
    )
    
    # Show history
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost instead of docker hostname"
    )
    
    # Downgrade
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade migrations")
    downgrade_parser.add_argument(
        "target",
        help="Target revision (e.g., -1 for one step back, revision_id for specific)"
    )
    downgrade_parser.add_argument(
        "--local",
        action="store_true",
        help="Use localhost instead of docker hostname"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute the appropriate command
    if args.command == "create":
        exit_code = create_migration(args.message, args.autogenerate, args.local)
    elif args.command == "apply":
        exit_code = apply_migrations(args.target, args.local)
    elif args.command == "current":
        exit_code = show_current(args.local)
    elif args.command == "history":
        exit_code = show_history(args.local)
    elif args.command == "downgrade":
        exit_code = downgrade_migration(args.target, args.local)
    else:
        parser.print_help()
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
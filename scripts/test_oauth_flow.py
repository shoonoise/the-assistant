#!/usr/bin/env python3
"""
Test script for Google OAuth2 flow.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cryptography.fernet import Fernet
from the_assistant.integrations.google.credential_store import PostgresCredentialStore
from the_assistant.integrations.google.client import GoogleClient

logger = logging.getLogger(__name__)


async def test_credential_store():
    """Test credential store operations."""
    print("Testing credential store...")
    
    # Get configuration
    database_url = os.getenv(
        "DATABASE_URL", 
        "postgresql://temporal:temporal@localhost:5432/the_assistant"
    )
    encryption_key = os.getenv("DB_ENCRYPTION_KEY")
    if not encryption_key:
        raise SystemExit("DB_ENCRYPTION_KEY is required")
    
    # Create store
    store = PostgresCredentialStore(database_url, encryption_key)
    
    # Test user ID (from our seeded data)
    user_id = 1
    
    # Test get (should be None initially)
    creds = await store.get(user_id)
    print(f"Initial credentials: {creds}")
    
    print("Credential store test completed!")


async def test_google_client():
    """Test Google client operations."""
    print("Testing Google client...")
    
    client = GoogleClient(
        user_id=1
    )
    
    # Test authentication status
    is_authenticated = await client.is_authenticated()
    print(f"User authenticated: {is_authenticated}")
    
    # Test auth URL generation
    try:
        auth_url = await client.generate_auth_url("http://localhost:9000/google/oauth2callback")
        print(f"Auth URL generated: {auth_url[:100]}...")
    except Exception as e:
        print(f"Failed to generate auth URL: {e}")
    
    print("Google client test completed!")


async def main():
    """Run all tests."""
    logging.basicConfig(level=logging.INFO)
    
    print("Starting OAuth2 flow tests...")
    
    await test_credential_store()
    await test_google_client()
    
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 
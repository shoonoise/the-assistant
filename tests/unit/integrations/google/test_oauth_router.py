import importlib
import os
from unittest.mock import patch


def test_missing_jwt_secret_no_error():
    """Importing oauth_router without JWT_SECRET should not fail."""
    with patch.dict(os.environ, {}, clear=True):
        import the_assistant.integrations.google.oauth_router as oauth_router

        importlib.reload(oauth_router)

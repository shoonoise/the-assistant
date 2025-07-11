import importlib
import os
from unittest.mock import patch

import pytest


def test_missing_jwt_secret_raises_error():
    """Importing oauth_router without JWT_SECRET should raise RuntimeError."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(
            RuntimeError, match="JWT_SECRET environment variable not set"
        ):
            import the_assistant.integrations.google.oauth_router as oauth_router

            importlib.reload(oauth_router)

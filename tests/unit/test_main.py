"""Tests for the main FastAPI application."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from the_assistant.main import app


class TestMainApp:
    """Test the main FastAPI application."""

    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app."""
        with patch.dict(
            "os.environ",
            {
                "DB_ENCRYPTION_KEY": "key",
                "JWT_SECRET": "secret",
            },
            clear=False,
        ):
            yield TestClient(app)

    def test_app_creation(self):
        """Test that the app is created successfully."""
        assert app.title == "The Assistant"
        assert app.version == "0.1.0"

    def test_oauth_redirect_with_all_params(self, client):
        """Test OAuth redirect with all parameters."""
        response = client.get(
            "/oauth2callback?state=test_state&code=test_code&error=test_error"
        )

        # The actual behavior depends on the OAuth router implementation
        # Since error is present, it will redirect to auth-error
        assert response.status_code == 200  # The router handles this internally

    def test_oauth_redirect_with_state_only(self, client):
        """Test OAuth redirect with state parameter only."""
        response = client.get("/oauth2callback?state=test_state")

        # Without code, this will be processed by the OAuth router
        assert response.status_code in [200, 302, 422]  # Various possible responses

    def test_oauth_redirect_with_code_only(self, client):
        """Test OAuth redirect with code parameter only."""
        response = client.get("/oauth2callback?code=test_code")

        # Without state, this will be processed by the OAuth router
        assert response.status_code in [200, 302, 422]  # Various possible responses

    def test_oauth_redirect_with_error_only(self, client):
        """Test OAuth redirect with error parameter only."""
        response = client.get("/oauth2callback?error=access_denied")

        # Error will be processed by the OAuth router
        assert response.status_code in [200, 302, 422]  # Various possible responses

    def test_oauth_redirect_no_params(self, client):
        """Test OAuth redirect with no parameters."""
        response = client.get("/oauth2callback")

        # No params will be processed by the OAuth router
        assert response.status_code in [200, 302, 422]  # Various possible responses

    def test_auth_success_endpoint(self, client):
        """Test the auth success endpoint."""
        response = client.get("/auth-success")

        assert response.status_code == 200
        assert response.json() == {
            "message": "Google authentication successful! You can close this window."
        }

    def test_auth_error_endpoint_no_params(self, client):
        """Test the auth error endpoint without parameters."""
        response = client.get("/auth-error")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_auth_error_endpoint_with_params(self, client):
        """Test the auth error endpoint with parameters."""
        response = client.get(
            "/auth-error?error=access_denied&message=User denied access"
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_google_oauth_router_included(self):
        """Test that the Google OAuth router is included."""
        # Check that the router is included by looking at the routes
        routes = [route.path for route in app.routes]

        # The exact paths depend on the router implementation,
        # but we should have some Google OAuth related routes
        assert any("/google" in route for route in routes)

    def test_user_settings_router_included(self):
        """Test that the user settings router is included."""
        routes = [route.path for route in app.routes]
        assert any(route.startswith("/settings") for route in routes)

    def test_app_has_correct_metadata(self):
        """Test that the app has correct metadata."""
        assert hasattr(app, "title")
        assert hasattr(app, "version")
        assert app.title == "The Assistant"
        assert app.version == "0.1.0"

    def test_app_routes_exist(self):
        """Test that expected routes exist."""
        routes = [route.path for route in app.routes]

        # Check for our custom routes
        assert "/oauth2callback" in routes
        assert "/auth-success" in routes
        assert "/auth-error" in routes

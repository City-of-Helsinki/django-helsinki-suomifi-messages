import pytest

from suomifi_messages.errors import SuomiFiAPIError, SuomiFiClientError


class TestSuomiFiClientLogin:
    """Test SuomiFiClient login functionality."""

    def test_login_success(self, client, requests_mock):
        """Test successful login uses Django settings and parses the response."""
        requests_mock.post(
            client.url("v1/token"),
            json={
                "access_token": "test_token_123",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
            status_code=200,
        )

        client.login()

        assert requests_mock.last_request.json() == {
            "username": "suomifi_username",
            "password": "suomifi_password",
        }
        assert client.token == "test_token_123"
        assert client.token_expiry == 3600
        assert client.token_type == "Bearer"
        assert client.session.headers["Authorization"] == "test_token_123"
        assert client.session.headers["Host"] == client.hostname

    def test_login_with_explicit_credentials(self, client, requests_mock):
        """Test login with explicitly provided credentials."""
        requests_mock.post(
            client.url("v1/token"),
            json={
                "access_token": "custom_token",
                "expires_in": 7200,
                "token_type": "Bearer",
            },
            status_code=200,
        )

        client.login(username="custom_user", password="custom_pass")

        assert requests_mock.last_request.json() == {
            "username": "custom_user",
            "password": "custom_pass",
        }
        assert client.token == "custom_token"

    def test_login_failure_non_200_status(self, client, requests_mock):
        """Test login failure with non-200 status code."""
        requests_mock.post(
            client.url("v1/token"),
            json={"error": "Invalid credentials"},
            status_code=401,
        )

        with pytest.raises(SuomiFiAPIError, match="Authentication failed"):
            client.login()


class TestSuomiFiClientChangePassword:
    """Test SuomiFiClient password change functionality."""

    def test_change_password_success(self, client, requests_mock):
        """Test successful password change clears token state."""
        client.token = "existing_token"
        client.token_expiry = 3600
        client.token_type = "Bearer"
        client.session.headers["Authorization"] = "existing_token"
        requests_mock.post(
            client.url("v1/change-password"),
            json={},
            status_code=200,
        )

        client.change_password("old_pass", "new_pass")

        assert requests_mock.last_request.json() == {
            "currentPassword": "old_pass",
            "newPassword": "new_pass",
            "accessToken": "existing_token",
        }
        assert "Authorization" not in requests_mock.last_request.headers
        assert client.token is None
        assert client.token_expiry is None
        assert client.token_type is None
        assert "Authorization" not in client.session.headers

    def test_change_password_failure(self, client, requests_mock):
        """Test password change failure."""
        client.token = "existing_token"
        requests_mock.post(
            client.url("v1/change-password"),
            json={"error": "Invalid current password"},
            status_code=400,
        )

        with pytest.raises(SuomiFiClientError, match="Password change failed"):
            client.change_password("wrong_pass", "new_pass")

    def test_change_password_without_login(self, client):
        """Test that change_password raises ValueError if not logged in."""
        with pytest.raises(ValueError, match="login"):
            client.change_password("old_pass", "new_pass")

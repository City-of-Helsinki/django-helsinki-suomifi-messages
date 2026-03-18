import pytest
import requests

from suomifi_messages.client import (
    SUOMIFI_BASE_URL,
    SUOMIFI_QA_BASE_URL,
    SuomiFiClient,
)
from suomifi_messages.errors import (
    SuomiFiAPIError,
    SuomiFiClientError,
    SuomiFiDuplicateMessageError,
    SuomiFiServerError,
)


class TestSuomiFiClientInit:
    """Test SuomiFiClient initialization and basic utilities."""

    @pytest.mark.parametrize(
        "env_type,expected_url",
        [
            ("qa", SUOMIFI_QA_BASE_URL),
            ("prod", SUOMIFI_BASE_URL),
        ],
    )
    def test_init_environment(self, env_type, expected_url):
        """Test client initialization with different environments."""
        client = SuomiFiClient(type=env_type)

        assert client.base_url == expected_url
        assert isinstance(client.session, requests.Session)

    def test_init_default_is_qa(self):
        """Test that default environment is QA."""
        client = SuomiFiClient()

        assert client.base_url == SUOMIFI_QA_BASE_URL

    def test_init_invalid_type_raises_error(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(
            TypeError, match='Invalid type. Allowed values are "prod" and "qa"'
        ):
            SuomiFiClient(type="invalid")  # type: ignore[arg-type]

    def test_hostname_property(self, client):
        """Test hostname property extracts hostname from URL."""
        assert client.hostname == "foo-bar.baz.test"

    @pytest.mark.parametrize("path", ["/v1/endpoint", "v1/endpoint"])
    @pytest.mark.parametrize("base_url", ["https://foo.bar/", "https://foo.bar"])
    def test_url_method(self, path, base_url):
        """Test url method handles paths with and without leading slash."""
        client = SuomiFiClient()
        client.base_url = base_url

        url = client.url(path)

        assert url == "https://foo.bar/v1/endpoint"


class TestRaiseForStatus:
    """Test SuomiFiClient._raise_for_status error routing."""

    def test_409_raises_duplicate_message_error_with_message_id(
        self, client, make_response
    ):
        """Test that 409 with messageId raises SuomiFiDuplicateMessageError."""
        response = make_response(409, {"messageId": 12345})

        with pytest.raises(SuomiFiDuplicateMessageError) as exc_info:
            client._raise_for_status(response, "Test error")

        assert exc_info.value.message_id == 12345

    def test_409_raises_duplicate_message_error_without_message_id(
        self, client, make_response
    ):
        """Test that 409 without messageId raises SuomiFiDuplicateMessageError."""
        response = make_response(409, {"error": "conflict"})

        with pytest.raises(SuomiFiDuplicateMessageError) as exc_info:
            client._raise_for_status(response, "Test error")

        assert exc_info.value.message_id is None

    def test_4xx_raises_client_error(self, client, make_response):
        """Test that 4xx (non-409) raises SuomiFiClientError."""
        response = make_response(400, {"error": "bad request"})

        with pytest.raises(SuomiFiClientError):
            client._raise_for_status(response, "Test error")

    def test_5xx_raises_server_error(self, client, make_response):
        """Test that 5xx raises SuomiFiServerError."""
        response = make_response(500, {"error": "server error"})

        with pytest.raises(SuomiFiServerError):
            client._raise_for_status(response, "Test error")

    def test_2xx_does_not_raise(self, client, make_response):
        """Test that 2xx responses do not raise."""
        response = make_response(200, {"ok": True})

        client._raise_for_status(response, "Test error")  # should not raise

    def test_3xx_raises_api_error(self, client, make_response):
        """Test that 3xx (and other non-2xx outside 4xx/5xx) raises SuomiFiAPIError."""
        response = make_response(302, {})

        with pytest.raises(SuomiFiAPIError):
            client._raise_for_status(response, "Test error")


class TestSuomiFiClientRequests:
    """Test SuomiFiClient request methods."""

    def test_request_method(self, client, requests_mock):
        """Test generic request method."""
        requests_mock.get(client.url("v1/test"), json={"status": "ok"})

        response = client.request("GET", "/v1/test")

        assert response.json() == {"status": "ok"}

    def test_get_method(self, client, requests_mock):
        """Test GET request method."""
        requests_mock.get(client.url("v1/test"), json={"status": "ok"})

        response = client.get("/v1/test")

        assert response.json() == {"status": "ok"}

    def test_get_method_with_params(self, client, requests_mock):
        """Test GET request with query parameters."""
        requests_mock.get(
            client.url("v1/test"),
            json={"status": "ok"},
        )

        response = client.get("/v1/test", params={"key": "value"})

        assert response.json() == {"status": "ok"}
        assert "key=value" in requests_mock.last_request.url

    def test_post_method(self, client, requests_mock):
        """Test POST request method."""
        requests_mock.post(client.url("v1/test"), json={"status": "created"})

        response = client.post("/v1/test", json={"data": "test"})

        assert response.json() == {"status": "created"}

    def test_post_method_with_data(self, client, requests_mock):
        """Test POST request with form data."""
        requests_mock.post(client.url("v1/test"), json={"status": "created"})

        response = client.post("/v1/test", data={"key": "value"})

        assert response.json() == {"status": "created"}

import uuid
from unittest.mock import Mock

import pytest
import requests

from suomifi_messages.client import (
    SUOMIFI_BASE_URL,
    SUOMIFI_QA_BASE_URL,
    SuomiFiClient,
)
from suomifi_messages.errors import SuomiFiError


@pytest.fixture
def client():
    client = SuomiFiClient()
    client.base_url = "https://foo-bar.baz.test/"
    return client


class TestSuomiFiClientInit:
    """Test SuomiFiClient initialization."""

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
            SuomiFiClient(type="invalid")


class TestSuomiFiClientProperties:
    """Test SuomiFiClient properties."""

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


class TestSuomiFiClientLogin:
    """Test SuomiFiClient login functionality."""

    @pytest.fixture
    def mock_settings(self, settings):
        """Configure Django settings for tests."""
        settings.SUOMIFI_USERNAME = "test_user"
        settings.SUOMIFI_PASSWORD = "test_pass"
        return settings

    @pytest.mark.usefixtures("mock_settings")
    def test_login_success(self, client, requests_mock):
        """Test successful login."""
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

    @pytest.mark.usefixtures("mock_settings")
    def test_login_failure_non_200_status(self, client, requests_mock):
        """Test login failure with non-200 status code."""
        requests_mock.post(
            client.url("v1/token"),
            json={"error": "Invalid credentials"},
            status_code=401,
        )

        with pytest.raises(requests.HTTPError):
            client.login()

    @pytest.mark.usefixtures("mock_settings")
    def test_login_uses_settings_by_default(self, client, requests_mock):
        """Test that login uses Django settings by default."""
        requests_mock.post(
            client.url("v1/token"),
            json={
                "access_token": "token",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
            status_code=200,
        )

        client.login()

        assert requests_mock.last_request.json() == {
            "username": "test_user",
            "password": "test_pass",
        }


class TestSuomiFiClientChangePassword:
    """Test SuomiFiClient password change functionality."""

    def test_change_password_success(self, client, requests_mock):
        """Test successful password change."""
        client.token = "existing_token"
        requests_mock.post(
            client.url("v1/change-password"),
            json={"status": "Password changed successfully"},
            status_code=200,
        )

        result = client.change_password("old_pass", "new_pass")

        assert result == {"status": "Password changed successfully"}
        assert requests_mock.last_request.json() == {
            "currentPassword": "old_pass",
            "newPassword": "new_pass",
            "accessToken": "existing_token",
        }

    def test_change_password_failure(self, client, requests_mock):
        """Test password change failure."""
        client.token = "existing_token"
        requests_mock.post(
            client.url("v1/change-password"),
            json={"error": "Invalid current password"},
            status_code=400,
        )

        with pytest.raises(SuomiFiError, match="Password change request failed"):
            client.change_password("wrong_pass", "new_pass")


class TestSuomiFiClientCheckMailboxes:
    """Test SuomiFiClient mailbox checking functionality."""

    def test_check_mailboxes_success(self, client, requests_mock):
        """Test successful mailbox check."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={
                "activeMailboxes": [
                    {"id": "123456-789A", "active": True},
                    {"id": "987654-321B", "active": False},
                ]
            },
            status_code=200,
        )

        result = client.check_mailboxes(["123456-789A", "987654-321B"])

        assert "activeMailboxes" in result
        assert len(result["activeMailboxes"]) == 2
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": "123456-789A"}, {"id": "987654-321B"}]
        }

    def test_check_mailboxes_empty_list(self, client, requests_mock):
        """Test mailbox check with empty list."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"activeMailboxes": []},
            status_code=200,
        )

        result = client.check_mailboxes([])

        assert result == {"activeMailboxes": []}


@pytest.mark.usefixtures("mock_settings")
class TestSuomiFiClientSendMessage:
    """Test SuomiFiClient message sending functionality."""

    @pytest.fixture
    def mock_settings(self, settings):
        """Configure Django settings for tests."""
        settings.SUOMIFI_SERVICE_ID = "test_service_123"
        settings.SUOMIFI_TEST_USER_SSN = "123456-789A"
        return settings

    def test_send_electronic_message_success(self, client, requests_mock):
        """Test sending electronic message successfully."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Test Message",
            body="Test body content",
            delivery_format="electronic",
        )

        # Verify output
        assert result == {"messageId": "msg_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert request_json["electronic"]["title"] == "Test Message"
        assert request_json["electronic"]["body"] == "Test body content"
        assert request_json["sender"]["serviceId"] == "test_service_123"
        assert request_json["recipient"]["id"] == "123456-789A"

    def test_send_message_with_reply_to(self, client, requests_mock):
        """Test sending message as reply to another message."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_reply_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Reply Message",
            body="This is a reply",
            reply_to="original_msg_456",
        )

        # Verify output
        assert result == {"messageId": "msg_reply_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert request_json["electronic"]["inReplyToMessageId"] == "original_msg_456"

    @pytest.mark.parametrize(
        "verifiable,expected_type",
        [
            (True, "Verifiable"),
            (False, "Normal"),
        ],
    )
    def test_send_message_verifiable(
        self, verifiable, expected_type, client, requests_mock
    ):
        """Test sending message with verifiable flag."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Test Message",
            body="Test body",
            verifiable=verifiable,
        )

        # Verify output
        assert result == {"messageId": "msg_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert request_json["electronic"]["messageServiceType"] == expected_type

    @pytest.mark.parametrize(
        "reply_allowed,expected_value",
        [
            (True, "Anyone"),
            (False, "No one"),
        ],
    )
    def test_send_message_reply_allowed(
        self, client, reply_allowed, expected_value, requests_mock
    ):
        """Test sending message with reply_allowed flag."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Test Message",
            body="Test body",
            reply_allowed=reply_allowed,
        )

        # Verify output
        assert result == {"messageId": "msg_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert request_json["electronic"]["replyAllowedBy"] == expected_value

    def test_send_electronic_only_message(self, client, requests_mock):
        """Test sending electronic-only message."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Electronic Message",
            body="Electronic content",
            delivery_format="electronic",
        )

        # Verify output
        assert result == {"messageId": "msg_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert "electronic" in request_json
        assert "paperMail" not in request_json

    def test_send_postal_message(self, client, requests_mock):
        """Test sending postal message."""
        requests_mock.post(
            client.url("v1/messages"),
            json={"messageId": "msg_postal_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Postal Message",
            body="Postal content",
            delivery_format="postal",
        )

        # Verify output
        assert result == {"messageId": "msg_postal_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert "electronic" in request_json
        assert "paperMail" in request_json

    def test_send_message_both_formats(self, client, requests_mock):
        """Test sending message in both electronic and postal formats."""
        requests_mock.post(
            client.url("v1/messages"),
            json={"messageId": "msg_both_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Dual Format Message",
            body="Both formats content",
            delivery_format="both",
        )

        # Verify output
        assert result == {"messageId": "msg_both_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert "electronic" in request_json
        assert "paperMail" in request_json

    def test_send_message_with_custom_ids(self, client, requests_mock):
        """Test sending message with custom service and recipient IDs."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_custom_123"},
            status_code=200,
        )
        custom_internal_id = str(uuid.uuid4())

        result = client.send_message(
            title="Custom IDs Message",
            body="Custom IDs test",
            service_id="custom_service_456",
            recipient_id="custom_recipient_789",
            internal_id=custom_internal_id,
        )

        # Verify output
        assert result == {"messageId": "msg_custom_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        assert request_json["sender"]["serviceId"] == "custom_service_456"
        assert request_json["recipient"]["id"] == "custom_recipient_789"
        assert request_json["externalId"] == custom_internal_id

    def test_send_message_invalid_delivery_format(self, client):
        """Test that invalid delivery format raises ValueError."""
        with pytest.raises(
            ValueError, match='Parameter "delivery_format" must be one of'
        ):
            client.send_message(
                title="Test",
                body="Test",
                delivery_format="invalid",
            )

    def test_send_message_failure(self, client, requests_mock):
        """Test message send failure."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"error": "Invalid message format"},
            status_code=400,
        )

        with pytest.raises(Exception, match="Message send request failed"):
            client.send_message(title="Test", body="Test")

    def test_send_message_with_attachment_ids(self, client, requests_mock):
        """Test sending message with attachment IDs."""
        requests_mock.post(
            client.url("v1/messages/electronic"),
            json={"messageId": "msg_123"},
            status_code=200,
        )

        result = client.send_message(
            title="Message with attachments",
            body="Body",
            attachment_ids=["att_1", "att_2"],
        )

        # Verify output
        assert result == {"messageId": "msg_123"}
        # Verify API contract
        request_json = requests_mock.last_request.json()
        # Note: In the implementation, attachments is set to empty list
        assert request_json["electronic"]["attachments"] == []


class TestSuomiFiClientGetEvents:
    """Test SuomiFiClient event retrieval functionality."""

    def test_get_events_without_continuation(self, client, requests_mock):
        """Test getting events without continuation token."""
        requests_mock.get(
            client.url("v2/events"),
            json={
                "events": [{"id": "event_1"}, {"id": "event_2"}],
                "continuationToken": "next_token_123",
            },
            status_code=200,
        )

        result = client.get_events()

        assert "events" in result
        assert len(result["events"]) == 2
        assert result["continuationToken"] == "next_token_123"

    def test_get_events_with_continuation(self, client, requests_mock):
        """Test getting events with continuation token."""
        requests_mock.get(
            client.url("v2/events"),
            json={
                "events": [{"id": "event_3"}],
                "continuationToken": None,
            },
            status_code=200,
        )

        result = client.get_events(continuation="existing_token_456")

        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["id"] == "event_3"
        assert result["continuationToken"] is None

    def test_get_events_raises_on_error(self, client, requests_mock):
        """Test that get_events raises on HTTP error."""
        requests_mock.get(
            client.url("v2/events"),
            status_code=500,
        )

        with pytest.raises(requests.HTTPError):
            client.get_events()


class TestSuomiFiClientGetMessage:
    """Test SuomiFiClient message retrieval functionality."""

    def test_get_message_success(self, client, requests_mock):
        """Test successful message retrieval."""
        requests_mock.get(
            client.url("v1/messages/msg_123"),
            json={
                "messageId": "msg_123",
                "title": "Test Message",
                "body": "Message content",
            },
            status_code=200,
        )

        result = client.get_message("msg_123")

        assert result["messageId"] == "msg_123"
        assert result["title"] == "Test Message"

    def test_get_message_raises_on_error(self, client, requests_mock):
        """Test that get_message raises on HTTP error."""
        requests_mock.get(
            client.url("v1/messages/nonexistent"),
            status_code=404,
        )

        with pytest.raises(requests.HTTPError):
            client.get_message("nonexistent")


class TestSuomiFiClientGetMessageState:
    """Test SuomiFiClient message state retrieval functionality."""

    def test_get_message_state_success(self, client, requests_mock):
        """Test successful message state retrieval."""
        requests_mock.get(
            client.url("v1/messages/msg_123/state"),
            json={
                "messageId": "msg_123",
                "state": "delivered",
                "timestamp": "2026-02-13T10:00:00Z",
            },
            status_code=200,
        )

        result = client.get_message_state("msg_123")

        assert result["messageId"] == "msg_123"
        assert result["state"] == "delivered"

    def test_get_message_state_raises_on_error(self, client, requests_mock):
        """Test that get_message_state raises on HTTP error."""
        requests_mock.get(
            client.url("v1/messages/nonexistent/state"),
            status_code=404,
        )

        with pytest.raises(requests.HTTPError):
            client.get_message_state("nonexistent")


class TestSuomiFiClientGetAttachment:
    """Test SuomiFiClient attachment retrieval functionality."""

    def test_get_attachment_success(self, client, requests_mock):
        """Test successful attachment retrieval."""
        requests_mock.get(
            client.url("v1/attachments/att_123"),
            content=b"Binary attachment content",
            status_code=200,
        )

        result = client.get_attachment("att_123")

        assert result.content == b"Binary attachment content"
        assert result.status_code == 200

    def test_get_attachment_raises_on_error(self, client, requests_mock):
        """Test that get_attachment raises on HTTP error."""
        requests_mock.get(
            client.url("v1/attachments/nonexistent"),
            status_code=404,
        )

        with pytest.raises(requests.HTTPError):
            client.get_attachment("nonexistent")


class TestSuomiFiClientAddAttachment:
    """Test SuomiFiClient attachment upload functionality."""

    def test_add_attachment_not_implemented(self, client):
        """Test that add_attachment raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            client.add_attachment(Mock())


class TestSuomiFiError:
    """Test SuomiFiError exception."""

    def test_suomifi_error_is_exception(self):
        """Test that SuomiFiError is an Exception."""
        error = SuomiFiError("Test error")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"

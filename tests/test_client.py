import uuid
from datetime import datetime

import pytest
import requests

from suomifi_messages.client import (
    SUOMIFI_BASE_URL,
    SUOMIFI_QA_BASE_URL,
    SuomiFiClient,
)
from suomifi_messages.errors import SuomiFiAPIError, SuomiFiError
from suomifi_messages.schemas import (
    Address,
    AttachmentReference,
    BodyFormat,
    ElectronicPart,
    Event,
    EventMetadata,
    EventType,
    MessageNotifications,
    MessageSender,
    MessageSenderActor,
    MessageServiceType,
    MessageThread,
    NewPaperMailRecipient,
    NewPaperMailSender,
    PaperMailPart,
    PostiMessaging,
    PrintingAndEnvelopingService,
    ReceivedAttachment,
    ReceivedElectronicMessage,
    ReceivedMessage,
    ReminderType,
    ReplyAllowedBy,
    SenderDetailsInNotifications,
    UnreadMessageNotification,
    Visibility,
)


@pytest.fixture
def client():
    client = SuomiFiClient()
    client.base_url = "https://foo-bar.baz.test/"
    return client


@pytest.fixture
def recipient_address():
    """Standard recipient address for testing."""
    return Address(
        name="Matti Meikäläinen",
        street_address="Esimerkkikatu 1",
        zip_code="00100",
        city="Helsinki",
        country_code="FI",
    )


@pytest.fixture
def sender_address():
    """Standard sender address for testing."""
    return Address(
        name="Helsingin kaupunki",
        street_address="Lähettäjänkatu 1",
        zip_code="00100",
        city="Helsinki",
        country_code="FI",
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

        with pytest.raises(SuomiFiAPIError, match="Password change failed"):
            client.change_password("wrong_pass", "new_pass")


class TestSuomiFiClientCheckMailboxes:
    """Test SuomiFiClient mailbox checking functionality."""

    @pytest.mark.parametrize(
        "input_ids,expected_result",
        [
            # Some recipients have active mailboxes
            (
                ["123456-789A", "987654-321B", "111111-222C"],
                ["123456-789A", "987654-321B"],
            ),
            # All recipients have active mailboxes
            (["123456-789A", "987654-321B"], ["123456-789A", "987654-321B"]),
            # No recipients have active mailboxes
            (["123456-789A", "987654-321B"], []),
            # Single recipient with active mailbox
            (["123456-789A"], ["123456-789A"]),
            # Empty input list
            ([], []),
        ],
    )
    def test_check_mailboxes_responses(
        self, client, requests_mock, input_ids, expected_result
    ):
        """Test mailbox check with various response scenarios."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"endUsersWithActiveMailbox": [{"id": id} for id in expected_result]},
            status_code=200,
        )

        result = client.check_mailboxes(input_ids)

        assert result == expected_result
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": id} for id in input_ids]
        }

    def test_check_mailboxes_error(self, client, requests_mock):
        """Test mailbox check request failure raises SuomiFiAPIError."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"reason": "Bad request"},
            status_code=400,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to check mailbox status"):
            client.check_mailboxes(["123456-789A"])


class TestSuomiFiClientCheckMailbox:
    """Test SuomiFiClient single mailbox checking functionality."""

    def test_check_mailbox_active(self, client, requests_mock):
        """Test checking mailbox that is active returns True."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"endUsersWithActiveMailbox": [{"id": "123456-789A"}]},
            status_code=200,
        )

        result = client.check_mailbox("123456-789A")

        assert result is True
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": "123456-789A"}]
        }

    def test_check_mailbox_inactive(self, client, requests_mock):
        """Test checking mailbox that is inactive returns False."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"endUsersWithActiveMailbox": []},
            status_code=200,
        )

        result = client.check_mailbox("987654-321B")

        assert result is False
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": "987654-321B"}]
        }

    def test_check_mailbox_error(self, client, requests_mock):
        """Test single mailbox check request failure raises SuomiFiAPIError."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"reason": "Bad request"},
            status_code=400,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to check mailbox status"):
            client.check_mailbox("123456-789A")


class TestSuomiFiClientSendElectronicMessage:
    """Test SuomiFiClient electronic message sending functionality."""

    def test_send_electronic_message_success(self, client, requests_mock, mocker):
        """Test sending electronic message successfully."""
        # Mock builder to return simple structure for assertion
        mock_electronic = {"title": "Test", "body": "Content"}

        mocker.patch.object(
            client, "build_electronic_message", return_value=mock_electronic
        )

        requests_mock.post(
            client.url("v2/messages/electronic"),
            json={"messageId": 12345},
            status_code=200,
        )

        result = client.send_electronic_message(
            title="Test Message",
            body="Test body content",
            body_format=BodyFormat.TEXT,
            recipient_id="123456-789A",
        )

        # Verify complete request structure
        request_json = requests_mock.last_request.json()
        assert request_json == {
            "electronic": mock_electronic,
            "sender": {"serviceId": "suomifi_service_id"},
            "recipient": {"id": "123456-789A"},
            "externalId": request_json["externalId"],  # UUID, generated
        }

        # Verify output
        message_id, external_id = result
        assert message_id == 12345
        assert external_id == request_json["externalId"]

    def test_send_electronic_message_with_custom_ids(self, client, requests_mock):
        """Test sending electronic message with custom service and recipient IDs."""
        requests_mock.post(
            client.url("v2/messages/electronic"),
            json={"messageId": 12345},
            status_code=200,
        )
        custom_external_id = str(uuid.uuid4())

        result = client.send_electronic_message(
            title="Custom IDs Message",
            body="Custom IDs test",
            body_format=BodyFormat.TEXT,
            service_id="custom_service_456",
            recipient_id="custom_recipient_789",
            external_id=custom_external_id,
        )

        message_id, external_id = result
        assert message_id == 12345
        assert external_id == custom_external_id
        request_json = requests_mock.last_request.json()
        assert request_json["sender"]["serviceId"] == "custom_service_456"
        assert request_json["recipient"]["id"] == "custom_recipient_789"
        assert request_json["externalId"] == custom_external_id

    def test_send_electronic_message_failure(self, client, requests_mock):
        """Test electronic message send failure."""
        requests_mock.post(
            client.url("v2/messages/electronic"),
            json={"error": "Invalid message format"},
            status_code=400,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to send electronic message"):
            client.send_electronic_message(
                title="Test",
                body="Test",
                body_format=BodyFormat.TEXT,
                recipient_id="123456-789A",
            )

    def test_send_electronic_message_missing_service_id(self, settings):
        """Test that ValueError is raised when service_id is missing."""
        settings.SUOMIFI_SERVICE_ID = ""

        client = SuomiFiClient()
        client.base_url = "https://foo-bar.baz.test/"

        with pytest.raises(ValueError, match="Suomi.fi service_id is not configured."):
            client.send_electronic_message(
                title="Test",
                body="Test",
                body_format=BodyFormat.TEXT,
                recipient_id="123456-789A",
            )


class TestSuomiFiClientSendMultichannelMessage:
    """Test SuomiFiClient multichannel message sending functionality."""

    def test_send_multichannel_message_success(
        self, client, requests_mock, recipient_address, sender_address, mocker
    ):
        """Test sending multichannel message successfully."""
        # Mock builders to return simple structures for assertion
        mock_electronic = {"title": "Test", "body": "Content"}
        mock_paper = {"attachments": [{"attachmentId": "att_1"}]}

        mocker.patch.object(
            client, "build_electronic_message", return_value=mock_electronic
        )
        mocker.patch.object(client, "build_paper_mail_message", return_value=mock_paper)

        requests_mock.post(
            client.url("v2/messages"),
            json={"messageId": 12345},
            status_code=200,
        )

        result = client.send_multichannel_message(
            title="Test Message",
            body="Test body content",
            body_format=BodyFormat.TEXT,
            recipient_id="123456-789A",
            recipient_address=recipient_address,
            sender_address=sender_address,
            paper_mail_attachment_id="att_paper_1",
        )

        # Verify complete request structure
        request_json = requests_mock.last_request.json()
        assert request_json == {
            "electronic": mock_electronic,
            "paperMail": mock_paper,
            "sender": {"serviceId": "suomifi_service_id"},
            "recipient": {"id": "123456-789A"},
            "externalId": request_json["externalId"],  # UUID, generated
        }

        # Verify output
        message_id, external_id = result
        assert message_id == 12345
        assert external_id == request_json["externalId"]

    def test_send_multichannel_message_with_custom_ids(
        self, client, requests_mock, recipient_address, sender_address
    ):
        """Test sending multichannel message with custom service and recipient IDs."""
        requests_mock.post(
            client.url("v2/messages"),
            json={"messageId": 12345},
            status_code=200,
        )
        custom_external_id = str(uuid.uuid4())

        result = client.send_multichannel_message(
            title="Custom IDs Message",
            body="Custom IDs test",
            body_format=BodyFormat.TEXT,
            service_id="custom_service_456",
            recipient_id="custom_recipient_789",
            recipient_address=recipient_address,
            sender_address=sender_address,
            paper_mail_attachment_id="att_paper_1",
            external_id=custom_external_id,
        )

        # Verify output
        message_id, external_id = result
        assert message_id == 12345
        assert external_id == custom_external_id

        # Verify custom IDs are passed through (send method responsibility)
        request_json = requests_mock.last_request.json()
        assert request_json["sender"]["serviceId"] == "custom_service_456"
        assert request_json["recipient"]["id"] == "custom_recipient_789"
        assert request_json["externalId"] == custom_external_id

    def test_send_multichannel_message_missing_service_id(
        self, settings, recipient_address, sender_address
    ):
        """Test that ValueError is raised when service_id is missing."""
        settings.SUOMIFI_SERVICE_ID = ""

        client = SuomiFiClient()
        client.base_url = "https://foo-bar.baz.test/"

        with pytest.raises(ValueError, match="Suomi.fi service_id is not configured."):
            client.send_multichannel_message(
                title="Test",
                body="Test",
                body_format=BodyFormat.TEXT,
                recipient_id="123456-789A",
                recipient_address=recipient_address,
                sender_address=sender_address,
                paper_mail_attachment_id="att_1",
            )

    def test_send_multichannel_message_failure(
        self, client, requests_mock, recipient_address, sender_address
    ):
        """Test multichannel message send failure."""
        requests_mock.post(
            client.url("v2/messages"),
            json={"error": "Invalid message format"},
            status_code=400,
        )

        with pytest.raises(
            SuomiFiAPIError, match="Failed to send multichannel message"
        ):
            client.send_multichannel_message(
                title="Test",
                body="Test",
                body_format=BodyFormat.TEXT,
                recipient_id="123456-789A",
                recipient_address=recipient_address,
                sender_address=sender_address,
                paper_mail_attachment_id="att_1",
            )


class TestSuomiFiClientSendPaperMailWithoutId:
    """Test SuomiFiClient paper mail without ID sending functionality."""

    def test_send_paper_mail_without_id_success(
        self, client, requests_mock, recipient_address, sender_address, mocker
    ):
        """Test sending paper mail without ID successfully."""
        mock_paper = {"attachments": [{"attachmentId": "att_1"}]}
        mocker.patch.object(client, "build_paper_mail_message", return_value=mock_paper)

        requests_mock.post(
            client.url("v2/paper-mail-without-id"),
            json={"messageId": 12345},
            status_code=200,
        )

        result = client.send_paper_mail_without_id(
            recipient_address=recipient_address,
            sender_address=sender_address,
            attachment_id="att_paper_1",
        )

        request_json = requests_mock.last_request.json()
        assert request_json == {
            "paperMail": mock_paper,
            "sender": {"serviceId": "suomifi_service_id"},
            "externalId": request_json["externalId"],
        }

        message_id, external_id = result
        assert message_id == 12345
        assert external_id == request_json["externalId"]

    def test_send_paper_mail_without_id_with_custom_ids(
        self, client, requests_mock, recipient_address, sender_address
    ):
        """Test sending paper mail without ID with custom service and external IDs."""
        requests_mock.post(
            client.url("v2/paper-mail-without-id"),
            json={"messageId": 12345},
            status_code=200,
        )
        custom_external_id = str(uuid.uuid4())

        result = client.send_paper_mail_without_id(
            recipient_address=recipient_address,
            sender_address=sender_address,
            attachment_id="att_paper_1",
            service_id="custom_service_456",
            external_id=custom_external_id,
        )

        message_id, external_id = result
        assert message_id == 12345
        assert external_id == custom_external_id
        request_json = requests_mock.last_request.json()
        assert request_json["sender"]["serviceId"] == "custom_service_456"
        assert request_json["externalId"] == custom_external_id

    def test_send_paper_mail_without_id_missing_service_id(
        self, settings, recipient_address, sender_address
    ):
        """Test that ValueError is raised when service_id is missing."""
        settings.SUOMIFI_SERVICE_ID = ""

        client = SuomiFiClient()
        client.base_url = "https://foo-bar.baz.test/"

        with pytest.raises(ValueError, match="Suomi.fi service_id is not configured."):
            client.send_paper_mail_without_id(
                recipient_address=recipient_address,
                sender_address=sender_address,
                attachment_id="att_1",
            )

    def test_send_paper_mail_without_id_failure(
        self, client, requests_mock, recipient_address, sender_address
    ):
        """Test paper mail without ID send failure."""
        requests_mock.post(
            client.url("v2/paper-mail-without-id"),
            json={"error": "Invalid message format"},
            status_code=400,
        )

        with pytest.raises(
            SuomiFiAPIError, match="Failed to send paper mail without id"
        ):
            client.send_paper_mail_without_id(
                recipient_address=recipient_address,
                sender_address=sender_address,
                attachment_id="att_1",
            )


class TestSuomiFiClientGetEvents:
    """Test SuomiFiClient event retrieval functionality."""

    def test_get_events_without_continuation(self, client, requests_mock):
        """Test getting events without continuation token."""
        requests_mock.get(
            client.url("v2/events"),
            json={
                "events": [
                    {
                        "type": "Electronic message created",
                        "eventTime": "2024-01-01T12:00:00Z",
                        "metadata": {
                            "messageId": 123,
                            "serviceId": "service_1",
                            "externalId": "ext_1",
                        },
                    },
                    {
                        "type": "Electronic message read",
                        "eventTime": "2024-01-02T12:00:00Z",
                        "metadata": {
                            "messageId": 456,
                            "serviceId": "service_2",
                        },
                    },
                ],
                "continuationToken": "next_token_123",
            },
            status_code=200,
        )

        result = client.get_events()

        assert requests_mock.last_request.qs == {}

        events, continuation_token = result

        assert events == [
            Event(
                type=EventType.ELECTRONIC_MESSAGE_CREATED,
                event_time=datetime.fromisoformat("2024-01-01T12:00:00+00:00"),
                metadata=EventMetadata(
                    message_id=123,
                    service_id="service_1",
                    external_id="ext_1",
                ),
            ),
            Event(
                type=EventType.ELECTRONIC_MESSAGE_READ,
                event_time=datetime.fromisoformat("2024-01-02T12:00:00+00:00"),
                metadata=EventMetadata(
                    message_id=456,
                    service_id="service_2",
                    external_id=None,
                ),
            ),
        ]
        assert continuation_token == "next_token_123"

    def test_get_events_with_continuation(self, client, requests_mock):
        """Test getting events with continuation token."""
        requests_mock.get(
            client.url("v2/events"),
            json={
                "events": [
                    {
                        "type": "Paper mail created",
                        "eventTime": "2024-01-03T12:00:00Z",
                        "metadata": {
                            "messageId": 789,
                            "serviceId": "service_3",
                        },
                    }
                ],
                "continuationToken": None,
            },
            status_code=200,
        )

        result = client.get_events(continuation_token="existing_token_456")

        assert requests_mock.last_request.qs == {
            "continuationToken": ["existing_token_456"]
        }

        events, continuation_token = result

        assert events == [
            Event(
                type=EventType.PAPER_MAIL_CREATED,
                event_time=datetime.fromisoformat("2024-01-03T12:00:00+00:00"),
                metadata=EventMetadata(
                    message_id=789,
                    service_id="service_3",
                    external_id=None,
                ),
            ),
        ]
        assert continuation_token is None

    def test_get_events_with_unknown_event_type(self, client, requests_mock):
        """Test that unknown event types are handled gracefully as strings."""
        requests_mock.get(
            client.url("v2/events"),
            json={
                "events": [
                    {
                        "type": "Unknown type",
                        "eventTime": "2024-01-02T12:00:00Z",
                        "metadata": {
                            "messageId": 456,
                            "serviceId": "service_2",
                        },
                    },
                ],
                "continuationToken": None,
            },
            status_code=200,
        )

        events, continuation_token = client.get_events()

        assert len(events) == 1
        assert events[0].type == "Unknown type"
        assert continuation_token is None

    def test_get_events_with_empty_events_list(self, client, requests_mock):
        """Test that empty events list is handled correctly."""
        requests_mock.get(
            client.url("v2/events"),
            json={
                "events": [],
                "continuationToken": None,
            },
            status_code=200,
        )

        events, continuation_token = client.get_events()

        assert events == []
        assert continuation_token is None

    def test_get_events_raises_on_error(self, client, requests_mock):
        """Test that get_events raises on HTTP error."""
        requests_mock.get(
            client.url("v2/events"),
            status_code=500,
        )

        with pytest.raises(SuomiFiAPIError):
            client.get_events()


class TestSuomiFiClientGetMessage:
    """Test SuomiFiClient message retrieval functionality."""

    def test_get_message_success(self, client, requests_mock):
        """Test successful message retrieval returns a parsed ReceivedMessage."""
        requests_mock.get(
            client.url("v2/messages/12345"),
            json={
                "messageId": 12345,
                "createdAt": "2024-01-01T12:00:00Z",
                "electronic": {
                    "messageId": 12345,
                    "createdAt": "2024-01-01T12:00:00Z",
                    "title": "Test Message",
                    "body": "Message content",
                    "attachments": [],
                },
                "sender": {
                    "mailboxOwner": {
                        "id": "123456-789A",
                        "name": "Matti Meikäläinen",
                    }
                },
            },
            status_code=200,
        )

        result = client.get_message(12345)

        assert result == ReceivedMessage(
            message_id=12345,
            created_at=datetime.fromisoformat("2024-01-01T12:00:00+00:00"),
            electronic=ReceivedElectronicMessage(
                message_id=12345,
                created_at=datetime.fromisoformat("2024-01-01T12:00:00+00:00"),
                title="Test Message",
                body="Message content",
                attachments=[],
            ),
            sender=MessageSender(
                mailbox_owner=MessageSenderActor(
                    id="123456-789A",
                    name="Matti Meikäläinen",
                ),
            ),
        )

    def test_get_message_with_attachment_and_thread(self, client, requests_mock):
        """Test message retrieval correctly parses attachments and thread info."""
        requests_mock.get(
            client.url("v2/messages/12345"),
            json={
                "messageId": 12345,
                "createdAt": "2024-01-01T12:00:00Z",
                "electronic": {
                    "messageId": 12345,
                    "createdAt": "2024-01-01T12:00:00Z",
                    "title": "Test Message",
                    "body": "Message content",
                    "attachments": [
                        {
                            "attachmentId": "att-uuid-123",
                            "filename": "document.pdf",
                            "mediaType": "application/pdf",
                            "sizeBytes": 12345,
                        }
                    ],
                    "thread": {
                        "rootMessageId": 99999,
                        "threadExternalId": "ext-thread-1",
                    },
                },
            },
            status_code=200,
        )

        result = client.get_message(12345)

        assert result.electronic.attachments == [
            ReceivedAttachment(
                attachment_id="att-uuid-123",
                filename="document.pdf",
                media_type="application/pdf",
                size_bytes=12345,
            )
        ]
        assert result.electronic.thread == MessageThread(
            root_message_id=99999,
            thread_external_id="ext-thread-1",
        )
        assert result.sender is None

    def test_get_message_with_person_on_behalf(self, client, requests_mock):
        """Test message retrieval parses person sending on behalf of mailbox owner."""
        requests_mock.get(
            client.url("v2/messages/12345"),
            json={
                "messageId": 12345,
                "createdAt": "2024-01-01T12:00:00Z",
                "electronic": {
                    "messageId": 12345,
                    "createdAt": "2024-01-01T12:00:00Z",
                    "title": "Test Message",
                    "body": "Message content",
                    "attachments": [],
                },
                "sender": {
                    "mailboxOwner": {
                        "id": "123456-789A",
                        "name": "Matti Meikäläinen",
                    },
                    "personSendingMessageOnBehalfOfMailboxOwner": {
                        "id": "987654-321B",
                        "name": "Maija Virtanen",
                    },
                },
            },
            status_code=200,
        )

        result = client.get_message(12345)

        assert result.sender == MessageSender(
            mailbox_owner=MessageSenderActor(
                id="123456-789A", name="Matti Meikäläinen"
            ),
            person_sending_on_behalf=MessageSenderActor(
                id="987654-321B", name="Maija Virtanen"
            ),
        )

    def test_get_message_with_thread_without_external_id(self, client, requests_mock):
        """Test message retrieval with a thread that has no threadExternalId."""
        requests_mock.get(
            client.url("v2/messages/12345"),
            json={
                "messageId": 12345,
                "createdAt": "2024-01-01T12:00:00Z",
                "electronic": {
                    "messageId": 12345,
                    "createdAt": "2024-01-01T12:00:00Z",
                    "title": "Test Message",
                    "body": "Message content",
                    "attachments": [],
                    "thread": {
                        "rootMessageId": 99999,
                    },
                },
            },
            status_code=200,
        )

        result = client.get_message(12345)

        assert result.electronic.thread == MessageThread(
            root_message_id=99999,
            thread_external_id=None,
        )

    def test_get_message_raises_on_error(self, client, requests_mock):
        """Test that get_message raises SuomiFiAPIError on HTTP error."""
        requests_mock.get(
            client.url("v2/messages/99999"),
            status_code=404,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to retrieve message"):
            client.get_message(99999)


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

        assert result == b"Binary attachment content"

    def test_get_attachment_raises_on_error(self, client, requests_mock):
        """Test that get_attachment raises on HTTP error."""
        requests_mock.get(
            client.url("v1/attachments/nonexistent"),
            status_code=404,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to retrieve attachment"):
            client.get_attachment("nonexistent")


class TestSuomiFiClientUploadAttachment:
    """Test SuomiFiClient attachment upload functionality."""

    def test_upload_attachment(self, client, requests_mock):
        """Test uploading an attachment returns the attachment ID and sends filename."""
        attachment_id = "550e8400-e29b-41d4-a716-446655440000"
        requests_mock.post(
            client.url("/v2/attachments"),
            json={"attachmentId": attachment_id},
            status_code=201,
        )

        result = client.upload_attachment("document.pdf", b"file content")

        assert result == attachment_id
        assert b"document.pdf" in requests_mock.last_request.body

    def test_upload_attachment_failure(self, client, requests_mock):
        """Test that a non-2xx response raises SuomiFiAPIError."""
        requests_mock.post(
            client.url("/v2/attachments"),
            json={"error": "Unsupported media type"},
            status_code=415,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to upload attachment"):
            client.upload_attachment("document.xyz", b"file content")


class TestBuildElectronicMessage:
    """Test electronic message builder."""

    @pytest.mark.parametrize("body_format", [BodyFormat.TEXT, BodyFormat.MARKDOWN])
    def test_build_electronic_message_with_body_format(self, client, body_format):
        """Build electronic message with different body formats."""
        electronic_msg = client.build_electronic_message(
            title="Test Title",
            body="Test Body",
            body_format=body_format,
            attachment_ids=[],
            verifiable=False,
            reply_allowed=False,
            reply_to=None,
            reminder=True,
        )

        expected = ElectronicPart(
            attachments=[],
            body="Test Body",
            body_format=body_format,
            message_service_type=MessageServiceType.NORMAL,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.DEFAULT_REMINDER
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.NO_ONE,
            title="Test Title",
            visibility=Visibility.NORMAL,
        )
        assert electronic_msg == expected

    def test_build_electronic_message_with_verifiable(self, client):
        """Build verifiable electronic message."""
        electronic_msg = client.build_electronic_message(
            title="Test Title",
            body="Test Body",
            body_format=BodyFormat.TEXT,
            attachment_ids=[],
            verifiable=True,
            reply_allowed=False,
            reply_to=None,
            reminder=True,
        )

        expected = ElectronicPart(
            attachments=[],
            body="Test Body",
            body_format=BodyFormat.TEXT,
            message_service_type=MessageServiceType.VERIFIABLE,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.DEFAULT_REMINDER
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.NO_ONE,
            title="Test Title",
            visibility=Visibility.NORMAL,
        )
        assert electronic_msg == expected

    def test_build_electronic_message_with_reply_allowed(self, client):
        """Build electronic message with replies allowed."""
        electronic_msg = client.build_electronic_message(
            title="Test Title",
            body="Test Body",
            body_format=BodyFormat.TEXT,
            attachment_ids=[],
            verifiable=False,
            reply_allowed=True,
            reply_to=None,
            reminder=True,
        )

        expected = ElectronicPart(
            attachments=[],
            body="Test Body",
            body_format=BodyFormat.TEXT,
            message_service_type=MessageServiceType.NORMAL,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.DEFAULT_REMINDER
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.ANYONE,
            title="Test Title",
            visibility=Visibility.NORMAL,
        )
        assert electronic_msg == expected

    def test_build_electronic_message_with_no_reminders(self, client):
        """Build electronic message with reminders disabled."""
        electronic_msg = client.build_electronic_message(
            title="Test Title",
            body="Test Body",
            body_format=BodyFormat.TEXT,
            attachment_ids=[],
            verifiable=False,
            reply_allowed=False,
            reply_to=None,
            reminder=False,
        )

        expected = ElectronicPart(
            attachments=[],
            body="Test Body",
            body_format=BodyFormat.TEXT,
            message_service_type=MessageServiceType.NORMAL,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.NO_REMINDERS
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.NO_ONE,
            title="Test Title",
            visibility=Visibility.NORMAL,
        )
        assert electronic_msg == expected

    def test_build_electronic_message_with_attachments(self, client):
        """Build electronic message with attachments."""
        electronic_msg = client.build_electronic_message(
            title="Test Title",
            body="Test Body",
            body_format=BodyFormat.TEXT,
            attachment_ids=["att_1", "att_2"],
            verifiable=False,
            reply_allowed=False,
            reply_to=None,
            reminder=True,
        )

        expected = ElectronicPart(
            attachments=[
                AttachmentReference(attachment_id="att_1"),
                AttachmentReference(attachment_id="att_2"),
            ],
            body="Test Body",
            body_format=BodyFormat.TEXT,
            message_service_type=MessageServiceType.NORMAL,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.DEFAULT_REMINDER
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.NO_ONE,
            title="Test Title",
            visibility=Visibility.NORMAL,
        )
        assert electronic_msg == expected

    def test_build_electronic_message_with_reply_to(self, client):
        """Build electronic message as a reply."""
        electronic_msg = client.build_electronic_message(
            title="Re: Test Title",
            body="Reply Body",
            body_format=BodyFormat.TEXT,
            attachment_ids=[],
            verifiable=False,
            reply_allowed=False,
            reply_to=12345,
            reminder=True,
        )

        expected = ElectronicPart(
            attachments=[],
            body="Reply Body",
            body_format=BodyFormat.TEXT,
            in_reply_to_message_id=12345,
            message_service_type=MessageServiceType.NORMAL,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.DEFAULT_REMINDER
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.NO_ONE,
            title="Re: Test Title",
            visibility=Visibility.NORMAL,
        )
        assert electronic_msg == expected


class TestBuildPaperMailMessage:
    """Test paper mail message builder."""

    def test_build_paper_mail_missing_credentials_raises_error(
        self, client, settings, recipient_address, sender_address
    ):
        """Verify error is raised when Posti credentials are not configured."""
        settings.SUOMIFI_POSTI_EMAIL = ""
        settings.SUOMIFI_POSTI_USERNAME = ""
        settings.SUOMIFI_POSTI_PASSWORD = ""

        with pytest.raises(SuomiFiError, match="Paper mail requires Posti credentials"):
            client.build_paper_mail_message(
                recipient_address=recipient_address,
                sender_address=sender_address,
                attachment_id="",
                verifiable=False,
            )

    @pytest.mark.parametrize(
        "verifiable,expected_service_type",
        [
            (False, MessageServiceType.NORMAL),
            (True, MessageServiceType.VERIFIABLE),
        ],
    )
    def test_build_paper_mail_with_verifiable(
        self,
        client,
        recipient_address,
        sender_address,
        verifiable,
        expected_service_type,
    ):
        """Build paper mail with and without verifiable flag."""
        paper_mail = client.build_paper_mail_message(
            recipient_address=recipient_address,
            sender_address=sender_address,
            attachment_id="att_1",
            verifiable=verifiable,
        )

        expected = PaperMailPart(
            color_printing=True,
            create_address_page=True,
            attachments=[AttachmentReference(attachment_id="att_1")],
            message_service_type=expected_service_type,
            recipient=NewPaperMailRecipient(
                address=recipient_address,
            ),
            sender=NewPaperMailSender(
                address=sender_address,
            ),
            printing_and_enveloping_service=PrintingAndEnvelopingService(
                posti_messaging=PostiMessaging(
                    contact_details={"email": "suomifi_posti_email"},
                    password="suomifi_posti_password",
                    username="suomifi_posti_username",
                ),
            ),
            rotate_landscape_pages=False,
            two_sided_printing=False,
        )
        assert paper_mail == expected

    def test_build_paper_mail_with_additional_name(
        self, client, recipient_address, sender_address
    ):
        """Build paper mail with additional address line."""
        # Create a modified address with additional_name
        recipient_with_co = Address(
            name=recipient_address.name,
            street_address=recipient_address.street_address,
            zip_code=recipient_address.zip_code,
            city=recipient_address.city,
            country_code=recipient_address.country_code,
            additional_name="c/o Virtanen",
        )

        paper_mail = client.build_paper_mail_message(
            recipient_address=recipient_with_co,
            sender_address=sender_address,
            attachment_id="att_1",
            verifiable=False,
        )

        expected = PaperMailPart(
            color_printing=True,
            create_address_page=True,
            attachments=[AttachmentReference(attachment_id="att_1")],
            message_service_type=MessageServiceType.NORMAL,
            recipient=NewPaperMailRecipient(
                address=recipient_with_co,
            ),
            sender=NewPaperMailSender(
                address=sender_address,
            ),
            printing_and_enveloping_service=PrintingAndEnvelopingService(
                posti_messaging=PostiMessaging(
                    contact_details={"email": "suomifi_posti_email"},
                    password="suomifi_posti_password",
                    username="suomifi_posti_username",
                ),
            ),
            rotate_landscape_pages=False,
            two_sided_printing=False,
        )
        assert paper_mail == expected

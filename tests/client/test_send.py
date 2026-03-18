import uuid

import pytest

from suomifi_messages.client import SuomiFiClient
from suomifi_messages.errors import SuomiFiAPIError
from suomifi_messages.schemas import BodyFormat


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

from datetime import datetime

import pytest

from suomifi_messages.errors import SuomiFiAPIError
from suomifi_messages.schemas import (
    Event,
    EventMetadata,
    EventType,
    MessageSender,
    MessageSenderActor,
    MessageThread,
    ReceivedAttachment,
    ReceivedElectronicMessage,
    ReceivedMessage,
)


def test_get_events_without_continuation(client, requests_mock):
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


def test_get_events_with_continuation(client, requests_mock):
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


def test_get_events_with_unknown_event_type(client, requests_mock):
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


def test_get_events_with_empty_events_list(client, requests_mock):
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


def test_get_events_raises_on_error(client, requests_mock):
    """Test that get_events raises on HTTP error."""
    requests_mock.get(
        client.url("v2/events"),
        status_code=500,
    )

    with pytest.raises(SuomiFiAPIError):
        client.get_events()


def test_get_message_success(client, requests_mock):
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


def test_get_message_with_attachment_and_thread(client, requests_mock):
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


def test_get_message_with_person_on_behalf(client, requests_mock):
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
        mailbox_owner=MessageSenderActor(id="123456-789A", name="Matti Meikäläinen"),
        person_sending_on_behalf=MessageSenderActor(
            id="987654-321B", name="Maija Virtanen"
        ),
    )


def test_get_message_with_thread_without_external_id(client, requests_mock):
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


def test_get_message_raises_on_error(client, requests_mock):
    """Test that get_message raises SuomiFiAPIError on HTTP error."""
    requests_mock.get(
        client.url("v2/messages/99999"),
        status_code=404,
    )

    with pytest.raises(SuomiFiAPIError, match="Failed to retrieve message"):
        client.get_message(99999)

"""Tests for suomifi_messages.schemas module functions."""

from dataclasses import dataclass

import pytest

from suomifi_messages.schemas import (
    BodyFormat,
    ElectronicPart,
    MessageNotifications,
    MessageServiceType,
    ReminderType,
    ReplyAllowedBy,
    SenderDetailsInNotifications,
    UnreadMessageNotification,
    Visibility,
    camel_case_dict_factory,
    dataclass_to_dict,
    to_camel_case,
)

# Test dataclasses for helper function tests


@dataclass
class SimpleItem:
    """Simple test dataclass for basic conversions."""

    item_id: str


@dataclass
class ItemWithOptionals:
    """Test dataclass with optional fields."""

    name: str
    street_address: str
    optional_field: str | None = None
    another_optional: str | None = None


@dataclass
class ComplexItem:
    """Test dataclass with nested structures."""

    title: str
    nested_items: list[SimpleItem]


@pytest.mark.parametrize(
    "snake_case,expected_camel_case",
    [
        ("foo", "foo"),
        ("foo_bar", "fooBar"),
        ("very_long_field_name_foo_bar_baz", "veryLongFieldNameFooBarBaz"),
        ("a", "a"),
        ("a_b_c", "aBC"),
        ("", ""),
        # Actual use cases
        ("id", "id"),
        ("external_id", "externalId"),
        ("street_address", "streetAddress"),
        ("in_reply_to_message_id", "inReplyToMessageId"),
        # transformation doesn't work with leading underscores
        pytest.param("_foo_bar", "_fooBar", marks=pytest.mark.xfail),
    ],
)
def test_to_camel_case(snake_case, expected_camel_case):
    result = to_camel_case(snake_case)

    assert result == expected_camel_case


def test_camel_case_dict_factory_converts_keys():
    fields = [
        ("first_name", "John"),
        ("last_name", "Doe"),
        ("email_address", "john@example.com"),
    ]

    result = camel_case_dict_factory(fields)

    assert result == {
        "firstName": "John",
        "lastName": "Doe",
        "emailAddress": "john@example.com",
    }


def test_camel_case_dict_factory_omits_none_values():
    fields = [
        ("name", "Test"),
        ("optional_field", None),
        ("another_field", "Value"),
        ("none_field", None),
    ]

    result = camel_case_dict_factory(fields)

    assert result == {
        "name": "Test",
        "anotherField": "Value",
    }


def test_camel_case_dict_factory_empty_fields():
    result = camel_case_dict_factory([])

    assert result == {}


def test_camel_case_dict_factory_preserves_value_types():
    fields = [
        ("string_val", "text"),
        ("int_val", 42),
        ("bool_val", True),
        ("list_val", [1, 2, 3]),
        ("dict_val", {"key": "value"}),
    ]

    result = camel_case_dict_factory(fields)

    assert result == {
        "stringVal": "text",
        "intVal": 42,
        "boolVal": True,
        "listVal": [1, 2, 3],
        "dictVal": {"key": "value"},
    }


def test_dataclass_to_dict_simple():
    obj = SimpleItem(item_id="test-123")

    result = dataclass_to_dict(obj)

    assert result == {"itemId": "test-123"}


def test_dataclass_to_dict_omits_none():
    obj = ItemWithOptionals(
        name="Test",
        street_address="Street 1",
        optional_field=None,
        another_optional=None,
    )

    result = dataclass_to_dict(obj)

    assert result == {"name": "Test", "streetAddress": "Street 1"}


def test_dataclass_to_dict_nested_list():
    nested_items = [
        SimpleItem(item_id="item-1"),
        SimpleItem(item_id="item-2"),
    ]

    obj = ComplexItem(
        title="Test",
        nested_items=nested_items,
    )

    result = dataclass_to_dict(obj)

    assert result == {
        "title": "Test",
        "nestedItems": [
            {"itemId": "item-1"},
            {"itemId": "item-2"},
        ],
    }


def test_dataclass_to_dict_serializes_enums():
    electronic = ElectronicPart(
        title="Test",
        body="Body",
        body_format=BodyFormat.MARKDOWN,
        message_service_type=MessageServiceType.VERIFIABLE,
        reply_allowed_by=ReplyAllowedBy.ANYONE,
        visibility=Visibility.RECIPIENT_ONLY,
        attachments=[],
        notifications=MessageNotifications(
            sender_details_in_notifications=SenderDetailsInNotifications.NONE,
            unread_message_notification=UnreadMessageNotification(
                reminder=ReminderType.NO_REMINDERS
            ),
        ),
    )

    result = dataclass_to_dict(electronic)

    assert result == {
        "title": "Test",
        "body": "Body",
        "bodyFormat": "Markdown",
        "messageServiceType": "Verifiable",
        "replyAllowedBy": "Anyone",
        "visibility": "Recipient only",
        "attachments": [],
        "notifications": {
            "senderDetailsInNotifications": "None",
            "unreadMessageNotification": {
                "reminder": "No reminders",
            },
        },
    }

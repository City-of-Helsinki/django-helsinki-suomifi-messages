"""
Wrappers for Suomi.fi Messages API v2 request/response schemas.

Based on the OpenAPI schema from https://api.messages.suomi.fi/docs/messages-api.yaml
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import TypedDict


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def camel_case_dict_factory(fields):
    """
    Dict factory for asdict() that converts snake_case keys to camelCase.

    This is used with dataclasses.asdict() to automatically convert all
    field names to camelCase for API requests.

    :param fields: An iterable of (key, value) tuples from the dataclass
    :returns: A dict with camelCase keys, omitting None values
    :rtype: dict
    """
    return {to_camel_case(key): value for key, value in fields if value is not None}


def dataclass_to_dict(obj) -> dict:
    """
    Convert a dataclass instance to a dict with camelCase keys.

    This recursively handles nested dataclasses and lists, and omits
    fields with None values.

    :param obj: A dataclass instance
    :returns: A dictionary with camelCase keys suitable for API requests
    :rtype: dict
    """
    return asdict(obj, dict_factory=camel_case_dict_factory)


# Enums


class MessageServiceType(str, Enum):
    """Message service type enum."""

    NORMAL = "Normal"
    VERIFIABLE = "Verifiable"


class BodyFormat(str, Enum):
    """Body format enum for electronic messages."""

    TEXT = "Text"
    MARKDOWN = "Markdown"


class ReplyAllowedBy(str, Enum):
    """Reply permission enum."""

    ANYONE = "Anyone"
    NO_ONE = "No one"


class Visibility(str, Enum):
    """Message visibility enum."""

    NORMAL = "Normal"
    RECIPIENT_ONLY = "Recipient only"


class SenderDetailsInNotifications(str, Enum):
    """Sender details in notifications enum."""

    ORGANISATION_AND_SERVICE_NAME = "Organisation and service name"
    NONE = "None"


class ReminderType(str, Enum):
    """Reminder type enum for unread message notifications."""

    DEFAULT_REMINDER = "Default reminder"
    NO_REMINDERS = "No reminders"


# Typed dicts


class TranslatedText(TypedDict):
    """Text in Finnish, Swedish, and English."""

    fi: str
    sv: str
    en: str


class ContactDetails(TypedDict):
    """Contact details for printing and enveloping service."""

    email: str


# Dataclasses


@dataclass
class Address:
    """Address information for paper mail."""

    city: str
    country_code: str
    name: str
    street_address: str
    zip_code: str
    additional_name: str | None = None


@dataclass
class PostiMessaging:
    """Posti messaging configuration."""

    contact_details: ContactDetails
    password: str
    username: str


@dataclass
class PrintingAndEnvelopingService:
    """Printing and enveloping service configuration."""

    posti_messaging: PostiMessaging
    cost_pool: str | None = None


@dataclass
class NewPaperMailRecipient:
    """Recipient information for paper mail."""

    address: Address


@dataclass
class NewPaperMailSender:
    """Sender information for paper mail."""

    address: Address


@dataclass
class AttachmentReference:
    """Reference to an uploaded attachment."""

    attachment_id: str


@dataclass
class CustomisedMessageNotification:
    """Customised new message notification."""

    content: TranslatedText
    title: TranslatedText


@dataclass
class UnreadMessageNotification:
    """Unread message notification settings."""

    reminder: ReminderType | str


@dataclass
class MessageNotifications:
    """Message notification settings."""

    sender_details_in_notifications: SenderDetailsInNotifications | str
    unread_message_notification: UnreadMessageNotification
    customised_new_message_notification: CustomisedMessageNotification | None = None


@dataclass
class ElectronicPart:
    """Electronic part of a multichannel message."""

    attachments: list[AttachmentReference]
    body: str
    body_format: BodyFormat | str
    message_service_type: MessageServiceType | str
    notifications: MessageNotifications
    reply_allowed_by: ReplyAllowedBy | str
    title: str
    visibility: Visibility | str
    in_reply_to_message_id: int | None = None


@dataclass
class PaperMailPart:
    """Paper mail part of a multichannel message."""

    attachments: list[AttachmentReference]
    color_printing: bool
    create_address_page: bool
    message_service_type: MessageServiceType | str
    printing_and_enveloping_service: PrintingAndEnvelopingService
    recipient: NewPaperMailRecipient
    rotate_landscape_pages: bool
    sender: NewPaperMailSender
    two_sided_printing: bool


@dataclass
class Recipient:
    """Message recipient (personal identity code or business ID)."""

    id: str


@dataclass
class Sender:
    """Message sender (service ID)."""

    service_id: str


@dataclass
class ElectronicMessageRequestBody:
    """
    Request body for sending an electronic-only message via Suomi.fi Messages API v2.

    Use this when sending electronic messages without paper mail fallback.
    """

    electronic: ElectronicPart
    external_id: str
    recipient: Recipient
    sender: Sender


@dataclass
class MultichannelMessageRequestBody:
    """
    Request body for sending a multichannel message via Suomi.fi Messages API v2.

    The message can be delivered either electronically or as paper mail depending
    on the state of the recipient's electronic mailbox.
    """

    electronic: ElectronicPart
    external_id: str
    paper_mail: PaperMailPart
    recipient: Recipient
    sender: Sender

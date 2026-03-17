"""
Wrappers for Suomi.fi Messages API v2 request/response schemas.

Based on the OpenAPI schema from https://api.messages.suomi.fi/docs/messages-api.yaml
"""

from dataclasses import asdict, dataclass
from datetime import datetime
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


class EventType(str, Enum):
    """Event type enum for message lifecycle events."""

    ELECTRONIC_MESSAGE_CREATED = "Electronic message created"
    ELECTRONIC_MESSAGE_FROM_END_USER = "Electronic message from end user"
    ELECTRONIC_MESSAGE_READ = "Electronic message read"
    PAPER_MAIL_CREATED = "Paper mail created"
    POSTI_RECEIPT_CONFIRMED = "Posti: receipt confirmed"
    POSTI_RETURNED_TO_SENDER = "Posti: returned to sender"
    POSTI_UNRESOLVED = "Posti: unresolved"
    RECEIPT_CONFIRMED = "Receipt confirmed"
    SENT_FOR_PRINTING_AND_ENVELOPING = "Sent for printing and enveloping"


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


@dataclass
class PaperMailWithoutIdRequestBody:
    """
    Request body for sending paper mail without a recipient identity code via
    Suomi.fi Messages API v2.
    """

    external_id: str
    paper_mail: PaperMailPart
    sender: Sender


@dataclass
class EndUserId:
    """End user identifier (personal identity code or business ID)."""

    id: str


@dataclass
class EndUsers:
    """
    Request body for checking mailbox activity.

    Used with /v1/mailboxes/active endpoint.
    """

    end_users: list[EndUserId]


@dataclass
class EndUsersWithActiveMailbox:
    """
    Response body from mailbox activity check.

    Contains list of user IDs that have active Suomi.fi Messages mailboxes.
    """

    end_users_with_active_mailbox: list[EndUserId]


@dataclass
class EventMetadata:
    """
    Event metadata containing message and service information.

    Common metadata present in all event types.
    """

    message_id: int
    service_id: str
    external_id: str | None = None


@dataclass
class Event:
    """
    Event related to a message sent or received.

    Events track the lifecycle of messages including creation, reading,
    and delivery status updates. The type field contains known EventType
    enum values or unknown types as strings for forward compatibility.
    """

    type: EventType | str
    event_time: datetime
    metadata: EventMetadata


@dataclass
class ReceivedAttachment:
    """Attachment metadata on a message received from an end user."""

    attachment_id: str | None = None
    filename: str | None = None
    media_type: str | None = None
    size_bytes: int | None = None


@dataclass
class MessageThread:
    """Thread information linking messages in a conversation."""

    root_message_id: int
    thread_external_id: str | None = None


@dataclass
class ReceivedElectronicMessage:
    """Electronic message content received from an end user."""

    message_id: int
    created_at: datetime
    title: str
    body: str
    attachments: list[ReceivedAttachment]
    thread: MessageThread | None = None


@dataclass
class MessageSenderActor:
    """Individual actor in a message sender context."""

    id: str
    name: str


@dataclass
class MessageSender:
    """Sender information for a message received from an end user."""

    mailbox_owner: MessageSenderActor
    person_sending_on_behalf: MessageSenderActor | None = None


@dataclass
class ReceivedMessage:
    """
    A message received from an end user via Suomi.fi Messages.

    Corresponds to the v2 API response from GET /v2/messages/{id}.
    """

    message_id: int
    created_at: datetime
    electronic: ReceivedElectronicMessage
    sender: MessageSender | None = None


@dataclass
class AccessTokenRequestBody:
    """Request body for obtaining an authentication token via POST /v1/token."""

    username: str
    password: str


@dataclass
class ChangePasswordRequestBody:
    """Request body for changing a password via POST /v1/change-password."""

    access_token: str
    current_password: str
    new_password: str

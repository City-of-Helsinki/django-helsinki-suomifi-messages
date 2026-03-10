import logging
import typing
import uuid
from urllib.parse import urljoin, urlsplit

import requests

from suomifi_messages import settings
from suomifi_messages.errors import SuomiFiAPIError, SuomiFiError
from suomifi_messages.schemas import (
    Address,
    AttachmentReference,
    BodyFormat,
    ElectronicMessageRequestBody,
    ElectronicPart,
    EndUserId,
    EndUsers,
    Event,
    EventMetadata,
    EventType,
    MessageNotifications,
    MessageSender,
    MessageSenderActor,
    MessageServiceType,
    MessageThread,
    MultichannelMessageRequestBody,
    NewPaperMailRecipient,
    NewPaperMailSender,
    PaperMailPart,
    PostiMessaging,
    PrintingAndEnvelopingService,
    ReceivedAttachment,
    ReceivedElectronicMessage,
    ReceivedMessage,
    Recipient,
    ReminderType,
    ReplyAllowedBy,
    Sender,
    SenderDetailsInNotifications,
    UnreadMessageNotification,
    Visibility,
    dataclass_to_dict,
)
from suomifi_messages.utils import parse_iso_datetime, safe_get_response_body

logger = logging.getLogger("suomi-fi-messages")

SUOMIFI_QA_BASE_URL = "https://api.messages-qa.suomi.fi"
SUOMIFI_BASE_URL = "https://api.messages.suomi.fi"


class SuomiFiClient:
    session: requests.Session
    base_url: str

    def __init__(self, type: typing.Literal["qa", "prod"] = "qa"):
        if type == "prod":
            self.base_url = SUOMIFI_BASE_URL
        elif type == "qa":
            self.base_url = SUOMIFI_QA_BASE_URL
        else:
            raise TypeError('Invalid type. Allowed values are "prod" and "qa"')

        self.token = None
        self.token_expiry = None
        self.token_type = None
        self.session = requests.Session()

    @property
    def hostname(self):
        return urlsplit(self.base_url).hostname or ""

    def url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    def request(self, method: str, path: str, **kwargs):
        return self.session.request(method, self.url(path), **kwargs)

    def post(self, path: str, data=None, json=None, **kwargs):
        return self.request("POST", path, data=data, json=json, **kwargs)

    def get(self, path: str, params=None, **kwargs):
        return self.request("GET", path, params=params, **kwargs)

    def _raise_for_status(self, response: requests.Response, error_message: str):
        """Check response status and raise SuomiFiAPIError if not successful.

        :param response: HTTP response to check
        :param error_message: Error message to use (status code will be appended)
        :raises SuomiFiAPIError: If response status is not in 2xx range
        """
        if not (200 <= response.status_code < 300):
            raise SuomiFiAPIError(
                f"{error_message} (status {response.status_code})",
                response_body=safe_get_response_body(response),
            )

    def login(self, username: str = "", password: str = ""):
        auth_params = {
            "username": username or settings.SUOMIFI_USERNAME,
            "password": password or settings.SUOMIFI_PASSWORD,
        }

        def mask_password(password: str) -> str:
            if password:
                return password[0] + "*" * (len(password) - 1)
            return ""

        logger.debug(
            f"Logging in with username: {auth_params['username']}, "
            f"password: {mask_password(auth_params['password'])}"
        )

        response = self.post("/v1/token", json=auth_params)
        self._raise_for_status(response, "Authentication failed")

        parsed_response = response.json()

        # These are informational only, session header setup below
        # is used for all authorized requests
        self.token = parsed_response["access_token"]
        self.token_expiry = parsed_response["expires_in"]
        self.token_type = parsed_response["token_type"]

        self.session.headers.update(
            {"Authorization": self.token, "Host": self.hostname}
        )

    def change_password(self, current_password, new_password):
        pw_change_request = {
            "currentPassword": current_password,
            "newPassword": new_password,
            "accessToken": self.token,
        }

        # Password change is a special case that does not use Authorization-header
        response = self.post("/v1/change-password", json=pw_change_request)
        self._raise_for_status(response, "Password change failed")

        return response.json()

    def build_paper_mail_message(
        self,
        recipient_address: Address,
        sender_address: Address,
        attachment_id: str,
        verifiable: bool,
    ) -> PaperMailPart:
        """
        Build paper mail message structure.

        :param recipient_address: Recipient address information
        :param sender_address: Sender address information
        :param attachment_id: Attachment ID
        :param verifiable: Whether this is a verifiable message
        :returns: PaperMailPart dataclass ready for API request
        :rtype: PaperMailPart
        :raises SuomiFiError: If Posti credentials are not configured
        """
        posti_email = settings.SUOMIFI_POSTI_EMAIL
        posti_username = settings.SUOMIFI_POSTI_USERNAME
        posti_password = settings.SUOMIFI_POSTI_PASSWORD

        # Verify Posti credentials are configured
        if not all([posti_email, posti_username, posti_password]):
            raise SuomiFiError(
                "Paper mail requires Posti credentials. Please configure "
                "SUOMIFI_POSTI_EMAIL, SUOMIFI_POSTI_USERNAME, and "
                "SUOMIFI_POSTI_PASSWORD in your Django settings. "
                "See: https://kehittajille.suomi.fi/services/messages/deployment/"
                "deployment-of-the-printing-enveloping-and-distribution-service"
            )

        paper_mail = PaperMailPart(
            color_printing=True,
            create_address_page=True,
            attachments=[AttachmentReference(attachment_id=attachment_id)],
            message_service_type=MessageServiceType.VERIFIABLE
            if verifiable
            else MessageServiceType.NORMAL,
            printing_and_enveloping_service=PrintingAndEnvelopingService(
                posti_messaging=PostiMessaging(
                    contact_details={"email": posti_email},
                    password=posti_password,
                    username=posti_username,
                ),
            ),
            recipient=NewPaperMailRecipient(address=recipient_address),
            rotate_landscape_pages=False,
            sender=NewPaperMailSender(address=sender_address),
            two_sided_printing=False,
        )

        return paper_mail

    def build_electronic_message(
        self,
        title: str,
        body: str,
        body_format: BodyFormat,
        verifiable: bool,
        reply_allowed: bool,
        reminder: bool,
        reply_to: int | None = None,
        attachment_ids: list[str] | None = None,
    ) -> ElectronicPart:
        """
        Build electronic message structure.

        :param title: Message title
        :param body: Message body content
        :param body_format: Body format (TEXT or MARKDOWN)
        :param verifiable: Whether this is a verifiable message
        :param reply_allowed: Whether recipient can reply
        :param reminder: Whether to send unread message reminders
        :param reply_to: Message ID to reply to (optional)
        :param attachment_ids: List of attachment IDs (optional)
        :returns: ElectronicPart dataclass ready for API request
        :rtype: ElectronicPart
        """
        attachment_ids = attachment_ids or []
        electronic_msg = ElectronicPart(
            attachments=[
                AttachmentReference(attachment_id=attachment_id)
                for attachment_id in attachment_ids
            ],
            body=body,
            body_format=body_format,
            message_service_type=MessageServiceType.VERIFIABLE
            if verifiable
            else MessageServiceType.NORMAL,
            notifications=MessageNotifications(
                sender_details_in_notifications=SenderDetailsInNotifications.ORGANISATION_AND_SERVICE_NAME,
                unread_message_notification=UnreadMessageNotification(
                    reminder=ReminderType.DEFAULT_REMINDER
                    if reminder
                    else ReminderType.NO_REMINDERS
                ),
            ),
            reply_allowed_by=ReplyAllowedBy.ANYONE
            if reply_allowed
            else ReplyAllowedBy.NO_ONE,
            title=title,
            visibility=Visibility.NORMAL,
            in_reply_to_message_id=reply_to,
        )

        return electronic_msg

    def send_electronic_message(
        self,
        title: str,
        body: str,
        body_format: BodyFormat,
        recipient_id: str,
        service_id: str | None = None,
        reply_to: int | None = None,
        attachment_ids: list[str] | None = None,
        external_id: str | None = None,
        verifiable: bool = False,
        reply_allowed: bool = False,
        reminder: bool = True,
    ) -> tuple[int, str]:
        """
        Send an electronic-only message to a Suomi.fi Messages user.

        This sends a message that is delivered electronically to recipients with
        active Suomi.fi Messages mailboxes. Use this endpoint to send new messages
        or replies to messages from end users.

        :param title: Message title
        :param body: Message body content
        :param body_format: Body format (TEXT or MARKDOWN)
        :param recipient_id: Recipient ID (SSN or business ID)
        :param service_id: Service ID, uses settings.SUOMIFI_SERVICE_ID if not provided
        :param reply_to: Message ID to reply to (optional)
        :param attachment_ids: List of attachment IDs (optional)
        :param external_id: External ID for idempotency, generates UUID if
            not provided
        :param verifiable: Whether to send as verifiable message
        :param reply_allowed: Whether recipient can reply
        :param reminder: Whether to send unread message reminders
        :returns: Tuple of (message_id, external_id) where message_id is the
            Suomi.fi unique identifier (int) for tracking/replies, and external_id
            is your system's identifier (str) used for idempotency
        :rtype: tuple[int, str]
        :raises ValueError: If service_id is not provided or configured
        :raises SuomiFiAPIError: If message send fails (e.g., mailbox not active,
            replied-to message not found)
        """
        if not (service_id := service_id or settings.SUOMIFI_SERVICE_ID):
            raise ValueError(
                "Suomi.fi service_id is not configured. Pass service_id explicitly "
                "to this method or define SUOMIFI_SERVICE_ID in your "
                "Django settings."
            )
        attachment_ids = attachment_ids or []
        external_id = external_id or str(uuid.uuid4())

        # Build electronic message
        electronic_msg = self.build_electronic_message(
            title=title,
            body=body,
            body_format=body_format,
            attachment_ids=attachment_ids,
            verifiable=verifiable,
            reply_allowed=reply_allowed,
            reply_to=reply_to,
            reminder=reminder,
        )

        # Build request body
        payload = ElectronicMessageRequestBody(
            electronic=electronic_msg,
            external_id=external_id,
            recipient=Recipient(id=recipient_id),
            sender=Sender(service_id=service_id),
        )

        logger.debug("Sending electronic message to /v2/messages/electronic")

        response = self.post("/v2/messages/electronic", json=dataclass_to_dict(payload))
        self._raise_for_status(response, "Failed to send electronic message")

        return response.json()["messageId"], external_id

    def send_multichannel_message(
        self,
        title: str,
        body: str,
        body_format: BodyFormat,
        recipient_id: str,
        recipient_address: Address,
        sender_address: Address,
        paper_mail_attachment_id: str,
        service_id: str | None = None,
        reply_to: int | None = None,
        electronic_attachment_ids: list[str] | None = None,
        external_id: str | None = None,
        verifiable: bool = False,
        reply_allowed: bool = False,
        reminder: bool = True,
    ) -> tuple[int, str]:
        """
        Send a multichannel message that adapts to recipient's mailbox state.

        The message will be delivered either electronically OR as paper mail
        depending on whether the recipient has an active Suomi.fi Messages mailbox.
        You must provide content for both delivery channels.

        :param title: Message title (for both electronic and paper mail)
        :param body: Message body content (for electronic message)
        :param body_format: Body format (TEXT or MARKDOWN)
        :param recipient_id: Recipient ID (SSN or business ID)
        :param recipient_address: Postal address for paper mail delivery
        :param sender_address: Sender's postal address for paper mail
        :param paper_mail_attachment_id: Attachment ID for paper mail (required)
        :param service_id: Service ID, uses settings.SUOMIFI_SERVICE_ID if not provided
        :param reply_to: Message ID to reply to (optional)
        :param electronic_attachment_ids: List of attachment IDs for electronic message
            (optional)
        :param external_id: External ID for idempotency, generates UUID if not provided
        :param verifiable: Whether to send as verifiable message
        :param reply_allowed: Whether recipient can reply (electronic only)
        :param reminder: Whether to send unread message reminders (electronic only)
        :returns: Tuple of (message_id, external_id) where message_id is the
            Suomi.fi unique identifier (int) for tracking/replies, and external_id
            is your system's identifier (str) used for idempotency
        :rtype: tuple[int, str]
        :raises ValueError: If service_id is not provided or configured
        :raises SuomiFiAPIError: If message send fails
        """

        if not (service_id := service_id or settings.SUOMIFI_SERVICE_ID):
            raise ValueError(
                "Suomi.fi service_id is not configured. Pass service_id explicitly "
                "to this method or define SUOMIFI_SERVICE_ID in your "
                "Django settings."
            )
        electronic_attachment_ids = electronic_attachment_ids or []
        external_id = external_id or str(uuid.uuid4())

        electronic_msg = self.build_electronic_message(
            title=title,
            body=body,
            body_format=body_format,
            verifiable=verifiable,
            reply_allowed=reply_allowed,
            reply_to=reply_to,
            reminder=reminder,
            attachment_ids=electronic_attachment_ids,
        )
        paper_mail = self.build_paper_mail_message(
            recipient_address=recipient_address,
            sender_address=sender_address,
            attachment_id=paper_mail_attachment_id,
            verifiable=verifiable,
        )
        payload = MultichannelMessageRequestBody(
            electronic=electronic_msg,
            external_id=external_id,
            paper_mail=paper_mail,
            recipient=Recipient(id=recipient_id),
            sender=Sender(service_id=service_id),
        )

        logger.debug("Sending message to /v2/messages")

        response = self.post("/v2/messages", json=dataclass_to_dict(payload))
        self._raise_for_status(response, "Failed to send multichannel message")

        return response.json()["messageId"], external_id

    def check_mailboxes(self, recipient_ids: list[str]) -> list[str]:
        """
        Check which recipients have active Suomi.fi Messages mailboxes.

        This endpoint should only be used in the context of sending messages to
        determine whether a recipient can receive electronic messages.

        :param recipient_ids: List of recipient IDs (SSNs or business IDs) to check.
            Maximum 10,000 IDs per request.
        :returns: List of recipient IDs that have active mailboxes
        :rtype: list[str]
        :raises SuomiFiAPIError: If the mailbox check request fails
        """
        payload = EndUsers(
            end_users=[EndUserId(id=recipient_id) for recipient_id in recipient_ids]
        )

        logger.debug(f"Checking mailbox activity for {len(recipient_ids)} recipients")

        response = self.post("/v1/mailboxes/active", json=dataclass_to_dict(payload))
        self._raise_for_status(response, "Failed to check mailbox status")

        response_data = response.json()
        active_mailbox_ids = [
            user["id"] for user in response_data.get("endUsersWithActiveMailbox", [])
        ]

        logger.debug(f"Found {len(active_mailbox_ids)} active mailboxes")

        return active_mailbox_ids

    def check_mailbox(self, recipient_id: str) -> bool:
        """
        Check if a single recipient has an active Suomi.fi Messages mailbox.

        This is a convenience method that wraps check_mailboxes for single ID checks.
        For checking multiple recipients, use check_mailboxes() directly to avoid
        making multiple API requests.

        :param recipient_id: Recipient ID (SSN or business ID)
        :returns: True if recipient has an active mailbox, False otherwise
        :rtype: bool
        :raises SuomiFiAPIError: If the mailbox check request fails
        """
        active_ids = self.check_mailboxes([recipient_id])
        return recipient_id in active_ids

    def get_events(
        self, continuation_token: str | None = None
    ) -> tuple[list[Event], str | None]:
        """
        Retrieve events related to messages you have sent or received.

        Returns at most 1,000 events per request. Event data is retrievable for
        60 days. If an empty event list is returned, there are no more events
        at this time.

        :param continuation_token: Token for pagination (optional). Use the token
            from the previous response to retrieve the next batch of events.
        :returns: Tuple of (events, continuation_token) where events is a list
            of Event objects and continuation_token is a string for pagination
            or None if no more events
        :rtype: tuple[list[Event], str | None]
        :raises SuomiFiAPIError: If the events request fails
        """
        params = {"continuationToken": continuation_token} if continuation_token else {}

        if continuation_token:
            logger.debug("Fetching events (continuing from pagination)")
        else:
            logger.debug("Fetching events")

        response = self.get("/v2/events", params=params)
        self._raise_for_status(response, "Failed to get events")

        response_data = response.json()
        raw_events = response_data.get("events", [])

        logger.debug(f"Retrieved {len(raw_events)} events")

        # Parse events into Event dataclasses
        events = []
        for raw_event in raw_events:
            # Try to parse event type as enum, fall back to string for unknown types
            try:
                event_type = EventType(raw_event["type"])
            except ValueError:
                event_type = raw_event["type"]

            events.append(
                Event(
                    type=event_type,
                    event_time=parse_iso_datetime(raw_event["eventTime"]),
                    metadata=EventMetadata(
                        message_id=raw_event["metadata"]["messageId"],
                        service_id=raw_event["metadata"]["serviceId"],
                        external_id=raw_event["metadata"].get("externalId"),
                    ),
                )
            )

        return events, response_data.get("continuationToken")

    def get_message(self, message_id: int) -> ReceivedMessage:
        """
        Retrieve a message that an end user has sent you.

        Message data is retrievable for 60 days. The messageId can be found
        in the events returned by get_events().

        :param message_id: Suomi.fi message ID from events
        :returns: The received message
        :rtype: ReceivedMessage
        :raises SuomiFiAPIError: If the message cannot be retrieved
        """
        logger.debug(f"Retrieving message {message_id}")

        response = self.get(f"/v2/messages/{message_id}")
        self._raise_for_status(response, "Failed to retrieve message")

        data = response.json()

        raw_el = data["electronic"]

        thread = None
        if raw_thread := raw_el.get("thread"):
            thread = MessageThread(
                root_message_id=raw_thread["rootMessageId"],
                thread_external_id=raw_thread.get("threadExternalId"),
            )

        electronic = ReceivedElectronicMessage(
            message_id=raw_el["messageId"],
            created_at=parse_iso_datetime(raw_el["createdAt"]),
            title=raw_el["title"],
            body=raw_el["body"],
            attachments=[
                ReceivedAttachment(
                    attachment_id=att.get("attachmentId"),
                    filename=att.get("filename"),
                    media_type=att.get("mediaType"),
                    size_bytes=att.get("sizeBytes"),
                )
                for att in raw_el.get("attachments", [])
            ],
            thread=thread,
        )

        sender = None
        if raw_sender := data.get("sender"):
            person_on_behalf = None
            if raw_on_behalf := raw_sender.get(
                "personSendingMessageOnBehalfOfMailboxOwner"
            ):
                person_on_behalf = MessageSenderActor(
                    id=raw_on_behalf["id"],
                    name=raw_on_behalf["name"],
                )

            sender = MessageSender(
                mailbox_owner=MessageSenderActor(
                    id=raw_sender["mailboxOwner"]["id"],
                    name=raw_sender["mailboxOwner"]["name"],
                ),
                person_sending_on_behalf=person_on_behalf,
            )

        return ReceivedMessage(
            message_id=data["messageId"],
            created_at=parse_iso_datetime(data["createdAt"]),
            electronic=electronic,
            sender=sender,
        )

    def get_attachment(self, attachment_id: str) -> bytes:
        """
        Retrieve an attachment that an end user has included in a message they sent you.

        Attachment data is retrievable for 60 days.

        :param attachment_id: Attachment ID
        :returns: Raw attachment content as bytes
        :rtype: bytes
        :raises SuomiFiAPIError: If the attachment cannot be retrieved
        """
        response = self.get(f"/v1/attachments/{attachment_id}")

        self._raise_for_status(response, "Failed to retrieve attachment")

        return response.content

    def upload_attachment(
        self, filename: str, filelike: bytes | typing.BinaryIO
    ) -> str:
        """
        Upload an attachment for use in electronic or paper mail messages.

        Attachments must be used in a message within 24 hours or they will be removed.
        The attachment is shown to the recipient with the filename provided here.

        :param filename: Filename shown to the recipient
        :param filelike: File content as bytes or a binary file-like object
        :returns: Attachment ID to use in message attachment references
        :rtype: str
        :raises SuomiFiAPIError: If the upload fails
        """
        logger.debug(f"Uploading attachment: {filename}")

        response = self.post("/v2/attachments", files={"file": (filename, filelike)})
        self._raise_for_status(response, "Failed to upload attachment")

        return response.json()["attachmentId"]

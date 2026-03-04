import logging
import typing
import uuid
from urllib.parse import urljoin, urlsplit

import requests
from django.conf import settings

from suomifi_messages.errors import SuomiFiError
from suomifi_messages.schemas import (
    Address,
    AttachmentReference,
    BodyFormat,
    ElectronicMessageRequestBody,
    ElectronicPart,
    EndUserId,
    EndUsers,
    MessageNotifications,
    MessageServiceType,
    MultichannelMessageRequestBody,
    NewPaperMailRecipient,
    NewPaperMailSender,
    PaperMailPart,
    PostiMessaging,
    PrintingAndEnvelopingService,
    Recipient,
    ReminderType,
    ReplyAllowedBy,
    Sender,
    SenderDetailsInNotifications,
    UnreadMessageNotification,
    Visibility,
    dataclass_to_dict,
)

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
        response.raise_for_status()

        if response.status_code != requests.codes.ok:
            logger.debug(
                f"Authentication request failed with status code {response.status_code}"
            )
            logger.debug(response.json())
            raise SuomiFiError(
                "Authentication request failed with status code "
                f"{response.status_code} (expected: {requests.codes.ok})"
            )

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

        if response.status_code != requests.codes.ok:
            logger.error(response.json())
            raise SuomiFiError("Password change request failed")

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
        # Get Posti credentials dynamically (they may be set in tests)
        posti_email = getattr(settings, "SUOMIFI_POSTI_EMAIL", "")
        posti_username = getattr(settings, "SUOMIFI_POSTI_USERNAME", "")
        posti_password = getattr(settings, "SUOMIFI_POSTI_PASSWORD", "")

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
        :raises SuomiFiError: If message send fails (e.g., mailbox not active,
            replied-to message not found)
        """
        if not (
            service_id := service_id or getattr(settings, "SUOMIFI_SERVICE_ID", "")
        ):
            raise ValueError(
                "Suomi.fi service_id is not configured. Pass service_id explicitly "
                "to this method or define settings.SUOMIFI_SERVICE_ID in your "
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

        if response.status_code != requests.codes.ok:
            logger.debug(
                "Electronic message send request failed with status code "
                f"{response.status_code}"
            )
            logger.debug(response.json())
            raise SuomiFiError("Electronic message send request failed")

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
        :raises SuomiFiError: If message send fails
        """

        if not (
            service_id := service_id or getattr(settings, "SUOMIFI_SERVICE_ID", "")
        ):
            raise ValueError(
                "Suomi.fi service_id is not configured. Pass service_id explicitly "
                "to this method or define settings.SUOMIFI_SERVICE_ID in your "
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

        if response.status_code != requests.codes.ok:
            logger.debug(
                f"Message send request failed with status code {response.status_code}"
            )
            logger.debug(response.json())
            raise SuomiFiError("Message send request failed")

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
        :raises SuomiFiError: If the mailbox check request fails
        """
        payload = EndUsers(
            end_users=[EndUserId(id=recipient_id) for recipient_id in recipient_ids]
        )

        logger.debug(f"Checking mailbox activity for {len(recipient_ids)} recipients")

        response = self.post("/v1/mailboxes/active", json=dataclass_to_dict(payload))

        if response.status_code != requests.codes.ok:
            logger.debug(
                f"Mailbox check request failed with status code {response.status_code}"
            )
            logger.debug(response.json())
            raise SuomiFiError("Mailbox check request failed")

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
        :raises SuomiFiError: If the mailbox check request fails
        """
        active_ids = self.check_mailboxes([recipient_id])
        return recipient_id in active_ids

    def get_events(self, continuation=None):
        if continuation:
            response = self.get(
                "/v2/events",
                json={"continuationToken": continuation},
            )
        else:
            response = self.get("/v2/events")

        response.raise_for_status()

        return response.json()

    def get_message(self, message_id):
        response = self.get(f"/v1/messages/{message_id}")

        response.raise_for_status()

        return response.json()

    def get_message_state(self, message_id):
        response = self.get(f"/v1/messages/{message_id}/state")

        response.raise_for_status()

        return response.json()

    def get_attachment(self, attachment_id):
        response = self.get(f"/v1/attachments/{attachment_id}")

        response.raise_for_status()

        return response

    def add_attachment(self, filelike):
        # _ATTACHMENT_ENDPOINT = "/v1/attachments"

        raise NotImplementedError

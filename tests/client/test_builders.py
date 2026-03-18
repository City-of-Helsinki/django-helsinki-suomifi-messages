import pytest

from suomifi_messages.errors import SuomiFiError
from suomifi_messages.schemas import (
    Address,
    AttachmentReference,
    BodyFormat,
    ElectronicPart,
    MessageNotifications,
    MessageServiceType,
    NewPaperMailRecipient,
    NewPaperMailSender,
    PaperMailPart,
    PostiMessaging,
    PrintingAndEnvelopingService,
    ReminderType,
    ReplyAllowedBy,
    SenderDetailsInNotifications,
    UnreadMessageNotification,
    Visibility,
)


@pytest.mark.parametrize("body_format", [BodyFormat.TEXT, BodyFormat.MARKDOWN])
def test_build_electronic_message_with_body_format(client, body_format):
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


def test_build_electronic_message_with_verifiable(client):
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


def test_build_electronic_message_with_reply_allowed(client):
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


def test_build_electronic_message_with_no_reminders(client):
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


def test_build_electronic_message_with_attachments(client):
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


def test_build_electronic_message_with_reply_to(client):
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


def test_build_paper_mail_missing_credentials_raises_error(
    client, settings, recipient_address, sender_address
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
    client, recipient_address, sender_address
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

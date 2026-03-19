# django-helsinki-suomifi-messages

Suomi.fi Messages client for City of Helsinki Django apps. See the
[API reference](https://api.messages.suomi.fi/api-docs/) for endpoint details.

- Send electronic messages to recipients with active Suomi.fi mailboxes
- Send multichannel messages (electronic or paper mail, depending on mailbox status)
- Send paper mail without a personal identity code or business ID
- Check whether recipients have active Suomi.fi mailboxes
- Retrieve message events and read received messages
- Upload and download attachments

## Contents

- [Installation](#installation)
  - [Configuration](#configuration)
- [Quick start](#quick-start)
- [Usage](#usage)
  - [Creating a client](#creating-a-client)
  - [Authentication](#authentication)
  - [Checking mailbox status](#checking-mailbox-status)
  - [Sending a multichannel message](#sending-a-multichannel-message)
  - [Sending an electronic message](#sending-an-electronic-message)
  - [Sending paper mail without an identity code](#sending-paper-mail-without-an-identity-code)
  - [Reading events and messages](#reading-events-and-messages)
  - [Error handling](#error-handling)
- [For developers](#for-developers)

## Installation

Requires Python 3.10+ and Django 5.2+.

```
pip install django-helsinki-suomifi-messages
```

No changes to `INSTALLED_APPS` are needed; this is a pure client library.

### Configuration

Add the following to your Django settings:

```python
# Suomi.fi API credentials
SUOMIFI_USERNAME = "your-api-username"
SUOMIFI_PASSWORD = "your-api-password"
SUOMIFI_SERVICE_ID = "your-service-id"

# Posti Messaging Oy credentials (required for paper mail only)
# Obtained during paper mail deployment:
# https://kehittajille.suomi.fi/services/messages/deployment/deployment-of-the-printing-enveloping-and-distribution-service
SUOMIFI_POSTI_EMAIL = "your-posti-email"
SUOMIFI_POSTI_USERNAME = "your-posti-username"
SUOMIFI_POSTI_PASSWORD = "your-posti-password"
```

All settings default to an empty string if not set. `SUOMIFI_USERNAME`,
`SUOMIFI_PASSWORD`, and `SUOMIFI_SERVICE_ID` can also be passed directly to
the relevant client methods. Posti credentials (`SUOMIFI_POSTI_*`) must always
be configured in Django settings.

## Quick start

```python
from suomifi_messages import SuomiFiClient
from suomifi_messages.schemas import Address, BodyFormat

client = SuomiFiClient()  # QA environment; use type="prod" for production
client.login()            # uses SUOMIFI_USERNAME / SUOMIFI_PASSWORD from settings

recipient_address = Address(
    name="Matti Meikäläinen",
    street_address="Esimerkkikatu 1",
    zip_code="00100",
    city="Helsinki",
    country_code="FI"
)
sender_address = Address(
    name="Helsingin kaupunki",
    street_address="Lähettäjänkatu 1",
    zip_code="00100",
    city="Helsinki",
    country_code="FI"
)

with open("letter.pdf", "rb") as f:
    attachment_id = client.upload_attachment("letter.pdf", f)

message_id, external_id = client.send_multichannel_message(
    title="This is a title",
    body="Hello, world!",
    body_format=BodyFormat.TEXT,
    recipient_id="123456-789A",
    recipient_address=recipient_address,
    sender_address=sender_address,
    paper_mail_attachment_id=attachment_id,
)
```

## Usage

### Creating a client

```python
from suomifi_messages import SuomiFiClient

# QA environment (default)
client = SuomiFiClient()

# More explicit
client = SuomiFiClient(type="qa")

# Production environment
client = SuomiFiClient(type="prod")
```

### Authentication

```python
# Uses SUOMIFI_USERNAME and SUOMIFI_PASSWORD from Django settings
client.login()

# Or pass credentials explicitly
client.login(username="user", password="pass")

# Change password; re-login required afterwards (token is invalidated)
client.change_password(current_password="old-pass", new_password="new-pass")
```

### Checking mailbox status

```python
# Check multiple recipients at once
active_ids = client.check_mailboxes(["123456-789A", "987654-321B"])

# Check a single recipient
has_mailbox = client.check_mailbox("123456-789A")  # True / False
```

### Sending a multichannel message

A multichannel message is delivered electronically to recipients with an active
mailbox, or as paper mail to those without:

```python
from suomifi_messages.schemas import Address, BodyFormat

recipient_address = Address(
    name="Matti Meikäläinen",
    street_address="Esimerkkikatu 1",
    zip_code="00100",
    city="Helsinki",
    country_code="FI"
)
sender_address = Address(
    name="Helsingin kaupunki",
    street_address="Lähettäjänkatu 1",
    zip_code="00100",
    city="Helsinki",
    country_code="FI"
)

# Upload the paper mail attachment first
with open("letter.pdf", "rb") as f:
    attachment_id = client.upload_attachment("letter.pdf", f)

message_id, external_id = client.send_multichannel_message(
    title="Title",
    body="Hello, world!",
    body_format=BodyFormat.TEXT,  # or BodyFormat.MARKDOWN
    recipient_id="123456-789A",
    recipient_address=recipient_address,
    sender_address=sender_address,
    paper_mail_attachment_id=attachment_id,
)
```

All send methods return a `(message_id, external_id)` tuple:

- `message_id`: the Suomi.fi identifier assigned to the message. Use this to
  reply to the message or to look it up via `get_message()`.
- `external_id`: your own identifier for the message, used for idempotency.
  If not provided, a UUID is generated automatically. Sending a message with
  the same `external_id` twice will raise `SuomiFiDuplicateMessageError`.

### Sending an electronic message

Use this to send a new message or reply to a message from an end user:

```python
message_id, external_id = client.send_electronic_message(
    title="Title",
    body="Hello, world!",
    body_format=BodyFormat.TEXT,
    recipient_id="123456-789A",
    reply_to=original_message_id,
    reply_allowed=True,
)
```

### Sending paper mail without an identity code

Use this when the recipient's identity code is not known or not required. The
recipient is identified solely by their postal address. Using the same `Address`
setup as above:

```python
with open("letter.pdf", "rb") as f:
    attachment_id = client.upload_attachment("letter.pdf", f)

message_id, external_id = client.send_paper_mail_without_id(
    recipient_address=recipient_address,
    sender_address=sender_address,
    attachment_id=attachment_id,
)
```

### Reading events and messages

```python
# Fetch events; pass continuation_token back in subsequent calls for pagination
events, continuation_token = client.get_events()
for event in events:
    message = client.get_message(event.metadata.message_id)
    # process message...

# Download an attachment from a received message
content = client.get_attachment(attachment_id)  # bytes
```

### Error handling

```python
from suomifi_messages import (
    SuomiFiAPIError,
    SuomiFiClientError,
    SuomiFiDuplicateMessageError,
    SuomiFiServerError,
)

try:
    message_id, external_id = client.send_electronic_message(...)
except SuomiFiDuplicateMessageError as e:
    # 409: message with this external_id already sent
    # e.message_id contains the original message ID
    existing_id = e.message_id
except SuomiFiClientError as e:
    # 4xx: bad request, mailbox not active, etc.
    print(e.response_body)
except SuomiFiServerError as e:
    # 5xx: retry later
    raise
except SuomiFiAPIError as e:
    # Unexpected non-2xx
    raise
```

The exception hierarchy is:

```
SuomiFiError
└── SuomiFiAPIError
    ├── SuomiFiClientError
    │   └── SuomiFiDuplicateMessageError
    └── SuomiFiServerError
```

## For developers

### Prerequisites

- [Hatch](https://hatch.pypa.io/latest/install/)

### Testing

Run the tests with:

```
hatch test
```

Test all environments in the matrix with:

```
hatch test -a
```

### Available Hatch scripts

| Command | Description | Example |
| --- | --- | --- |
| `hatch run test <args>` | Run pytest directly | `hatch run test -k login` |
| `hatch run lint` | Install and run pre-commit hooks | `hatch run lint` |
| `hatch run manage <args>` | Run Django management commands | `hatch run manage migrate` |

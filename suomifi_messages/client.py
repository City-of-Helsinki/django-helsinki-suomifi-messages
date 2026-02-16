import logging
import typing
import uuid
from urllib.parse import urljoin, urlsplit

import requests
from django.conf import settings

from suomifi_messages.errors import SuomiFiError

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

    def check_mailboxes(self, hetu_list):
        mailbox_activity_request = {"endUsers": [{"id": x} for x in hetu_list]}

        response = self.post("/v1/mailboxes/active", json=mailbox_activity_request)

        return response.json()

    def send_message(
        self,
        title,
        body,
        service_id=None,
        recipient_id=None,
        reply_to=None,
        attachment_ids=None,
        delivery_format: typing.Literal["electronic", "postal", "both"] = "electronic",
        internal_id=None,
        verifiable=False,
        reply_allowed=False,
    ):
        if delivery_format not in ["electronic", "postal", "both"]:
            raise ValueError(
                'Parameter "delivery_format" must be one of the following: '
                f'"electronic", "postal", "both" (got: {delivery_format})'
            )
        attachment_ids = attachment_ids or []
        service_id = service_id or settings.SUOMIFI_SERVICE_ID
        recipient_id = recipient_id or settings.SUOMIFI_TEST_USER_SSN
        internal_id = internal_id or str(uuid.uuid4())

        electronic_msg = {
            "body": body,
            # "attachments": {'fileId': [ x for x in attachment_ids ]},
            "attachments": [],
            "messageServiceType": "Verifiable" if verifiable else "Normal",
            "replyAllowedBy": "Anyone" if reply_allowed else "No one",
            "title": title,
            "notifications": {
                "customisedNewMessageNotification": {
                    "title": {
                        "fi": "string",
                        "sv": "string",
                        "en": "string",
                    },
                    "content": {
                        "fi": "string",
                        "sv": "string",
                        "en": "string",
                    },
                },
                "unreadMessageNotification": {
                    "reminder": "Default reminder",
                },
                "senderDetailsInNotifications": "Organisation and service name",
            },
            "visibility": "Normal",
        }

        if reply_to:
            electronic_msg["inReplyToMessageId"] = reply_to

        paper_msg = {
            "colorPrinting": True,
            "createCoverPage": True,
            "files": {"fileId": [x for x in attachment_ids]},
            "messageServiceType": "Verifiable" if verifiable else "Normal",
            "printingAndEnvelopingService": {
                "postiMessaging": {
                    "contactDetails": {"email": "vastaanottajan@spostiosoite.example"},
                    "password": "posti_username_placeholder",
                    "username": "posti_password_placeholder",
                },
                "costPool": "string",
            },
            "recipient": {
                "address": {
                    "additionalName": "Lisäosoiterivi",
                    "city": "Helsinki",
                    "countryCode": "FI",
                    "name": "Paperipostin vastaanottaja",
                    "streetAddress": "Paperipostin osoite",
                    "zipCode": "Paperipostin postinumero",
                }
            },
            "sender": {
                "address": {
                    "additionalName": "Lisälähettäjä",
                    "city": "Helsinki",
                    "countryCode": "FI",
                    "name": "Helsingin kaupunki",
                    "streetAddress": "Työpajankatu 8",
                    "zipCode": "00100",
                },
            },
        }

        msg_request_head = {
            "externalId": internal_id,  # Identifier in some internal system of our own, checked for duplicates by suomi.fi  # noqa: E501
            "recipient": {
                "id": recipient_id
            },  # HETU or Business ID ("Y-tunnus"?), does not affect paper mail at all
            "sender": {"serviceId": service_id},
        }

        # Electronic message format is always required
        msg_request_head["electronic"] = electronic_msg

        if delivery_format == "postal" or delivery_format == "both":
            msg_request_head["paperMail"] = paper_msg
            path = "/v1/messages"
        else:
            # This endpoint accepts messages without paperMail
            path = "/v1/messages/electronic"

        logger.debug(f"Sending message {msg_request_head}")

        response = self.post(path, json=msg_request_head)

        if response.status_code != requests.codes.ok:
            logger.debug(
                f"Message send request failed with status code {response.status_code}"
            )
            logger.debug(response.json())
            raise SuomiFiError("Message send request failed")

        return response.json()

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

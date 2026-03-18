import pytest
import requests

from suomifi_messages.client import (
    SUOMIFI_BASE_URL,
    SUOMIFI_QA_BASE_URL,
    SuomiFiClient,
)
from suomifi_messages.errors import (
    SuomiFiAPIError,
    SuomiFiClientError,
    SuomiFiDuplicateMessageError,
    SuomiFiServerError,
)


@pytest.mark.parametrize(
    "env_type,expected_url",
    [
        ("qa", SUOMIFI_QA_BASE_URL),
        ("prod", SUOMIFI_BASE_URL),
    ],
)
def test_init_environment(env_type, expected_url):
    client = SuomiFiClient(type=env_type)

    assert client.base_url == expected_url
    assert isinstance(client.session, requests.Session)


def test_init_default_is_qa():
    client = SuomiFiClient()

    assert client.base_url == SUOMIFI_QA_BASE_URL


def test_init_invalid_type_raises_error():
    with pytest.raises(
        TypeError, match='Invalid type. Allowed values are "prod" and "qa"'
    ):
        SuomiFiClient(type="invalid")  # type: ignore[arg-type]


def test_hostname_property(client):
    assert client.hostname == "foo-bar.baz.test"


@pytest.mark.parametrize("path", ["/v1/endpoint", "v1/endpoint"])
@pytest.mark.parametrize("base_url", ["https://foo.bar/", "https://foo.bar"])
def test_url_method(path, base_url):
    client = SuomiFiClient()
    client.base_url = base_url

    url = client.url(path)

    assert url == "https://foo.bar/v1/endpoint"


def test_409_raises_duplicate_message_error_with_message_id(client, make_response):
    response = make_response(409, {"messageId": 12345})

    with pytest.raises(SuomiFiDuplicateMessageError) as exc_info:
        client._raise_for_status(response, "Test error")

    assert exc_info.value.message_id == 12345


def test_409_raises_duplicate_message_error_without_message_id(client, make_response):
    response = make_response(409, {"error": "conflict"})

    with pytest.raises(SuomiFiDuplicateMessageError) as exc_info:
        client._raise_for_status(response, "Test error")

    assert exc_info.value.message_id is None


def test_4xx_raises_client_error(client, make_response):
    response = make_response(400, {"error": "bad request"})

    with pytest.raises(SuomiFiClientError):
        client._raise_for_status(response, "Test error")


def test_5xx_raises_server_error(client, make_response):
    response = make_response(500, {"error": "server error"})

    with pytest.raises(SuomiFiServerError):
        client._raise_for_status(response, "Test error")


def test_2xx_does_not_raise(client, make_response):
    response = make_response(200, {"ok": True})

    client._raise_for_status(response, "Test error")  # should not raise


def test_3xx_raises_api_error(client, make_response):
    response = make_response(302, {})

    with pytest.raises(SuomiFiAPIError):
        client._raise_for_status(response, "Test error")


def test_request_method(client, requests_mock):
    requests_mock.get(client.url("v1/test"), json={"status": "ok"})

    response = client.request("GET", "/v1/test")

    assert response.json() == {"status": "ok"}


def test_get_method(client, requests_mock):
    requests_mock.get(client.url("v1/test"), json={"status": "ok"})

    response = client.get("/v1/test")

    assert response.json() == {"status": "ok"}


def test_get_method_with_params(client, requests_mock):
    requests_mock.get(
        client.url("v1/test"),
        json={"status": "ok"},
    )

    response = client.get("/v1/test", params={"key": "value"})

    assert response.json() == {"status": "ok"}
    assert "key=value" in requests_mock.last_request.url


def test_post_method(client, requests_mock):
    requests_mock.post(client.url("v1/test"), json={"status": "created"})

    response = client.post("/v1/test", json={"data": "test"})

    assert response.json() == {"status": "created"}


def test_post_method_with_data(client, requests_mock):
    requests_mock.post(client.url("v1/test"), json={"status": "created"})

    response = client.post("/v1/test", data={"key": "value"})

    assert response.json() == {"status": "created"}

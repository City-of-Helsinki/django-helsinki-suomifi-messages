import json

import pytest
import requests

from suomifi_messages.client import SuomiFiClient
from suomifi_messages.schemas import Address


@pytest.fixture
def client():
    client = SuomiFiClient()
    client.base_url = "https://foo-bar.baz.test/"
    return client


@pytest.fixture
def make_response():
    """Factory fixture for building requests.Response objects without HTTP mocking."""

    def _make_response(status_code, json_body=None):
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(json_body or {}).encode()
        response.headers["Content-Type"] = "application/json"
        return response

    return _make_response


@pytest.fixture
def recipient_address():
    """Standard recipient address for testing."""
    return Address(
        name="Matti Meikäläinen",
        street_address="Esimerkkikatu 1",
        zip_code="00100",
        city="Helsinki",
        country_code="FI",
    )


@pytest.fixture
def sender_address():
    """Standard sender address for testing."""
    return Address(
        name="Helsingin kaupunki",
        street_address="Lähettäjänkatu 1",
        zip_code="00100",
        city="Helsinki",
        country_code="FI",
    )

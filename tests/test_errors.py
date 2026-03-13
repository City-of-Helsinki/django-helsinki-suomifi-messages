from suomifi_messages.errors import (
    SuomiFiAPIError,
    SuomiFiClientError,
    SuomiFiDuplicateMessageError,
    SuomiFiError,
    SuomiFiServerError,
)


def test_suomifi_error_is_exception():
    """Test that SuomiFiError is an Exception."""
    error = SuomiFiError("Test error")

    assert isinstance(error, Exception)
    assert str(error) == "Test error"


def test_suomifi_api_error():
    """Test SuomiFiAPIError basic functionality."""
    error = SuomiFiAPIError("Request failed", response_body={"error": "details"})

    assert isinstance(error, SuomiFiError)
    assert str(error) == "Request failed"
    assert error.response_body == {"error": "details"}


def test_suomifi_client_error():
    """Test SuomiFiClientError basic functionality."""
    error = SuomiFiClientError("Bad request", response_body={"error": "invalid"})

    assert isinstance(error, SuomiFiAPIError)
    assert str(error) == "Bad request"
    assert error.response_body == {"error": "invalid"}


def test_suomifi_duplicate_message_error():
    """Test SuomiFiDuplicateMessageError basic functionality."""
    error = SuomiFiDuplicateMessageError(
        "Duplicate", message_id=12345, response_body={"messageId": 12345}
    )

    assert isinstance(error, SuomiFiClientError)
    assert isinstance(error, SuomiFiAPIError)
    assert str(error) == "Duplicate"
    assert error.message_id == 12345
    assert error.response_body == {"messageId": 12345}


def test_suomifi_server_error():
    """Test SuomiFiServerError basic functionality."""
    error = SuomiFiServerError("Server error", response_body={"error": "internal"})

    assert isinstance(error, SuomiFiAPIError)
    assert str(error) == "Server error"
    assert error.response_body == {"error": "internal"}

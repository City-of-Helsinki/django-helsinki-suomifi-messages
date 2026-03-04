from suomifi_messages.errors import SuomiFiAPIError, SuomiFiError


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

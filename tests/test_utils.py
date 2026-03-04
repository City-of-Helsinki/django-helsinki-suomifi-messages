from unittest.mock import Mock

from suomifi_messages.utils import safe_get_response_body


class TestSafeGetResponseBody:
    """Test safe_get_response_body utility function."""

    def test_returns_dict_for_valid_json(self):
        """Test that valid JSON is returned as a dict."""
        response = Mock()
        response.json.return_value = {"status": "ok", "code": 200}

        result = safe_get_response_body(response)

        assert result == {"status": "ok", "code": 200}
        response.json.assert_called_once()

    def test_returns_text_on_json_parse_failure(self):
        """Test that text is returned when JSON parsing fails."""
        response = Mock()
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "<html>Error page</html>"

        result = safe_get_response_body(response)

        assert result == "<html>Error page</html>"
        response.json.assert_called_once()

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from suomifi_messages.utils import parse_iso_datetime, safe_get_response_body


def test_safe_get_response_body_returns_dict_for_valid_json():
    response = Mock()
    response.json.return_value = {"status": "ok", "code": 200}

    result = safe_get_response_body(response)

    assert result == {"status": "ok", "code": 200}
    response.json.assert_called_once()


def test_safe_get_response_body_returns_text_on_json_parse_failure():
    response = Mock()
    response.json.side_effect = ValueError("Invalid JSON")
    response.text = "<html>Error page</html>"

    result = safe_get_response_body(response)

    assert result == "<html>Error page</html>"
    response.json.assert_called_once()


@pytest.mark.parametrize(
    "iso_string,expected",
    [
        # 'Z' suffix (main API use case)
        (
            "2024-01-01T12:00:00Z",
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        # +00:00 timezone
        (
            "2024-01-01T12:00:00+00:00",
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        # Non-UTC timezone
        (
            "2024-06-15T14:30:45+02:00",
            datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone(timedelta(hours=2))),
        ),
    ],
)
def test_parse_iso_datetime(iso_string, expected):
    result = parse_iso_datetime(iso_string)

    assert result == expected
    assert result.tzinfo is not None

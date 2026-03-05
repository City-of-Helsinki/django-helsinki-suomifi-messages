from datetime import datetime

import requests


def safe_get_response_body(response: requests.Response):
    """Get response body as JSON if possible, otherwise as text."""
    try:
        return response.json()
    except Exception:
        return response.text


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime string to datetime object.

    Handles 'Z' suffix for UTC timezone which Python 3.10's fromisoformat()
    doesn't support. Other ISO 8601 formats are passed through to fromisoformat().

    :param iso_string: ISO 8601 datetime string (e.g., "2024-01-01T12:00:00Z")
    :returns: datetime object (timezone-aware if input has timezone info)
    :rtype: datetime
    """
    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))

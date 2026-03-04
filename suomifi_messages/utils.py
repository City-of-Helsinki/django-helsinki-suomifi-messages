import requests


def safe_get_response_body(response: requests.Response):
    """Get response body as JSON if possible, otherwise as text."""
    try:
        return response.json()
    except Exception:
        return response.text

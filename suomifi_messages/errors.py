class SuomiFiError(Exception):
    pass


class SuomiFiAPIError(SuomiFiError):
    """Exception for API request failures with response body details."""

    def __init__(self, message: str, response_body=None):
        super().__init__(message)
        self.response_body = response_body


class SuomiFiClientError(SuomiFiAPIError):
    """Exception for 4xx API errors (bad request, unauthorized, etc.)."""


class SuomiFiDuplicateMessageError(SuomiFiClientError):
    """Exception raised when a message with the same external ID already exists (409).

    The original message_id from the first send is available on the exception.
    """

    def __init__(self, message: str, message_id: int | None, response_body=None):
        super().__init__(message, response_body=response_body)
        self.message_id = message_id


class SuomiFiServerError(SuomiFiAPIError):
    """Exception for 5xx API errors. The request should be retried."""

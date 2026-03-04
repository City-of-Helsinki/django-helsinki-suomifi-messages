class SuomiFiError(Exception):
    pass


class SuomiFiAPIError(SuomiFiError):
    """Exception for API request failures with response body details."""

    def __init__(self, message: str, response_body=None):
        super().__init__(message)
        self.response_body = response_body

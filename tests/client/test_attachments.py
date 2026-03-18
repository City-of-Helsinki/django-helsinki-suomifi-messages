import pytest

from suomifi_messages.errors import SuomiFiAPIError


class TestSuomiFiClientGetAttachment:
    """Test SuomiFiClient attachment retrieval functionality."""

    def test_get_attachment_success(self, client, requests_mock):
        """Test successful attachment retrieval."""
        requests_mock.get(
            client.url("v1/attachments/att_123"),
            content=b"Binary attachment content",
            status_code=200,
        )

        result = client.get_attachment("att_123")

        assert result == b"Binary attachment content"

    def test_get_attachment_raises_on_error(self, client, requests_mock):
        """Test that get_attachment raises on HTTP error."""
        requests_mock.get(
            client.url("v1/attachments/nonexistent"),
            status_code=404,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to retrieve attachment"):
            client.get_attachment("nonexistent")


class TestSuomiFiClientUploadAttachment:
    """Test SuomiFiClient attachment upload functionality."""

    def test_upload_attachment(self, client, requests_mock):
        """Test uploading an attachment returns the attachment ID and sends filename."""
        attachment_id = "550e8400-e29b-41d4-a716-446655440000"
        requests_mock.post(
            client.url("/v2/attachments"),
            json={"attachmentId": attachment_id},
            status_code=201,
        )

        result = client.upload_attachment("document.pdf", b"file content")

        assert result == attachment_id
        assert b"document.pdf" in requests_mock.last_request.body

    def test_upload_attachment_failure(self, client, requests_mock):
        """Test that a non-2xx response raises SuomiFiAPIError."""
        requests_mock.post(
            client.url("/v2/attachments"),
            json={"error": "Unsupported media type"},
            status_code=415,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to upload attachment"):
            client.upload_attachment("document.xyz", b"file content")

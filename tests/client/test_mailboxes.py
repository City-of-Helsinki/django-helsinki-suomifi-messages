import pytest

from suomifi_messages.errors import SuomiFiAPIError


class TestSuomiFiClientCheckMailboxes:
    """Test SuomiFiClient mailbox checking functionality."""

    @pytest.mark.parametrize(
        "input_ids,expected_result",
        [
            # Some recipients have active mailboxes
            (
                ["123456-789A", "987654-321B", "111111-222C"],
                ["123456-789A", "987654-321B"],
            ),
            # All recipients have active mailboxes
            (["123456-789A", "987654-321B"], ["123456-789A", "987654-321B"]),
            # No recipients have active mailboxes
            (["123456-789A", "987654-321B"], []),
            # Single recipient with active mailbox
            (["123456-789A"], ["123456-789A"]),
            # Empty input list
            ([], []),
        ],
    )
    def test_check_mailboxes_responses(
        self, client, requests_mock, input_ids, expected_result
    ):
        """Test mailbox check with various response scenarios."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"endUsersWithActiveMailbox": [{"id": id} for id in expected_result]},
            status_code=200,
        )

        result = client.check_mailboxes(input_ids)

        assert result == expected_result
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": id} for id in input_ids]
        }

    def test_check_mailboxes_error(self, client, requests_mock):
        """Test mailbox check request failure raises SuomiFiAPIError."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"reason": "Bad request"},
            status_code=400,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to check mailbox status"):
            client.check_mailboxes(["123456-789A"])


class TestSuomiFiClientCheckMailbox:
    """Test SuomiFiClient single mailbox checking functionality."""

    def test_check_mailbox_active(self, client, requests_mock):
        """Test checking mailbox that is active returns True."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"endUsersWithActiveMailbox": [{"id": "123456-789A"}]},
            status_code=200,
        )

        result = client.check_mailbox("123456-789A")

        assert result is True
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": "123456-789A"}]
        }

    def test_check_mailbox_inactive(self, client, requests_mock):
        """Test checking mailbox that is inactive returns False."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"endUsersWithActiveMailbox": []},
            status_code=200,
        )

        result = client.check_mailbox("987654-321B")

        assert result is False
        assert requests_mock.last_request.json() == {
            "endUsers": [{"id": "987654-321B"}]
        }

    def test_check_mailbox_error(self, client, requests_mock):
        """Test single mailbox check request failure raises SuomiFiAPIError."""
        requests_mock.post(
            client.url("v1/mailboxes/active"),
            json={"reason": "Bad request"},
            status_code=400,
        )

        with pytest.raises(SuomiFiAPIError, match="Failed to check mailbox status"):
            client.check_mailbox("123456-789A")

import pytest
import requests
import responses

from securehst_webhook_notifier.main import notify_webhook, send_webhook_message


@pytest.fixture
def mock_webhook_url():
    return "https://test.webhook.url/path"


@responses.activate
def test_send_webhook_message_discord(mock_webhook_url):
    # Setup response
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Test function
    send_webhook_message(mock_webhook_url, "Test message", "discord")

    # Verify
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == mock_webhook_url
    assert responses.calls[0].request.body == b'{"content": "Test message"}'


@responses.activate
def test_send_webhook_message_mattermost(mock_webhook_url):
    # Setup response
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Test function
    send_webhook_message(mock_webhook_url, "Test message", "mattermost")

    # Verify
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == mock_webhook_url
    assert responses.calls[0].request.body == b'{"text": "Test message"}'


@responses.activate
def test_send_webhook_message_slack(mock_webhook_url):
    # Setup response
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Test function
    send_webhook_message(mock_webhook_url, "Test message", "slack")

    # Verify
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == mock_webhook_url
    assert responses.calls[0].request.body == b'{"text": "Test message"}'


def test_send_webhook_message_invalid_platform(mock_webhook_url):
    with pytest.raises(ValueError, match="Unsupported platform 'invalid' for webhook messaging."):
        send_webhook_message(mock_webhook_url, "Test message", "invalid")


@responses.activate
def test_send_webhook_message_request_exception(mock_webhook_url):
    # Setup response to fail
    responses.add(responses.POST, mock_webhook_url, json={"error": "Internal server error"}, status=500)

    with pytest.raises(requests.RequestException):
        send_webhook_message(mock_webhook_url, "Test message", "slack")


@responses.activate
def test_notify_webhook_success(mock_webhook_url):
    # Setup responses for start and end notifications
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Create decorated function
    @notify_webhook(mock_webhook_url, "test_function")
    def sample_function():
        return "Function executed successfully"

    # Execute function
    result = sample_function()

    # Verify function result
    assert result == "Function executed successfully"

    # Verify webhook calls
    assert len(responses.calls) == 2
    start_body = responses.calls[0].request.body.decode()
    end_body = responses.calls[1].request.body.decode()

    # Use Unicode escape sequence or match partial text without emoji
    assert "Automation has started" in start_body
    assert "Automation has completed successfully" in end_body
    assert "Function Caller: test_function" in start_body
    assert "Function Caller: test_function" in end_body


@responses.activate
def test_notify_webhook_with_custom_message(mock_webhook_url):
    # Setup responses
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Create decorated function
    @notify_webhook(mock_webhook_url, "test_function", custom_message="Custom message!")
    def sample_function():
        return "Done"

    # Execute function
    sample_function()

    # Verify webhook calls
    assert len(responses.calls) == 2
    assert "Return Message: Done" in responses.calls[1].request.body.decode()


@responses.activate
def test_notify_webhook_with_exception(mock_webhook_url):
    # Setup responses
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Create decorated function that raises an exception
    @notify_webhook(mock_webhook_url, "test_function_error")
    def failing_function():
        raise ValueError("Test error message")

    # Execute function and expect exception
    with pytest.raises(ValueError, match="Test error message"):
        failing_function()

    # Verify webhook calls
    assert len(responses.calls) == 2
    start_body = responses.calls[0].request.body.decode()
    error_body = responses.calls[1].request.body.decode()

    assert "Automation has started" in start_body
    assert "Automation has crashed" in error_body
    assert "Error: Test error message" in error_body


@responses.activate
def test_notify_webhook_with_sql_error(mock_webhook_url):
    # Setup responses
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Create decorated function that raises an SQL error
    @notify_webhook(mock_webhook_url, "test_sql_error")
    def sql_error_function():
        raise ValueError("Database error [SQL: SELECT * FROM table WHERE id = 123] details")

    # Execute function and expect exception
    with pytest.raises(ValueError):
        sql_error_function()

    # Verify webhook calls
    assert len(responses.calls) == 2
    error_message = responses.calls[1].request.body.decode()

    # More precise assertions
    assert "Automation has crashed" in error_message

    # Check for sanitized error - it might include "Database error" and "details" separately
    assert "Database error" in error_message
    assert "details" in error_message
    # Verify SQL statement is removed
    assert "[SQL:" not in error_message
    assert "SELECT * FROM table WHERE id = 123" not in error_message


@responses.activate
def test_notify_webhook_with_user_mention(mock_webhook_url):
    # Setup responses
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    # Test with Mattermost
    @notify_webhook(mock_webhook_url, "test_function", platform="mattermost", user_id="user123")
    def failing_mattermost_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        failing_mattermost_function()

    assert "@user123" in responses.calls[1].request.body.decode()

    # Reset responses
    responses.reset()

    # Test with Slack
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)
    responses.add(responses.POST, mock_webhook_url, json={"success": True}, status=200)

    @notify_webhook(mock_webhook_url, "test_function", platform="slack", user_id="user123")
    def failing_slack_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        failing_slack_function()

    assert "<@user123>" in responses.calls[1].request.body.decode()


def test_notify_webhook_invalid_platform():
    with pytest.raises(ValueError, match="Unsupported platform 'invalid'"):

        @notify_webhook("https://example.com", "test", platform="invalid")
        def test_func():
            pass

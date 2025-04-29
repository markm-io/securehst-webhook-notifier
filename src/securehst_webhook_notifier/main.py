import re
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

import requests


def notify_webhook(
    webhook_url: str,
    func_identifier: str,
    platform: str = "mattermost",
    user_id: str | None = None,
    custom_message: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that sends start, end, and error notifications via a webhook.

    Args:
        webhook_url (str): The webhook URL to send notifications to.
        func_identifier (str): A string identifier representing the function being decorated.
        platform (str, optional): Messaging platform type: "mattermost", "slack",
        or "discord". Defaults to "mattermost".
        user_id (Optional[str], optional): User ID or username to mention on errors.
        Platform-specific formatting is applied. Defaults to None.
        custom_message (Optional[str], optional): Optional custom message to include.
        Defaults to None.

    Returns:
        Callable: A wrapped function with webhook notifications.

    """
    platform = platform.lower()

    if platform not in {"mattermost", "slack", "discord"}:
        raise ValueError(f"Unsupported platform '{platform}'. Supported platforms are: mattermost, slack, discord.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = datetime.now()
            start_message = (
                f"⏳ Automation has started.\n"
                f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Function Caller: {func_identifier}"
            )
            send_webhook_message(webhook_url, start_message, platform)

            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = end_time - start_time

                custom_message_str = f"\nReturn Message: {result}" if result else ""
                end_message = (
                    f"✅ Automation has completed successfully.\n"
                    f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Duration: {duration}\n"
                    f"Function Caller: {func_identifier}"
                    f"{custom_message_str}"
                )
                send_webhook_message(webhook_url, end_message, platform)
                return result

            except Exception as err:
                end_time = datetime.now()
                duration = end_time - start_time

                error_message = str(err)
                # Attempt to clean long SQL errors if detected
                if "SQL: " in error_message:
                    error_message = re.sub(r"\[SQL: .*?\]", "", error_message).strip()

                # User mention formatting per platform
                user_mention = ""
                if user_id:
                    if platform == "slack":
                        user_mention = f"<@{user_id}> "
                    elif platform in {"mattermost", "discord"}:
                        user_mention = f"@{user_id} "

                error_message_text = (
                    f"{user_mention}\n"
                    f"🆘 Automation has crashed.\n"
                    f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Duration: {duration}\n"
                    f"Function Caller: {func_identifier}\n"
                    f"Error: {error_message}"
                )
                send_webhook_message(webhook_url, error_message_text, platform)
                raise err

        return wrapper

    return decorator


def send_webhook_message(webhook_url: str, message: str, platform: str) -> None:
    """
    Sends a formatted message to the specified webhook URL.

    Args:
        webhook_url (str): The destination webhook URL.
        message (str): The message content to send.
        platform (str): Platform type to determine payload structure
        ("mattermost", "slack", "discord").

    Raises:
        ValueError: If the platform is unsupported.
        requests.RequestException: If the HTTP request fails.

    """
    platform = platform.lower()

    if platform == "discord":
        payload = {"content": message}
    elif platform in {"mattermost", "slack"}:
        payload = {"text": message}
    else:
        raise ValueError(f"Unsupported platform '{platform}' for webhook messaging.")

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to send webhook notification to {platform}: {e}")
        raise

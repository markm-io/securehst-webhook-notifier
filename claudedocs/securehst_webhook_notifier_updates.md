# securehst-webhook-notifier Library Updates

## Overview

This document outlines the necessary updates to the `securehst-webhook-notifier` library to support Prefect flow lifecycle notifications.

## New Decorator: @prefect_notify_webhook

### Function Signature

```python
def prefect_notify_webhook(
    webhook_url: str,
    display_name: str,
    user_id: str = None,
    silent_success: bool = True,
    start_message: str = None,
    success_message: str = None,
    failure_message: str = None
):
    """
    Decorator to add comprehensive Prefect flow notifications.

    Args:
        webhook_url: The webhook URL to send notifications to
        display_name: Human readable name for the flow (e.g., "D. Miller & Associates - dmiller-etl")
        user_id: User to mention on failures (e.g., "securehst")
        silent_success: If True, success notifications won't mention users
        start_message: Custom start message (default: "🚀 {display_name} started")
        success_message: Custom success message (default: "✅ {display_name} completed successfully")
        failure_message: Custom failure message (default: "❌ {display_name} failed")

    Returns:
        Decorated function with Prefect event hooks registered
    """
```

### Implementation Requirements

#### 1. Required Prefect Event Hooks

The decorator must register the following Prefect event hooks:

```python
from prefect.events import (
    on_failure,
    on_completion,
    on_crashed,
    on_cancellation,
    on_timed_out
)
```

#### 2. Notification Logic

**Flow Start Notification:**

- Send when flow begins execution
- Format: "🚀 {display_name} started"
- No user mentions

**Success Notification:**

- Send via `on_completion` hook
- Format: "✅ {display_name} completed successfully"
- Silent (no user mentions) if `silent_success=True`
- Mention user if `silent_success=False`

**Failure Notifications:**

- Send via `on_failure`, `on_crashed`, `on_cancellation`, `on_timed_out` hooks
- Format: "@{user_id} ❌ {display_name} {failure_type}"
- Always mention user_id if provided
- Failure types:
  - "failed" (on_failure)
  - "crashed" (on_crashed)
  - "was cancelled" (on_cancellation)
  - "timed out" (on_timed_out)

#### 3. HTTP Client Requirements

- Use existing HTTP client from the library
- Implement error swallowing (don't affect flow state on notification failures)
- Support JSON payload format compatible with Mattermost/Slack webhooks
- Timeout handling (suggest 10 second timeout)

#### 4. Decorator Implementation Pattern

```python
def prefect_notify_webhook(webhook_url, display_name, user_id=None, silent_success=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Send start notification
            send_start_notification(webhook_url, display_name)

            # Register event hooks
            register_completion_hook(webhook_url, display_name, user_id, silent_success)
            register_failure_hooks(webhook_url, display_name, user_id)

            # Execute original function
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 5. Helper Functions Needed

```python
def send_notification(webhook_url: str, message: str):
    """Send HTTP POST notification with error handling"""

def register_completion_hook(webhook_url, display_name, user_id, silent_success):
    """Register on_completion hook"""

def register_failure_hooks(webhook_url, display_name, user_id):
    """Register on_failure, on_crashed, on_cancellation, on_timed_out hooks"""

def send_start_notification(webhook_url, display_name):
    """Send flow start notification"""
```

## Backward Compatibility

The existing `@notify_webhook` decorator must remain unchanged and functional. The new `@prefect_notify_webhook` decorator is an addition, not a replacement.

## Usage Example

```python
from prefect import flow
from securehst_webhook_notifier import prefect_notify_webhook

@flow(name="my-etl-pipeline")
@prefect_notify_webhook(
    webhook_url="https://mattermost.apphst.com/hooks/abc123",
    display_name="D. Miller & Associates - ETL Pipeline",
    user_id="securehst",
    silent_success=True
)
def my_etl_flow():
    # ETL logic here
    pass
```

## Testing Requirements

1. **Unit Tests**: Test all notification scenarios
2. **Integration Tests**: Test with actual Prefect flows
3. **Error Handling Tests**: Ensure webhook failures don't break flows
4. **Backward Compatibility Tests**: Ensure existing decorator still works

## Dependencies

The library will need to add Prefect as a dependency:

```toml
dependencies = [
    "prefect>=2.0.0",
    # ... existing dependencies
]
```

## Configuration Schema Support

The decorator should support the configuration schema used by dmiller-etl:

```yaml
notification:
  url: "https://mattermost.apphst.com/hooks/z46qms5a83gbtqj6jk8np39sxh"
  user_id: "securehst"
  business: "D. Miller & Associates"
  organization: "" # Optional
  app: "dmiller-etl"
```

## Implementation Priority

1. **High Priority**: Core decorator with basic start/success/failure notifications
2. **Medium Priority**: All Prefect event hooks (crashed, cancelled, timed out)
3. **Low Priority**: Custom message templates and advanced configuration options

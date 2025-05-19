# Narratix Logging System

This document outlines our logging system, recent improvements, and best practices.

## Overview

Our logging system is designed to:
1. Capture all application events in a structured format
2. Log all API requests and responses with full details
3. Provide session-based organization of logs
4. Support both JSON and human-readable formats

## Recent Improvements

We recently improved the logging system to capture full API requests and responses:

1. **Enhanced Error Handling**: All API errors now include full response details including status code, headers, and response body.
2. **Full Request/Response Logging**: API client calls capture complete request and response payloads.
3. **Automatic HTTP Client Logging**: A new logging transport for httpx clients automatically logs all HTTP traffic.

## Using the Logging System

### Getting a Logger

```python
from utils.logging import get_logger

# Regular logger
logger = get_logger(__name__)

# API logger with enhanced request/response tracking
api_logger = get_logger(__name__, is_api=True)
```

### Logging API Requests and Responses

```python
# Manually log requests and responses
api_logger.log_request(
    method="POST",
    url="https://api.example.com/endpoint",
    headers={"Content-Type": "application/json"},
    body=request_payload
)

api_logger.log_response(
    status_code=response.status_code,
    headers=dict(response.headers),
    body=response.json()  # or response.text
)
```

### Using the HTTP Client with Automatic Logging

```python
from utils.http_client import create_client, create_async_client

# Synchronous client
client = create_client()
response = client.post("https://api.example.com/endpoint", json=payload)
# All requests and responses are automatically logged

# Async client
async_client = create_async_client()
response = await async_client.post("https://api.example.com/endpoint", json=payload)
# All requests and responses are automatically logged
```

## Log File Structure

Logs are organized by date with session-specific files:

```
logs/
  20250507/
    test_session_20250507_192638_20250507_192638.log
    voice_generation_20250507_143015.log
```

## Viewing Logs

Logs are stored in JSON format by default, which allows for easier parsing, filtering, and analysis.

Example log entry:
```json
{
  "timestamp": "2025-05-07 19:26:38,072",
  "level": "INFO",
  "name": "root",
  "message": "Started logging session: test_session_20250507_192638_20250507_192638 -> /Users/anatburg/Narratix2.0/logs/20250507/test_session_20250507_192638_20250507_192638.log",
  "session_id": "test_session_20250507_192638_20250507_192638",
  "http_request": {
    "method": "POST",
    "url": "https://api.hume.ai/v0/tts",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "[REDACTED]"
    },
    "body": {
      "utterances": [],
      "format": "mp3"
    }
  },
  "http_response": {
    "status_code": 422,
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "detail": [
        {
          "loc": ["body", "utterances"],
          "msg": "List should have at least 1 item after validation, not 0",
          "type": "too_short",
          "input": [],
          "ctx": {
            "field_type": "List",
            "min_length": 1,
            "actual_length": 0
          }
        }
      ]
    }
  }
}
```

## Best Practices

1. **Always use the `get_logger` function** to create loggers, not Python's built-in logging.
2. **Use `is_api=True`** when creating loggers for code that makes API calls.
3. **Prefer the HTTP client** from `utils.http_client` for automatic logging.
4. **Log sensitive data carefully** - API keys, passwords, and other sensitive information are automatically redacted from headers.
5. **Include context** when possible to improve log searchability.

## Advanced Features

### Session Management

You can start a new logging session explicitly:

```python
from utils.logging import SessionLogger

session_id = SessionLogger.start_session(
    session_name="custom_operation", 
    format_type="json"  # or "human_readable"
)
```

### Context-Based Logging

Add context to help filter and correlate logs:

```python
logger = get_logger(__name__, context={
    "operation": "speech_generation",
    "text_id": text_id,
    "user_id": user_id
})
``` 
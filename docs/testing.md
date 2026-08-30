# CTFVigil Testing Guide

This document describes the testing setup, execution instructions, and test coverage for the CTFVigil project.

## Running Tests

Run the test suite using `pytest` inside the virtual environment:

```bash
.venv/bin/python -m pytest tests/
```

To run individual test files:

```bash
.venv/bin/python -m pytest tests/test_utils.py
.venv/bin/python -m pytest tests/test_client.py
```

---

## Test Suite Overview

### 1. Utility Functions (`tests/test_utils.py`)
Tests helper functions in `ctfvigil/utils.py` responsible for timestamp conversion, description formatting, and Discord embed generation:

- **`TestIsoToTimestamp`**:
  - Valid ISO 8601 parsing with UTC `Z` suffix, positive (`+02:00`), negative (`-05:00`) offsets, and naive timestamps.
  - Graceful handling (`None` return) for falsy strings, malformed dates, invalid ranges, and empty containers.
  - Explicit error handling verification for unexpected types.
- **`TestFormatDescription`**:
  - Default fallback (`"No description provided."`) for empty or whitespace-only inputs.
  - First-paragraph extraction across standard (`\n\n`) and Windows (`\r\n\r\n`) paragraph separators.
  - Trailing period stripping prior to adding `...` truncation indicator.
- **`TestCreateEventEmbed`**:
  - Full payload Discord embed construction (title, description, timestamp fields, location, organizer).
  - Minimal payload fallback defaults (`Unnamed CTF`, `Unknown` fields, field omission for missing dates).
  - URL fallback behavior (`ctftime_url` when `url` is missing/empty).

### 2. CTFtime API Client (`tests/test_client.py`)
Tests `CTFTimeClient` in `ctfvigil/client.py` using mocked HTTP interactions:

- **`TestCTFTimeClient`**:
  - Default and custom `User-Agent` header initialization.
  - Request execution and query parameter formatting (`limit`, `start_timestamp`).
  - Session lifecycle management (verifying automatically created `ClientSession` instances are closed).
  - Error propagation for non-200 HTTP responses (e.g. HTTP status 500) and network failures (`aiohttp.ClientError`).

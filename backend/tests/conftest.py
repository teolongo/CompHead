"""Pytest configuration for backend agent tests."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import os
import sys
import time
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Pause between integration tests to avoid LLM rate limits (~1 req/s on free tiers).
DEFAULT_INTEGRATION_DELAY_SECONDS = 3.0


def has_integration_env() -> bool:
    return bool(os.environ.get("MOCK_API_TOKEN") and os.environ.get("LLM_API_KEY"))


def integration_delay_seconds() -> float:
    raw = os.environ.get("INTEGRATION_TEST_DELAY_SECONDS", "")
    if raw.strip():
        return float(raw)
    return DEFAULT_INTEGRATION_DELAY_SECONDS


def is_rate_limit_response(answer: str) -> bool:
    lower = answer.lower()
    return "rate limit" in lower or "error code: 429" in lower


@pytest.fixture(autouse=True)
def _pace_integration_tests(request: pytest.FixtureRequest) -> None:
    """Serial spacing between @pytest.mark.integration tests."""
    marker = request.node.get_closest_marker("integration")
    if marker is None:
        return

    session = request.session
    if getattr(session, "_integration_test_count", 0) > 0:
        time.sleep(integration_delay_seconds())
    session._integration_test_count = getattr(session, "_integration_test_count", 0) + 1

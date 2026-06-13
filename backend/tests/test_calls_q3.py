"""Tests for Calls tools (Q3: NordSpesa last call complaint and lot)."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

Q3_QUESTION = (
    "In the last call with NordSpesa S.p.A. (CUST-0137), what was the complaint "
    "and which lot did it concern?"
)

CALL_ROWS = [
    {
        "call_id": "CALL-57100",
        "customer_id": "CUST-0137",
        "call_date": "2026-01-10",
        "type": "support",
        "outcome": "resolved",
    },
    {
        "call_id": "CALL-58020",
        "customer_id": "CUST-0137",
        "call_date": "2026-02-18",
        "type": "support",
        "outcome": "complaint_open",
    },
    {
        "call_id": "CALL-57550",
        "customer_id": "CUST-0137",
        "call_date": "2026-02-01",
        "type": "sales",
        "outcome": "follow_up",
    },
]

TRANSCRIPT_SEGMENTS = [
    {
        "speaker": "NordSpesa buyer",
        "text": "We received broken pasta in the last delivery.",
    },
    {
        "speaker": "Al Dente support",
        "text": "Can you confirm the lot number LOT-2026-0658?",
    },
]


def _has_integration_env() -> bool:
    return bool(os.environ.get("MOCK_API_TOKEN") and os.environ.get("LLM_API_KEY"))


@patch("agent.tools.calls.get_client")
def test_list_calls_most_recent_call_id(mock_get_client: MagicMock) -> None:
    """list_calls with customer_id CUST-0137 returns CALL-58020 as most recent."""
    from agent.tools.calls import run_calls_tool

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "data": CALL_ROWS,
        "pagination": {"total": 3, "offset": 0, "limit": 50},
    }
    mock_get_client.return_value = mock_client

    result_json, source = run_calls_tool("list_calls", {"customer_id": "CUST-0137"})
    result = json.loads(result_json)

    assert source == "calls"
    assert result["most_recent_call_id"] == "CALL-58020"
    assert result["most_recent_call_date"] == "2026-02-18"
    assert result["customer_id"] == "CUST-0137"
    mock_client.get.assert_called_once_with(
        "/calls",
        params={"customer_id": "CUST-0137"},
    )


@patch("agent.tools.calls.get_client")
def test_search_transcript_extracts_complaint_and_lot(mock_get_client: MagicMock) -> None:
    """search_transcript with search=broken returns complaint_type and lot_id."""
    from agent.tools.calls import run_calls_tool

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "call_id": "CALL-58020",
        "segments": TRANSCRIPT_SEGMENTS,
        "pagination": {"total": 2, "offset": 0, "limit": 50},
    }
    mock_get_client.return_value = mock_client

    result_json, source = run_calls_tool(
        "search_transcript",
        {"call_id": "CALL-58020", "search": "broken"},
    )
    result = json.loads(result_json)

    assert source == "calls/CALL-58020/transcript"
    assert result["call_id"] == "CALL-58020"
    assert result["complaint_type"] == "broken pasta"
    assert result["lot_id"] == "LOT-2026-0658"
    mock_client.get.assert_called_once_with(
        "/calls/CALL-58020/transcript",
        params={"search": "broken"},
    )


@patch("agent.tools.calls.get_client")
def test_search_transcript_caps_matched_segments(mock_get_client: MagicMock) -> None:
    """search_transcript caps matched_segments at 20 even when API returns more."""
    from agent.tools.calls import run_calls_tool

    many_segments = [
        {"speaker": "agent", "text": f"broken pasta mention {index} LOT-2026-0658"}
        for index in range(25)
    ]
    mock_client = MagicMock()
    mock_client.get.return_value = {
        "call_id": "CALL-58020",
        "segments": many_segments,
        "pagination": {"total": 25, "offset": 0, "limit": 50},
    }
    mock_get_client.return_value = mock_client

    result_json, _source = run_calls_tool(
        "search_transcript",
        {"call_id": "CALL-58020", "search": "broken"},
    )
    result = json.loads(result_json)

    assert len(result["matched_segments"]) <= 20


@pytest.mark.integration
@pytest.mark.skipif(not _has_integration_env(), reason="MOCK_API_TOKEN and LLM_API_KEY required")
def test_q3_agent_integration() -> None:
    """Q3 via run_agent mentions broken pasta, LOT-2026-0658, and calls sources."""
    from agent.loop import run_agent

    response = run_agent(Q3_QUESTION)
    answer = response["answer"].lower()

    assert "broken" in answer
    assert "LOT-2026-0658" in response["answer"]
    assert "calls" in response["sources"]
    assert "calls/CALL-58020/transcript" in response["sources"]

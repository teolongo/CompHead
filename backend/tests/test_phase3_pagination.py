"""Phase 3 unit tests: pagination-aware aggregation and Python-side arithmetic.

These tests run without live MOCK_API_TOKEN or LLM_API_KEY. They mock the
low-level ``MockApiClient.get`` and exercise the real ``get_all_pages`` loop so
that aggregate tools must page through every row (not just the first page) and
compute totals/counts in Python.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from unittest.mock import MagicMock, patch

from services.api_client import MockApiClient
from services.config import Settings


def _make_client(get_side_effect: Callable[..., dict]) -> MockApiClient:
    """Build a real MockApiClient with its low-level ``get`` mocked."""
    settings = Settings(
        LLM_BASE_URL="http://test",
        LLM_API_KEY="test",
        MODEL="test",
        MOCK_API_BASE_URL="http://test",
        MOCK_API_TOKEN="test",
        PUBLIC_BASE_URL="http://test",
    )
    client = MockApiClient(settings)
    client.get = MagicMock(side_effect=get_side_effect)  # type: ignore[method-assign]
    return client


# --- get_all_pages helper ------------------------------------------------


def test_get_all_pages_follows_total_and_preserves_params() -> None:
    """get_all_pages pages until pagination.total and never mutates caller params."""

    def fake_get(path: str, params: dict | None = None) -> dict:
        assert path == "/crm/opportunities"
        assert params is not None
        assert params["limit"] == 200
        offset = params.get("offset", 0)
        if offset == 0:
            return {
                "data": [{"id": 1}, {"id": 2}, {"id": 3}],
                "pagination": {"offset": 0, "limit": 200, "total": 5},
            }
        assert offset == 3
        return {
            "data": [{"id": 4}, {"id": 5}],
            "pagination": {"offset": 3, "limit": 200, "total": 5},
        }

    client = _make_client(fake_get)
    caller_params = {"stage": "negotiation"}

    rows = client.get_all_pages("/crm/opportunities", params=caller_params)

    assert len(rows) == 5
    assert [row["id"] for row in rows] == [1, 2, 3, 4, 5]
    # Caller's params dict must be untouched (no limit/offset injected).
    assert caller_params == {"stage": "negotiation"}
    # Two pages requested: offset 0 then offset 3, both with limit 200.
    offsets = [call.args[1].get("offset") if len(call.args) > 1 else call.kwargs["params"].get("offset") for call in client.get.call_args_list]
    assert offsets == [0, 3]


# --- CRM: negotiation opportunities grouped by channel (Q6) --------------

NEG_PAGE_1 = [
    {"opportunity_id": "OPP-001", "stage": "negotiation", "customer_channel": "GDO", "value_eur": 100},
    {"opportunity_id": "OPP-002", "stage": "negotiation", "customer_channel": "distributor", "value_eur": 200},
    {"opportunity_id": "OPP-003", "stage": "negotiation", "customer_channel": "horeca", "value_eur": 300},
]
NEG_PAGE_2 = [
    {"opportunity_id": "OPP-004", "stage": "negotiation", "customer_channel": "GDO", "value_eur": 50},
    {"opportunity_id": "OPP-005", "stage": "negotiation", "customer_channel": "horeca", "value_eur": 25},
]


def test_list_opportunities_group_by_channel_pages_and_sums() -> None:
    """Q6: channel totals sum EVERY negotiation row across pages, computed in Python."""
    from agent.tools.crm import run_crm_tool

    def crm_get(path: str, params: dict | None = None) -> dict:
        assert path == "/crm/opportunities"
        assert params is not None
        assert params["limit"] == 200
        assert params.get("stage") == "negotiation"
        offset = params.get("offset", 0)
        if offset == 0:
            return {"data": NEG_PAGE_1, "pagination": {"offset": 0, "limit": 200, "total": 5}}
        assert offset == 3
        return {"data": NEG_PAGE_2, "pagination": {"offset": 3, "limit": 200, "total": 5}}

    client = _make_client(crm_get)
    with patch("agent.tools.crm.get_client", return_value=client):
        result_json, source = run_crm_tool(
            "list_opportunities",
            {"stage": "negotiation", "group_by": "customer_channel"},
        )

    result = json.loads(result_json)
    assert source == "crm/opportunities"
    assert result["count"] == 5
    grouped = result["grouped_total_value_eur"]
    assert grouped["GDO"] == 150
    assert grouped["distributor"] == 200
    assert grouped["horeca"] == 375
    # Second page was fetched (proves we did not stop at page 1).
    offsets = [
        call.args[1].get("offset") if len(call.args) > 1 else call.kwargs["params"].get("offset")
        for call in client.get.call_args_list
    ]
    assert 3 in offsets


# --- Calls: broken-pasta complaint count (Q11) ---------------------------

BROKEN_IDS = {f"CALL-{i:05d}" for i in range(1, 10)}  # exactly 9 calls match
ALL_CALLS = [
    {"call_id": f"CALL-{i:05d}", "type": "support", "outcome": "complaint_open"}
    for i in range(1, 81)
]


def test_count_calls_by_defect_pages_all_calls_and_counts_in_python() -> None:
    """Q11: page all 80 calls, targeted transcript search, exact count 9 in Python."""
    from agent.tools.calls import run_calls_tool

    def calls_get(path: str, params: dict | None = None) -> dict:
        if path == "/calls":
            assert params is not None
            assert params["limit"] == 200
            offset = params.get("offset", 0)
            if offset == 0:
                return {
                    "data": ALL_CALLS[:50],
                    "pagination": {"offset": 0, "limit": 200, "total": 80},
                }
            assert offset == 50
            return {
                "data": ALL_CALLS[50:80],
                "pagination": {"offset": 50, "limit": 200, "total": 80},
            }
        # Transcript endpoint: must always use a targeted search, never full download.
        assert path.endswith("/transcript")
        assert params is not None and params.get("search")
        call_id = path.split("/")[2]
        if call_id in BROKEN_IDS:
            return {
                "call_id": call_id,
                "segments": [
                    {"speaker": "customer", "text": "the box arrived with broken pasta inside"}
                ],
                "pagination": {"offset": 0, "limit": 20, "total": 1},
            }
        return {"call_id": call_id, "segments": [], "pagination": {"offset": 0, "limit": 20, "total": 0}}

    client = _make_client(calls_get)
    with patch("agent.tools.calls.get_client", return_value=client):
        result_json, source = run_calls_tool(
            "count_calls_by_defect",
            {"defect": "broken pasta"},
        )

    result = json.loads(result_json)
    assert source.startswith("calls")
    assert result["defect"] == "broken pasta"
    assert result["count"] == 9
    assert result["searched_call_count"] == 80
    assert len(result["matching_call_ids_sample"]) <= 10
    # Second page of /calls was fetched.
    list_offsets = [
        (call.args[1] if len(call.args) > 1 else call.kwargs.get("params")) or {}
        for call in client.get.call_args_list
        if (call.args[0] if call.args else call.kwargs.get("path")) == "/calls"
    ]
    assert any(p.get("offset") == 50 for p in list_offsets)

"""Tests for ERP inventory tool (Q2: PAS-PEN-500 below minimum stock)."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

Q2_QUESTION = (
    "Is SKU PAS-PEN-500 (Penne Rigate n.73 - 500g box) below its minimum stock? "
    "Give the on-hand quantity."
)

INVENTORY_ROW = {
    "sku": "PAS-PEN-500",
    "description": "Penne Rigate n.73 - 500g box",
    "type": "finished_good",
    "on_hand": 462,
    "min_stock": 2000,
    "below_min": True,
    "unit": "cartons",
}


def _has_integration_env() -> bool:
    return bool(os.environ.get("MOCK_API_TOKEN") and os.environ.get("LLM_API_KEY"))


@patch("agent.tools.erp.get_client")
def test_get_inventory_below_minimum(mock_get_client: MagicMock) -> None:
    """get_inventory returns pre-computed below_minimum and qty fields for PAS-PEN-500."""
    from agent.tools.erp import run_erp_tool

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "data": [INVENTORY_ROW],
        "pagination": {"total": 1, "offset": 0, "limit": 50},
    }
    mock_get_client.return_value = mock_client

    result_json, source = run_erp_tool("get_inventory", {"search": "PAS-PEN-500"})
    result = json.loads(result_json)

    assert source == "erp/inventory"
    assert result["sku"] == "PAS-PEN-500"
    assert result["below_minimum"] is True
    assert result["on_hand_qty"] == 462
    assert result["minimum_qty"] == 2000
    mock_client.get.assert_called_once_with(
        "/erp/inventory",
        params={"search": "PAS-PEN-500"},
    )


@pytest.mark.integration
@pytest.mark.skipif(not _has_integration_env(), reason="MOCK_API_TOKEN and LLM_API_KEY required")
def test_q2_agent_integration() -> None:
    """Q2 via run_agent mentions below minimum, on-hand 462, and erp/inventory source."""
    from agent.loop import run_agent

    response = run_agent(Q2_QUESTION)
    answer = response["answer"].lower()

    assert "462" in response["answer"]
    assert "below" in answer and "minimum" in answer
    assert "erp/inventory" in response["sources"]

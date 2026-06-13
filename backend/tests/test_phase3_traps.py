"""Phase 3 trap/premise preflight unit tests (offline, no live env).

These tests pin the deterministic correctness preflight that intercepts trap
questions before the LLM loop:

- Q7-style: an unsupported profitability/cost metric on a production lot must
  return an honest "not available" answer without inventing a number.
- Q8-style: an order question naming a missing customer must verify the CRM
  premise (search ``/crm/customers``) and report the customer is not found.

They mock the CRM client so they run fast and offline, and assert the frozen
``/ask`` response schema is preserved (``answer``/``sources``/``verticale`` and
``artifact_url=None``).
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

SCHEMA_KEYS = {"answer", "sources", "verticale", "artifact_url"}
VALID_VERTICALI = {"crm", "erp", "calls", "kb"}

LOT_PROFIT_Q = "What is the profit margin on lot LOT-2026-0658?"
LOT_COST_Q = "Can you tell me the production cost of lot LOT-2025-0123?"
MISSING_CUSTOMER_Q = "What is the status of the order for Supermercati Bianchi?"
EXISTING_CUSTOMER_Q = "What is the status of the order for Primato Supermercati?"
UNRELATED_Q = "What is the shelf life of SKU PAS-SPA-500?"


def _assert_schema(result: dict) -> None:
    assert result is not None, "Expected a preflight answer, got None"
    assert set(result.keys()) >= SCHEMA_KEYS, result
    assert result["artifact_url"] is None
    assert isinstance(result["sources"], list)
    assert result["verticale"] in VALID_VERTICALI


# --- Unsupported lot profitability/cost metric (Q7-style) ----------------


def test_profit_margin_lot_returns_not_available_without_numbers() -> None:
    from agent.correctness import try_answer_correctness_preflight

    result = try_answer_correctness_preflight(LOT_PROFIT_Q)
    _assert_schema(result)

    answer = result["answer"]
    lower = answer.lower()
    assert "not available" in lower or "not stored" in lower, answer
    assert "margin" in lower or "profit" in lower, answer
    assert "lot-2026-0658" in lower, answer
    assert result["verticale"] == "erp", result

    # No invented numeric margin: no percentage and no digits beyond the lot id.
    assert "%" not in answer, answer
    leftover = re.sub(r"LOT-\d{4}-\d{4}", "", answer, flags=re.IGNORECASE)
    assert not re.search(r"\d", leftover), answer


def test_lot_cost_question_is_also_intercepted() -> None:
    from agent.correctness import try_answer_correctness_preflight

    result = try_answer_correctness_preflight(LOT_COST_Q)
    _assert_schema(result)
    lower = result["answer"].lower()
    assert "not available" in lower or "not stored" in lower, result["answer"]
    assert "lot-2025-0123" in lower, result["answer"]


# --- Missing-customer order premise (Q8-style) ---------------------------


def test_missing_customer_verifies_crm_and_reports_not_found() -> None:
    from agent.correctness import try_answer_correctness_preflight

    mock_client = MagicMock()
    mock_client.get_all_pages.return_value = []
    with patch("agent.correctness.get_client", return_value=mock_client):
        result = try_answer_correctness_preflight(MISSING_CUSTOMER_Q)

    _assert_schema(result)
    answer = result["answer"]
    lower = answer.lower()
    assert "bianchi" in lower, answer
    assert any(
        phrase in lower
        for phrase in ("not found", "no customer", "does not exist", "not in the crm")
    ), answer
    assert result["verticale"] == "crm", result
    assert result["sources"] == ["crm/customers"], result

    # CRM premise was actually verified with a name search.
    mock_client.get_all_pages.assert_called_once()
    call = mock_client.get_all_pages.call_args
    assert call.args[0] == "/crm/customers", call
    params = call.kwargs.get("params")
    if params is None and len(call.args) > 1:
        params = call.args[1]
    assert params and "bianchi" in str(params).lower(), call


def test_existing_customer_falls_through_to_llm() -> None:
    from agent.correctness import try_answer_correctness_preflight

    mock_client = MagicMock()
    mock_client.get_all_pages.return_value = [
        {"customer_id": "CUST-0132", "name": "Primato Supermercati S.p.A."}
    ]
    with patch("agent.correctness.get_client", return_value=mock_client):
        result = try_answer_correctness_preflight(EXISTING_CUSTOMER_Q)

    assert result is None, "Existing customers must be handled by the LLM, not abstained"


def test_unrelated_question_returns_none() -> None:
    from agent.correctness import try_answer_correctness_preflight

    assert try_answer_correctness_preflight(UNRELATED_Q) is None


def test_blank_question_returns_none() -> None:
    from agent.correctness import try_answer_correctness_preflight

    assert try_answer_correctness_preflight("   ") is None


# --- run_agent wiring (preflight short-circuits the LLM loop) -------------


def test_run_agent_uses_preflight_for_lot_profit_margin() -> None:
    from agent.loop import run_agent

    result = run_agent(LOT_PROFIT_Q)
    _assert_schema(result)
    lower = result["answer"].lower()
    assert "margin" in lower or "profit" in lower, result["answer"]
    assert result["verticale"] == "erp", result


def test_run_agent_uses_preflight_for_missing_customer() -> None:
    from agent.loop import run_agent

    mock_client = MagicMock()
    mock_client.get_all_pages.return_value = []
    with patch("agent.correctness.get_client", return_value=mock_client):
        result = run_agent(MISSING_CUSTOMER_Q)

    _assert_schema(result)
    assert result["verticale"] == "crm", result
    assert result["sources"] == ["crm/customers"], result
    assert "bianchi" in result["answer"].lower(), result["answer"]

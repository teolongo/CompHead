"""Phase 2 integration battery: Q1-Q4 from SAMPLE_QUESTIONS.md."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

Q1_QUESTION = (
    "How many open opportunities does Primato Supermercati S.p.A. (CUST-0132) have, "
    "and what is their total value?"
)
Q2_QUESTION = (
    "Is SKU PAS-PEN-500 (Penne Rigate n.73 - 500g box) below its minimum stock? "
    "Give the on-hand quantity."
)
Q3_QUESTION = (
    "In the last call with NordSpesa S.p.A. (CUST-0137), what was the complaint "
    "and which lot did it concern?"
)
Q4_QUESTION = (
    "What is the shelf life (TMC) and the declared allergens for "
    "Spaghetti n.5 - 500g box (SKU PAS-SPA-500)?"
)

INTEGRATION_CASES = [
    (
        Q1_QUESTION,
        "crm",
        ["4", "740", "000"],
        lambda sources: any(s.startswith("crm/") for s in sources),
    ),
    (
        Q2_QUESTION,
        "erp",
        ["462", "below", "minimum"],
        lambda sources: any(s.startswith("erp/") for s in sources),
    ),
    (
        Q3_QUESTION,
        "calls",
        ["broken", "LOT-2026-0658"],
        lambda sources: any(s.startswith("calls") for s in sources),
    ),
    (
        Q4_QUESTION,
        "kb",
        ["36", "month", "gluten"],
        lambda sources: any(s.startswith("DOC-") for s in sources),
    ),
]

OPPORTUNITY_ROWS = [
    {
        "opportunity_id": "OPP-001",
        "customer_id": "CUST-0132",
        "stage": "qualification",
        "value_eur": 200000,
    },
    {
        "opportunity_id": "OPP-002",
        "customer_id": "CUST-0132",
        "stage": "negotiation",
        "value_eur": 180000,
    },
    {
        "opportunity_id": "OPP-003",
        "customer_id": "CUST-0132",
        "stage": "negotiation",
        "value_eur": 160000,
    },
    {
        "opportunity_id": "OPP-004",
        "customer_id": "CUST-0132",
        "stage": "qualification",
        "value_eur": 200000,
    },
    {
        "opportunity_id": "OPP-005",
        "customer_id": "CUST-0132",
        "stage": "won",
        "value_eur": 500000,
    },
]


def _has_integration_env() -> bool:
    return bool(os.environ.get("MOCK_API_TOKEN") and os.environ.get("LLM_API_KEY"))


@patch("agent.tools.crm.get_client")
def test_list_opportunities_cust_0132_open_stats(mock_get_client: MagicMock) -> None:
    """Q1 unit: CUST-0132 returns count=4 open opportunities, total_value_eur=740000."""
    from agent.tools.crm import run_crm_tool

    mock_client = MagicMock()
    mock_client.get.return_value = {
        "data": OPPORTUNITY_ROWS,
        "pagination": {"total": 5, "offset": 0, "limit": 50},
    }
    mock_get_client.return_value = mock_client

    result_json, source = run_crm_tool("list_opportunities", {"customer_id": "CUST-0132"})
    result = json.loads(result_json)

    assert source == "crm/opportunities"
    assert result["count"] == 4
    assert result["total_value_eur"] == 740000
    mock_client.get.assert_called_once_with(
        "/crm/opportunities",
        params={"customer_id": "CUST-0132"},
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "question,expected_verticale,expected_substrings,source_check",
    INTEGRATION_CASES,
    ids=["q1_crm", "q2_erp", "q3_calls", "q4_kb"],
)
@pytest.mark.skipif(not _has_integration_env(), reason="MOCK_API_TOKEN and LLM_API_KEY required")
def test_phase2_integration(
    question: str,
    expected_verticale: str,
    expected_substrings: list[str],
    source_check,
) -> None:
    """Each Q1-Q4 question returns correct facts, verticale, and non-empty sources."""
    from agent.loop import run_agent

    response = run_agent(question)
    answer_lower = response["answer"].lower()

    for substring in expected_substrings:
        assert substring.lower() in answer_lower, (
            f"Expected '{substring}' in answer: {response['answer'][:200]}"
        )

    assert response["verticale"] == expected_verticale
    assert response["sources"]
    assert source_check(response["sources"])

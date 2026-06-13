"""Integration battery for all 12 public sample questions (SAMPLE_QUESTIONS.md)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import pytest

from tests.conftest import has_integration_env, is_rate_limit_response

# --- Questions (verbatim from SAMPLE_QUESTIONS.md) ---

Q1 = (
    "How many open opportunities does Primato Supermercati S.p.A. (CUST-0132) have, "
    "and what is their total value?"
)
Q2 = (
    "Is SKU PAS-PEN-500 (Penne Rigate n.73 - 500g box) below its minimum stock? "
    "Give the on-hand quantity."
)
Q3 = (
    "In the last call with NordSpesa S.p.A. (CUST-0137), what was the complaint "
    "and which lot did it concern?"
)
Q4 = (
    "What is the shelf life (TMC) and the declared allergens for "
    "Spaghetti n.5 - 500g box (SKU PAS-SPA-500)?"
)
Q5 = (
    "Does the complaint from that last NordSpesa S.p.A. call qualify for a return "
    "under the quality policy?"
)
Q6 = (
    "Total value of opportunities in the negotiation stage, grouped by customer "
    "channel (GDO / distributor / horeca)."
)
Q7 = "What is the profit margin on lot LOT-2026-0658?"
Q8 = "What is the status of the order for Supermercati Bianchi?"
Q9 = (
    "Generate a 4-slide HTML deck for the sales rep visiting Primato Supermercati "
    "S.p.A. (CUST-0132): profile, open deals, order/lot status, recent call complaints."
)
Q10 = (
    "Which semolina does SKU PAS-SPA-500 use (per its bill of materials), which "
    "supplier provides it, and is that raw material below minimum stock?"
)
Q11 = (
    "Across ALL recorded calls (there are 80 - you must page through the entire call "
    "log, do not stop at the first page), count how many quality complaints concern "
    "the defect 'broken pasta'. Give the exact number."
)
Q12 = (
    "GranMercato S.p.A. (also written 'Gran Mercato S.p.A.' in some notes) asked "
    "about the price of Fusilli n.98 (PAS-FUS-500). A call mentions one figure and "
    "the official 2026 wholesale price list mentions another. Which is the correct "
    "list price, and why? (When a phone call and an official document disagree, the "
    "official document is authoritative.)"
)

AGENT_MAX_ATTEMPTS = int(os.environ.get("INTEGRATION_AGENT_RETRIES", "3"))
AGENT_RETRY_BASE_SECONDS = float(os.environ.get("INTEGRATION_AGENT_RETRY_SECONDS", "5"))


def _any_in(text: str, *needles: str) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _all_in(text: str, *needles: str) -> bool:
    lower = text.lower()
    return all(needle.lower() in lower for needle in needles)


def run_agent_resilient(question: str) -> dict[str, Any]:
    """Call run_agent with backoff when the LLM returns a rate-limit fallback."""
    from agent.loop import run_agent

    last: dict[str, Any] | None = None
    for attempt in range(AGENT_MAX_ATTEMPTS):
        last = run_agent(question)
        if not is_rate_limit_response(last["answer"]):
            return last
        if attempt < AGENT_MAX_ATTEMPTS - 1:
            time.sleep(AGENT_RETRY_BASE_SECONDS * (2**attempt))
    assert last is not None
    return last


def _assert_sources(response: dict[str, Any], predicate: Callable[[list[str]], bool]) -> None:
    assert response["sources"], f"Expected non-empty sources, got: {response}"
    assert predicate(response["sources"]), f"Unexpected sources: {response['sources']}"


def _assert_not_rate_limited(response: dict[str, Any]) -> None:
    if is_rate_limit_response(response["answer"]):
        pytest.fail(
            "LLM rate limit persisted after retries. "
            "Increase INTEGRATION_TEST_DELAY_SECONDS or wait before re-running. "
            f"Answer: {response['answer'][:300]}"
        )


def _assert_q1(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    assert _all_in(response["answer"], "4", "740"), response["answer"][:300]
    _assert_sources(response, lambda s: any(x.startswith("crm/") for x in s))


def _assert_q2(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    assert _all_in(response["answer"], "462", "below", "minimum"), response["answer"][:300]
    _assert_sources(response, lambda s: any(x.startswith("erp/") for x in s))


def _assert_q3(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    assert _all_in(response["answer"], "broken", "LOT-2026-0658"), response["answer"][:300]
    _assert_sources(response, lambda s: any(x.startswith("calls") for x in s))


def _assert_q4(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    assert _all_in(response["answer"], "36", "month", "gluten"), response["answer"][:300]
    _assert_sources(response, lambda s: any(x.startswith("DOC-") for x in s))


def _assert_q5(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    assert _any_in(
        response["answer"], "yes", "qualif", "qualify", "replacement", "credit"
    ), response["answer"][:300]
    _assert_sources(response, lambda s: any(x.startswith("DOC-") for x in s))


def _assert_q6(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _any_in(answer, "3,301", "3301", "3.301"), answer[:300]
    assert _any_in(answer, "1,931", "1931", "1.931"), answer[:300]
    assert _any_in(answer, "3,040", "3040", "3.040"), answer[:300]
    _assert_sources(response, lambda s: any(x.startswith("crm/") for x in s))


def _assert_q7(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _any_in(
        answer,
        "not available",
        "not stored",
        "cannot",
        "no profit",
        "do not",
        "does not",
    ), answer[:300]
    assert "margin" in answer.lower() or "profit" in answer.lower(), answer[:300]
    # Trap: must not invent a numeric/percentage profit margin.
    assert "%" not in answer, answer[:300]


def _assert_q8(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _any_in(
        answer,
        "does not exist",
        "do not exist",
        "not found",
        "no customer",
        "not in the crm",
        "cannot find",
    ), answer[:300]
    assert _any_in(answer, "bianchi", "supermercati bianchi"), answer[:300]
    # Premise was verified against the CRM customer list before abstaining.
    _assert_sources(response, lambda s: any(x.startswith("crm") for x in s))


def _assert_q9(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _any_in(answer, "<html", "<!doctype", "<div", "<section", "slide"), answer[:300]
    assert _any_in(answer, "740", "primato"), answer[:300]


def _assert_q10(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _all_in(answer, "RAW-SEM-003"), answer[:300]
    assert _any_in(answer, "molino", "san giorgio"), answer[:300]
    _assert_sources(response, lambda s: any(x.startswith("erp/") for x in s))


def _assert_q11(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _any_in(answer, " 9", " nine", "9 call", "9 quality", "exactly 9", "count is 9"), (
        answer[:300]
    )
    _assert_sources(response, lambda s: any(x.startswith("calls") for x in s))


def _assert_q12(response: dict[str, Any]) -> None:
    _assert_not_rate_limited(response)
    answer = response["answer"]
    assert _any_in(answer, "8.07", "8,07"), answer[:300]
    assert _any_in(answer, "doc-015", "official", "price list", "authoritative"), answer[:300]
    _assert_sources(response, lambda s: any(x.startswith("DOC-") for x in s))


SAMPLE_CASES: list[tuple[str, str, str, Callable[[dict[str, Any]], None]]] = [
    (Q1, "q01_crm_open_opportunities", "crm", _assert_q1),
    (Q2, "q02_erp_below_minimum", "erp", _assert_q2),
    (Q3, "q03_calls_complaint_lot", "calls", _assert_q3),
    (Q4, "q04_kb_shelf_life_allergens", "kb", _assert_q4),
    (Q5, "q05_calls_kb_return_policy", "calls", _assert_q5),
    (Q6, "q06_crm_negotiation_by_channel", "crm", _assert_q6),
    (Q7, "q07_erp_trap_profit_margin", "erp", _assert_q7),
    (Q8, "q08_crm_trap_missing_customer", "crm", _assert_q8),
    (Q9, "q09_crm_html_deck", "crm", _assert_q9),
    (Q10, "q10_erp_bom_supplier_stock", "erp", _assert_q10),
    (Q11, "q11_calls_broken_pasta_count", "calls", _assert_q11),
    (Q12, "q12_kb_price_authority", "kb", _assert_q12),
]


# Trap / multi-source questions: dominant verticale is ambiguous; content matters most.
FLEXIBLE_VERTICALE_CASES = {"q07_erp_trap_profit_margin"}


@pytest.mark.integration
@pytest.mark.parametrize(
    "question,case_id,expected_verticale,assert_fn",
    SAMPLE_CASES,
    ids=[case[1] for case in SAMPLE_CASES],
)
@pytest.mark.skipif(not has_integration_env(), reason="MOCK_API_TOKEN and LLM_API_KEY required")
@pytest.mark.timeout(90)
def test_sample_question(
    question: str,
    case_id: str,
    expected_verticale: str,
    assert_fn: Callable[[dict[str, Any]], None],
) -> None:
    """Each sample question returns expected facts, verticale, and sources."""
    response = run_agent_resilient(question)
    assert_fn(response)
    if case_id not in FLEXIBLE_VERTICALE_CASES:
        assert response["verticale"] == expected_verticale, (
            f"{case_id}: expected verticale={expected_verticale!r}, "
            f"got {response['verticale']!r}; answer={response['answer'][:200]}"
        )

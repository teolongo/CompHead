"""Deterministic correctness preflight for trap and premise questions.

Some evaluation questions are traps by design: they ask for a metric that does
not exist in any source (profit margin / cost on a lot), or about an entity that
does not exist (an order for a customer not in the CRM). For those, a precise,
honest "not available" scores full marks while inventing a figure scores
heavily negative.

This module intercepts those narrow, high-confidence cases *before* the LLM
tool-calling loop and returns a deterministic, frozen-schema answer. Triggers are
intentionally narrow (exact unsupported-metric keywords, an explicit lot id, or
an explicit "order ... for <Name>" premise); anything ambiguous returns ``None``
so the normal agent loop handles it.
"""

from __future__ import annotations

from typing import Any

import re

from services.api_client import get_client

# Production lot identifier, e.g. LOT-2026-0658.
_LOT_RE = re.compile(r"\bLOT-\d{4}-\d{4}\b", re.IGNORECASE)

# Financial metrics that are not stored on lots/orders/inventory anywhere.
_UNSUPPORTED_METRIC_RE = re.compile(
    r"\b(profit\s*margin|profit|margins?|markups?|profitability|"
    r"cost of goods|cogs|production\s*cost|cost)\b",
    re.IGNORECASE,
)

# "... order(s) ... for|of|from|placed by <Name>" premise extraction.
_ORDER_CUSTOMER_RE = re.compile(
    r"\border(?:s)?\b[^.?!]*?\b(?:for|of|from|placed\s+by|by)\s+(?P<name>[^.?!]+)",
    re.IGNORECASE,
)

# Clause boundaries that should terminate a candidate customer name.
_NAME_BOUNDARY_RE = re.compile(
    r"\s+(?:and|with|in|on|regarding|about|that|which|who|whose)\s+|[,;]",
    re.IGNORECASE,
)


def _schema(answer: str, sources: list[str], verticale: str) -> dict[str, Any]:
    return {
        "answer": answer,
        "sources": sources,
        "verticale": verticale,
        "artifact_url": None,
    }


def _unsupported_lot_metric_preflight(question: str) -> dict[str, Any] | None:
    lot_match = _LOT_RE.search(question)
    if not lot_match:
        return None
    if not _UNSUPPORTED_METRIC_RE.search(question):
        return None

    lot_id = lot_match.group(0).upper()
    answer = (
        f"The profit margin and cost for lot {lot_id} are not available: cost, "
        "profit, and margin figures are not stored on production lots or anywhere "
        "in the Al Dente data sources. Lots carry production, quality, and quantity "
        "data, but no financial profitability fields."
    )
    return _schema(answer, [], "erp")


def _extract_customer_name(question: str) -> str | None:
    match = _ORDER_CUSTOMER_RE.search(question)
    if not match:
        return None

    raw = match.group("name").strip()
    raw = _NAME_BOUNDARY_RE.split(raw, maxsplit=1)[0].strip()
    raw = raw.strip(" \t\"'.?!")
    raw = re.sub(r"^(?:the|a|an)\s+", "", raw, flags=re.IGNORECASE).strip()

    if not raw:
        return None
    # A bare customer id is a precise reference; let the LLM resolve it.
    if "cust-" in raw.lower():
        return None
    # Require a name-like token (at least one capitalized word) and bounded length.
    if not re.search(r"[A-Z]", raw):
        return None
    if len(raw) > 60:
        return None
    return raw


def _missing_customer_preflight(question: str) -> dict[str, Any] | None:
    name = _extract_customer_name(question)
    if not name:
        return None

    try:
        rows = get_client().get_all_pages("/crm/customers", params={"search": name})
    except Exception:
        # Could not verify the premise (no token / transient error): let the LLM try.
        return None

    if rows:
        # Customer exists; the order question is a real lookup for the LLM loop.
        return None

    answer = (
        f'There is no customer named "{name}" in the CRM, so there is no order '
        "status to report for it. The customer does not exist in the available sources."
    )
    return _schema(answer, ["crm/customers"], "crm")


_PREFLIGHTS = (
    _unsupported_lot_metric_preflight,
    _missing_customer_preflight,
)


def try_answer_correctness_preflight(question: str) -> dict[str, Any] | None:
    """Return a deterministic trap/premise answer, or ``None`` to defer to the LLM."""
    if not question or not question.strip():
        return None
    for check in _PREFLIGHTS:
        result = check(question)
        if result is not None:
            return result
    return None

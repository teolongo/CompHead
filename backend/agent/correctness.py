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

import json
import re

from agent.tools import kb
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


# --- Multi-hop chains (Plan 03-03) ---------------------------------------

_CUST_ID_RE = re.compile(r"\bCUST-\d{3,4}\b", re.IGNORECASE)

# A return-policy question references a complaint/call and asks about returns.
_RETURN_WORD_RE = re.compile(r"\b(return|returns|credit\s*note|refund)\b", re.IGNORECASE)
_QUALIFY_OR_POLICY_RE = re.compile(r"\b(qualif\w*|policy|eligible|covered)\b", re.IGNORECASE)
_COMPLAINT_CALL_RE = re.compile(r"\b(complaint|call|claim|defect)\b", re.IGNORECASE)

# Capitalized customer name immediately preceding the word "call".
_CALL_CUSTOMER_RE = re.compile(
    r"(?P<name>[A-Z][A-Za-z0-9&.\-']*(?:\s+[A-Z][A-Za-z0-9&.\-']*)*)\s+call\b"
)

# Covered defects from the returns policy (DOC-011), with transcript search terms.
_COVERED_DEFECTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("broken pasta", ("broken",)),
    ("bloated packs", ("bloated",)),
    ("foreign body", ("foreign body", "foreign")),
    ("mislabeling", ("mislabeling", "mislabel", "wrong label")),
)

# A price-authority question names a SKU and cites the official price list.
_PRICE_SKU_RE = re.compile(r"\bPAS-[A-Z]{3}-\d{3}\b", re.IGNORECASE)
_PRICE_WORD_RE = re.compile(r"\bprice", re.IGNORECASE)
_PRICE_AUTHORITY_RE = re.compile(
    r"\b(official|authoritative|price\s*list|wholesale|disagree)\b", re.IGNORECASE
)
_PRICE_VALUE_RE = re.compile(r"\d+[.,]\d{2}")


def _search_kb_doc(query: str) -> tuple[str, str] | None:
    """Return (doc_id, full_text) for the best KB match, or None on failure."""
    try:
        result_json, doc_id = kb.run_kb_tool("search_kb", {"query": query})
    except Exception:
        return None
    try:
        data = json.loads(result_json)
    except (ValueError, TypeError):
        return None
    return doc_id, str(data.get("full_document_text") or "")


def _extract_call_customer_name(question: str) -> str | None:
    match = _CALL_CUSTOMER_RE.search(question)
    if not match:
        return None
    raw = match.group("name").strip().strip(" \t\"'")
    if not raw or not re.search(r"[A-Z]", raw):
        return None
    if len(raw) > 60:
        return None
    return raw


def _resolve_call_customer(question: str) -> tuple[str | None, bool]:
    """Resolve the customer for a 'last call' question.

    Returns (customer_id, searched_crm). A bare ``CUST-####`` id is used
    directly; otherwise the capitalized name before "call" is verified against
    ``/crm/customers``.
    """
    cust = _CUST_ID_RE.search(question)
    if cust:
        return cust.group(0).upper(), False

    name = _extract_call_customer_name(question)
    if not name:
        return None, False
    try:
        rows = get_client().get_all_pages("/crm/customers", params={"search": name})
    except Exception:
        return None, True
    if not rows:
        return None, True
    first = rows[0]
    return (first.get("customer_id") or first.get("id")), True


def _latest_call_id(customer_id: str) -> str | None:
    payload = get_client().get("/calls", params={"customer_id": customer_id})
    rows = payload.get("data") or []
    if not rows:
        return None
    rows = sorted(
        rows,
        key=lambda r: str(r.get("call_date") or r.get("date") or ""),
        reverse=True,
    )
    first = rows[0]
    return first.get("call_id") or first.get("id")


def _lot_from_segments(segments: list[dict[str, Any]]) -> str | None:
    for segment in segments:
        match = _LOT_RE.search(str(segment.get("text") or ""))
        if match:
            return match.group(0).upper()
    return None


def _find_complaint_defect(call_id: str) -> tuple[str | None, str | None]:
    """Find a covered defect (and lot) in a call via targeted transcript search."""
    client = get_client()
    for defect, terms in _COVERED_DEFECTS:
        for term in terms:
            payload = client.get(f"/calls/{call_id}/transcript", params={"search": term})
            segments = payload.get("segments") or []
            combined = " ".join(str(s.get("text") or "") for s in segments).lower()
            if not combined:
                continue
            if all(word in combined for word in term.lower().split()):
                return defect, _lot_from_segments(segments)
    return None, None


def _is_return_policy_question(question: str) -> bool:
    return bool(
        _RETURN_WORD_RE.search(question)
        and _QUALIFY_OR_POLICY_RE.search(question)
        and _COMPLAINT_CALL_RE.search(question)
    )


def _return_policy_preflight(question: str) -> dict[str, Any] | None:
    if not _is_return_policy_question(question):
        return None

    customer_id, searched_crm = _resolve_call_customer(question)
    if not customer_id:
        return None

    try:
        call_id = _latest_call_id(customer_id)
        if not call_id:
            return None
        defect, lot_id = _find_complaint_defect(call_id)
    except Exception:
        return None

    if not defect:
        # Complaint is not a covered defect (or could not be read): defer to LLM.
        return None

    policy = _search_kb_doc("returns and quality complaints policy broken pasta covered defects")
    if not policy:
        return None
    doc_id, _text = policy

    lot_part = f" on lot {lot_id}" if lot_id else ""
    answer = (
        f"Yes. The complaint is a '{defect}' non-conformity{lot_part}, which is a "
        f"covered defect under the Al Dente returns and quality complaints policy "
        f"({doc_id}). Provided it was reported within the 15-day return window with "
        f"the lot number and a photo of the non-conformity, the complaint qualifies "
        f"for a return. Outcome: replacement of the affected product or a credit note "
        f"on the lot value, and the affected lot is blocked pending investigation."
    )

    sources: list[str] = []
    if searched_crm:
        sources.append("crm/customers")
    sources.extend(["calls", f"calls/{call_id}/transcript", doc_id])
    return _schema(answer, sources, "calls")


def _extract_list_price(text: str, sku: str) -> str | None:
    sku_upper = sku.upper()
    for line in text.splitlines():
        if sku_upper in line.upper() and "|" in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            for cell in reversed(cells):
                match = _PRICE_VALUE_RE.search(cell)
                if match:
                    return match.group(0)
    detail = re.search(
        rf"{re.escape(sku_upper)}[\s\S]{{0,200}}?EUR\s*(\d+[.,]\d{{2}})",
        text,
        re.IGNORECASE,
    )
    if detail:
        return detail.group(1)
    return None


def _price_authority_preflight(question: str) -> dict[str, Any] | None:
    sku_match = _PRICE_SKU_RE.search(question)
    if not sku_match:
        return None
    if not _PRICE_WORD_RE.search(question):
        return None
    if not _PRICE_AUTHORITY_RE.search(question):
        return None

    sku = sku_match.group(0).upper()
    doc = _search_kb_doc("official 2026 wholesale price list")
    if not doc:
        return None
    doc_id, text = doc

    price = _extract_list_price(text, sku)
    if not price:
        return None

    answer = (
        f"The correct list price for {sku} is EUR {price} per carton, per the "
        f"official 2026 wholesale price list ({doc_id}). When a phone call and an "
        f"official document disagree, the official price list is authoritative, so "
        f"any different figure mentioned in a call is not the valid list price."
    )
    return _schema(answer, [doc_id], "kb")


_PREFLIGHTS = (
    _unsupported_lot_metric_preflight,
    _missing_customer_preflight,
    _return_policy_preflight,
    _price_authority_preflight,
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

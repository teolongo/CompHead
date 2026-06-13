"""Phase 3 multi-hop chain unit tests (offline, no live LLM/API).

These tests pin the deterministic multi-source chains added in Plan 03-03:

- Q5-style: a return-policy question must combine the last complaint call
  (calls + transcript) with the KB quality/returns policy (DOC-011) and state
  whether the complaint qualifies — using policy facts, not LLM inference.
- DATA-05 / Q10-style: a BOM/supplier/stock question that references a
  ``LOT-...`` id must resolve the lot to its finished SKU *first*, then traverse
  BOM -> raw material -> supplier -> raw-material inventory. The chain must not
  short-circuit by being handed the finished SKU directly.
- Q12-style: a price-authority question must extract the official list price
  from the KB price list (DOC-015) and state the official document wins over a
  conflicting call mention.

The CRM/calls API client is mocked so the tests run fast and offline; the KB
chains read the real local documents in ``backend/data/kb/``.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

SCHEMA_KEYS = {"answer", "sources", "verticale", "artifact_url"}
VALID_VERTICALI = {"crm", "erp", "calls", "kb"}


def _assert_schema(result: dict) -> None:
    assert result is not None, "Expected a deterministic answer, got None"
    assert set(result.keys()) >= SCHEMA_KEYS, result
    assert result["artifact_url"] is None
    assert isinstance(result["sources"], list)
    assert result["verticale"] in VALID_VERTICALI


# --- ERP lot -> SKU -> BOM -> supplier -> stock chain (DATA-05 / Q10) -------

LOT_BOM_QUESTION = (
    "For production lot LOT-2026-0876, which semolina does the finished product "
    "use per its bill of materials, which supplier provides it, and is that raw "
    "material below minimum stock?"
)


def _make_erp_chain_client() -> MagicMock:
    """Mock ERP client: lot LOT-2026-0876 -> PAS-SPA-500 -> RAW-SEM-003 chain."""
    client = MagicMock()

    def _get_all_pages(path: str, params: dict | None = None, **_: object) -> list[dict]:
        if path == "/erp/production-orders":
            return [
                {"id": "LOT-2026-0001", "sku": "PAS-PEN-500"},
                {"id": "LOT-2026-0876", "sku": "PAS-SPA-500"},
            ]
        return []

    def _get(path: str, params: dict | None = None, **_: object) -> dict:
        params = params or {}
        if path == "/erp/bom":
            assert params.get("sku") == "PAS-SPA-500", params
            return {
                "data": [
                    {
                        "sku": "PAS-SPA-500",
                        "product_name": "Spaghetti n.5 - 500g box",
                        "components": [
                            {
                                "raw_sku": "RAW-SEM-003",
                                "description": "Durum semolina - premium",
                                "qty_per_carton": 10.5,
                                "unit": "kg",
                            },
                            {
                                "raw_sku": "RAW-PCK-001",
                                "description": "Carton box",
                                "qty_per_carton": 1,
                                "unit": "pcs",
                            },
                        ],
                    }
                ]
            }
        if path == "/erp/suppliers":
            return {
                "data": [
                    {
                        "id": "SUP-014",
                        "name": "Molino San Giorgio",
                        "category": "semolina",
                    }
                ]
            }
        if path == "/erp/inventory":
            assert params.get("search") == "RAW-SEM-003", params
            assert params.get("type") == "raw_material", params
            return {
                "data": [
                    {
                        "sku": "RAW-SEM-003",
                        "description": "Durum semolina - premium",
                        "type": "raw_material",
                        "on_hand": 50000,
                        "min_stock": 20000,
                        "below_min": False,
                    }
                ]
            }
        return {"data": []}

    client.get_all_pages.side_effect = _get_all_pages
    client.get.side_effect = _get
    return client


def test_resolve_bom_supplier_stock_from_lot_resolves_finished_sku_first() -> None:
    from agent.tools.erp import run_erp_tool

    client = _make_erp_chain_client()
    with patch("agent.tools.erp.get_client", return_value=client):
        result_json, source = run_erp_tool(
            "resolve_bom_supplier_stock",
            {"lot_id": "LOT-2026-0876", "material_category": "semolina"},
        )
    result = json.loads(result_json)

    assert source.startswith("erp/"), source
    # Lot was resolved to a finished SKU before BOM traversal (not handed in).
    assert result["lot_id"] == "LOT-2026-0876", result
    assert result["finished_sku"] == "PAS-SPA-500", result
    assert result["raw_material_sku"] == "RAW-SEM-003", result
    assert "semolina" in str(result["raw_material_name"]).lower(), result
    assert "molino san giorgio" in str(result["supplier_name"]).lower(), result
    # Comparison field consumed from inventory, not recomputed by an LLM.
    assert result["below_minimum"] is False, result
    assert result["on_hand_qty"] == 50000, result
    assert result["minimum_qty"] == 20000, result

    # Proof the lot was resolved via a production-order lookup.
    client.get_all_pages.assert_any_call("/erp/production-orders", params=None)


def test_resolve_bom_supplier_stock_from_sku_skips_lot_resolution() -> None:
    from agent.tools.erp import run_erp_tool

    client = _make_erp_chain_client()
    with patch("agent.tools.erp.get_client", return_value=client):
        result_json, _ = run_erp_tool(
            "resolve_bom_supplier_stock",
            {"sku": "PAS-SPA-500", "material_category": "semolina"},
        )
    result = json.loads(result_json)

    assert result["finished_sku"] == "PAS-SPA-500", result
    assert result["raw_material_sku"] == "RAW-SEM-003", result
    assert result["below_minimum"] is False, result
    # No lot given: must not page production orders to resolve a lot.
    client.get_all_pages.assert_not_called()


def test_resolve_bom_supplier_stock_requires_sku_or_lot() -> None:
    from agent.tools.erp import run_erp_tool

    client = _make_erp_chain_client()
    with patch("agent.tools.erp.get_client", return_value=client):
        result_json, _ = run_erp_tool("resolve_bom_supplier_stock", {})
    result = json.loads(result_json)
    # Missing premise -> honest not-found, never invented facts.
    assert result["finished_sku"] is None, result
    assert "note" in result, result


# --- Return-policy chain (Q5): last call complaint + KB policy --------------

RETURN_POLICY_QUESTION = (
    "Does the complaint from that last NordSpesa S.p.A. call qualify for a "
    "return under the quality policy?"
)


def _make_calls_client() -> MagicMock:
    client = MagicMock()

    def _get_all_pages(path: str, params: dict | None = None, **_: object) -> list[dict]:
        if path == "/crm/customers":
            return [{"customer_id": "CUST-0137", "name": "NordSpesa S.p.A."}]
        return []

    def _get(path: str, params: dict | None = None, **_: object) -> dict:
        params = params or {}
        if path == "/calls":
            return {
                "data": [
                    {"call_id": "CALL-50000", "call_date": "2026-04-01", "customer_id": "CUST-0137"},
                    {"call_id": "CALL-58020", "call_date": "2026-05-10", "customer_id": "CUST-0137"},
                ]
            }
        if path == "/calls/CALL-58020/transcript":
            search = str(params.get("search") or "").lower()
            if "broken" in search:
                return {
                    "segments": [
                        {
                            "speaker": "customer",
                            "text": "We received broken pasta in lot LOT-2026-0658, "
                            "lots of broken pieces.",
                        }
                    ]
                }
            return {"segments": []}
        return {"data": []}

    client.get_all_pages.side_effect = _get_all_pages
    client.get.side_effect = _get
    return client


def test_return_policy_chain_combines_call_and_kb_policy() -> None:
    from agent.correctness import try_answer_correctness_preflight

    client = _make_calls_client()
    with patch("agent.correctness.get_client", return_value=client):
        result = try_answer_correctness_preflight(RETURN_POLICY_QUESTION)

    _assert_schema(result)
    lower = result["answer"].lower()
    assert "broken" in lower, result["answer"]
    assert "lot-2026-0658" in lower, result["answer"]
    assert "replacement" in lower or "credit" in lower, result["answer"]
    # Multi-source: complaint defect (calls) + the KB returns policy document.
    assert any(s.startswith("DOC-") for s in result["sources"]), result["sources"]
    assert result["verticale"] == "calls", result


# --- Price authority chain (Q12): official price list wins over a call ------

PRICE_AUTHORITY_QUESTION = (
    "GranMercato S.p.A. asked about the price of Fusilli n.98 (PAS-FUS-500). A "
    "call mentions one figure and the official 2026 wholesale price list mentions "
    "another. Which is the correct list price, and why?"
)


def test_price_authority_chain_uses_official_price_list() -> None:
    from agent.correctness import try_answer_correctness_preflight

    result = try_answer_correctness_preflight(PRICE_AUTHORITY_QUESTION)

    _assert_schema(result)
    answer = result["answer"]
    lower = answer.lower()
    assert "8.07" in answer or "8,07" in answer, answer
    assert "doc-015" in lower, answer
    assert "official" in lower or "authoritative" in lower, answer
    assert any(s == "DOC-015" for s in result["sources"]), result["sources"]
    assert result["verticale"] == "kb", result


def test_plain_non_chain_question_returns_none() -> None:
    from agent.correctness import try_answer_correctness_preflight

    # No conflict/authority cue and no return-policy cue -> defer to the LLM.
    assert try_answer_correctness_preflight("What is the capital of Italy?") is None

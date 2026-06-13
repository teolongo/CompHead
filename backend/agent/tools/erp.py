"""ERP tools for the agent loop."""

from __future__ import annotations

import json
from typing import Any

from services.api_client import get_client

SAMPLE_CAP = 100

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": (
                "Look up ERP inventory with optional filters. Returns pre-computed "
                "below_minimum, on_hand_qty, and minimum_qty for the matched SKU — "
                "use those exact fields; do not compare raw rows yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "SKU substring filter, e.g. PAS-PEN-500",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["finished_good", "raw_material"],
                        "description": "Filter by inventory item type",
                    },
                    "below_min": {
                        "type": "boolean",
                        "description": "When true, only items below minimum stock",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_bom",
            "description": "List bill of materials for a finished SKU. Returns count and sample rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Finished product SKU, e.g. PAS-SPA-500",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_suppliers",
            "description": "List ERP suppliers with optional filters. Returns count and sample rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Search supplier name or id",
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "semolina",
                            "wheat",
                            "packaging",
                            "labels",
                            "ink",
                            "logistics",
                        ],
                        "description": "Supplier category filter",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_production_orders",
            "description": (
                "List ERP production orders with optional filters. Returns count and sample rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Filter by product SKU",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["planned", "in_progress", "done", "blocked"],
                        "description": "Production order status filter",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_shipments",
            "description": "List ERP shipments with optional filters. Returns count and sample rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0132",
                    },
                    "order_id": {
                        "type": "string",
                        "description": "Filter by order id, e.g. ORD-2026-0517",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def _row_int(row: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key in row and row[key] is not None:
            return int(row[key])
    return 0


def _compute_inventory_status(row: dict[str, Any]) -> tuple[bool, int, int]:
    on_hand = _row_int(row, "on_hand_qty", "on_hand", "quantity_on_hand")
    minimum = _row_int(row, "minimum_qty", "minimum_stock", "min_qty", "minimum")
    below_minimum = on_hand < minimum if minimum > 0 else False
    return below_minimum, on_hand, minimum


def _find_matching_row(rows: list[dict[str, Any]], search: str | None) -> dict[str, Any] | None:
    if not rows:
        return None
    if not search:
        return rows[0]
    search_upper = search.upper()
    for row in rows:
        sku = str(row.get("sku") or "").upper()
        if sku == search_upper or search_upper in sku:
            return row
    return rows[0]


def _thin_list_result(
    rows: list[dict[str, Any]], sample_key: str
) -> dict[str, Any]:
    return {
        "count": len(rows),
        sample_key: rows[:SAMPLE_CAP],
    }


def _run_get_inventory(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if search := arguments.get("search"):
        params["search"] = search
    if item_type := arguments.get("type"):
        params["type"] = item_type
    if arguments.get("below_min") is True:
        params["below_min"] = "true"

    payload = get_client().get("/erp/inventory", params=params or None)
    rows = payload.get("data") or []
    matched = _find_matching_row(rows, arguments.get("search"))

    if not matched:
        result = {
            "sku": arguments.get("search"),
            "below_minimum": None,
            "on_hand_qty": None,
            "minimum_qty": None,
            "inventory_sample": [],
            "note": "No inventory row matched the filters.",
        }
        return json.dumps(result), "erp/inventory"

    below_minimum, on_hand, minimum = _compute_inventory_status(matched)
    result = {
        "sku": matched.get("sku"),
        "below_minimum": below_minimum,
        "on_hand_qty": on_hand,
        "minimum_qty": minimum,
        "inventory_sample": rows[:SAMPLE_CAP],
    }
    return json.dumps(result), "erp/inventory"


def _run_list_bom(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if sku := arguments.get("sku"):
        params["sku"] = sku
    payload = get_client().get("/erp/bom", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "bom_sample")
    return json.dumps(result), "erp/bom"


def _run_list_suppliers(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if search := arguments.get("search"):
        params["search"] = search
    if category := arguments.get("category"):
        params["category"] = category
    payload = get_client().get("/erp/suppliers", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "suppliers_sample")
    return json.dumps(result), "erp/suppliers"


def _run_list_production_orders(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if sku := arguments.get("sku"):
        params["sku"] = sku
    if status := arguments.get("status"):
        params["status"] = status
    payload = get_client().get("/erp/production-orders", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "production_orders_sample")
    return json.dumps(result), "erp/production-orders"


def _run_list_shipments(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    if order_id := arguments.get("order_id"):
        params["order_id"] = order_id
    payload = get_client().get("/erp/shipments", params=params or None)
    rows = payload.get("data") or []
    result = _thin_list_result(rows, "shipments_sample")
    return json.dumps(result), "erp/shipments"


def run_erp_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    dispatch = {
        "get_inventory": _run_get_inventory,
        "list_bom": _run_list_bom,
        "list_suppliers": _run_list_suppliers,
        "list_production_orders": _run_list_production_orders,
        "list_shipments": _run_list_shipments,
    }
    handler = dispatch.get(name)
    if handler is None:
        raise ValueError(f"Unknown ERP tool: {name}")
    return handler(arguments)

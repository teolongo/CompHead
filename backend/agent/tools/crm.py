"""CRM tools for the agent loop."""

from __future__ import annotations

import json
from typing import Any

from services.api_client import get_client

OPEN_STAGES = {"qualification", "negotiation"}
SAMPLE_CAP = 100

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_opportunities",
            "description": (
                "List CRM opportunities with optional filters. Returns count, total EUR "
                "value, and a sample of rows. Open stages are qualification and negotiation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0132",
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["qualification", "negotiation", "won", "lost"],
                        "description": "Filter by pipeline stage",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_customers",
            "description": (
                "List CRM customers with optional filters. Returns count and sample rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Search customer name or id",
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["GDO", "distributor", "horeca"],
                        "description": "Customer channel filter",
                    },
                    "region": {
                        "type": "string",
                        "description": "Region filter",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": (
                "List CRM orders with optional filters. Returns count, total value EUR, "
                "and sample rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0132",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "open",
                            "in_production",
                            "shipped",
                            "delivered",
                            "cancelled",
                        ],
                        "description": "Order status filter",
                    },
                    "from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD)",
                    },
                    "to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD)",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_invoices",
            "description": (
                "List CRM invoices with optional filters. Returns count, total amount EUR, "
                "and sample rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0132",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["unpaid", "paid", "overdue"],
                        "description": "Invoice status filter",
                    },
                    "from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD)",
                    },
                    "to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD)",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def _compute_open_stats(rows: list[dict[str, Any]]) -> tuple[int, float]:
    open_rows = [row for row in rows if row.get("stage") in OPEN_STAGES]
    total = sum(float(row.get("value_eur") or row.get("value") or 0) for row in open_rows)
    return len(open_rows), total


def _row_amount(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in row and row[key] is not None:
            return float(row[key])
    return 0.0


def _run_list_opportunities(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    if stage := arguments.get("stage"):
        params["stage"] = stage

    payload = get_client().get("/crm/opportunities", params=params or None)
    rows = payload.get("data") or []

    if stage:
        count = len(rows)
        total = sum(_row_amount(row, "value_eur", "value") for row in rows)
    else:
        count, total = _compute_open_stats(rows)

    result = {
        "count": count,
        "total_value_eur": total,
        "opportunities_sample": rows[:SAMPLE_CAP],
        "note": (
            "Open opportunities use stages qualification and negotiation unless "
            "a specific stage filter was applied."
        ),
    }
    return json.dumps(result), "crm/opportunities"


def _run_list_customers(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if search := arguments.get("search"):
        params["search"] = search
    if channel := arguments.get("channel"):
        params["channel"] = channel
    if region := arguments.get("region"):
        params["region"] = region

    payload = get_client().get("/crm/customers", params=params or None)
    rows = payload.get("data") or []
    result = {
        "count": len(rows),
        "customers_sample": rows[:SAMPLE_CAP],
    }
    return json.dumps(result), "crm/customers"


def _run_list_orders(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    if status := arguments.get("status"):
        params["status"] = status
    if from_date := arguments.get("from"):
        params["from"] = from_date
    if to_date := arguments.get("to"):
        params["to"] = to_date

    payload = get_client().get("/crm/orders", params=params or None)
    rows = payload.get("data") or []
    total = sum(_row_amount(row, "total_value_eur", "value_eur", "value") for row in rows)
    result = {
        "count": len(rows),
        "total_value_eur": total,
        "orders_sample": rows[:SAMPLE_CAP],
    }
    return json.dumps(result), "crm/orders"


def _run_list_invoices(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    if status := arguments.get("status"):
        params["status"] = status
    if from_date := arguments.get("from"):
        params["from"] = from_date
    if to_date := arguments.get("to"):
        params["to"] = to_date

    payload = get_client().get("/crm/invoices", params=params or None)
    rows = payload.get("data") or []
    total = sum(_row_amount(row, "amount_eur", "total_amount", "amount") for row in rows)
    result = {
        "count": len(rows),
        "total_amount_eur": total,
        "invoices_sample": rows[:SAMPLE_CAP],
    }
    return json.dumps(result), "crm/invoices"


def run_crm_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    dispatch = {
        "list_opportunities": _run_list_opportunities,
        "list_customers": _run_list_customers,
        "list_orders": _run_list_orders,
        "list_invoices": _run_list_invoices,
    }
    handler = dispatch.get(name)
    if handler is None:
        raise ValueError(f"Unknown CRM tool: {name}")
    return handler(arguments)

"""CRM tools for the agent loop."""

from __future__ import annotations

import json
from typing import Any

from services.api_client import get_client

OPEN_STAGES = {"qualification", "negotiation"}

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
    }
]


def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def _compute_open_stats(rows: list[dict[str, Any]]) -> tuple[int, float]:
    open_rows = [row for row in rows if row.get("stage") in OPEN_STAGES]
    total = sum(float(row.get("value") or 0) for row in open_rows)
    return len(open_rows), total


def run_crm_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    if name != "list_opportunities":
        raise ValueError(f"Unknown CRM tool: {name}")

    params: dict[str, str] = {}
    if customer_id := arguments.get("customer_id"):
        params["customer_id"] = customer_id
    if stage := arguments.get("stage"):
        params["stage"] = stage

    payload = get_client().get("/crm/opportunities", params=params or None)
    rows = payload.get("data") or []

    if stage:
        count = len(rows)
        total = sum(float(row.get("value") or 0) for row in rows)
    else:
        count, total = _compute_open_stats(rows)

    result = {
        "count": count,
        "total_value_eur": total,
        "opportunities_sample": rows[:5],
        "note": (
            "Open opportunities use stages qualification and negotiation unless "
            "a specific stage filter was applied."
        ),
    }
    return json.dumps(result), "crm/opportunities"

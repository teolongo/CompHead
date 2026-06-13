"""LLM tool definitions and executors."""

from __future__ import annotations

import json
from typing import Any

from agent.tools import calls, crm, erp, kb

CRM_TOOLS = {definition["function"]["name"] for definition in crm.get_tool_definitions()}
ERP_TOOLS = {definition["function"]["name"] for definition in erp.get_tool_definitions()}
CALLS_TOOLS = {definition["function"]["name"] for definition in calls.get_tool_definitions()}
KB_TOOLS = {definition["function"]["name"] for definition in kb.get_tool_definitions()}

SUBMIT_ANSWER_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "submit_answer",
        "description": (
            "Submit the final answer to the user. Always call this as your last step "
            "after gathering data from other tools. Set verticale to the dominant "
            "data source used (crm, erp, calls, or kb)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Concise factual answer in English",
                },
                "verticale": {
                    "type": "string",
                    "enum": ["crm", "erp", "calls", "kb"],
                    "description": "Dominant data source for this answer",
                },
            },
            "required": ["answer", "verticale"],
            "additionalProperties": False,
        },
    },
}

VALID_VERTICALI = {"crm", "erp", "calls", "kb"}


def get_tool_definitions() -> list[dict[str, Any]]:
    return (
        crm.get_tool_definitions()
        + erp.get_tool_definitions()
        + calls.get_tool_definitions()
        + kb.get_tool_definitions()
        + [SUBMIT_ANSWER_TOOL]
    )


def run_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    if name == "submit_answer":
        return json.dumps(arguments), ""
    if name in CRM_TOOLS:
        return crm.run_crm_tool(name, arguments)
    if name in ERP_TOOLS:
        return erp.run_erp_tool(name, arguments)
    if name in CALLS_TOOLS:
        return calls.run_calls_tool(name, arguments)
    if name in KB_TOOLS:
        return kb.run_kb_tool(name, arguments)
    raise ValueError(f"Unknown tool: {name}")

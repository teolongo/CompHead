"""LLM tool definitions and executors."""

from __future__ import annotations

from typing import Any

from agent.tools import crm, erp

CRM_TOOLS = {definition["function"]["name"] for definition in crm.get_tool_definitions()}
ERP_TOOLS = {definition["function"]["name"] for definition in erp.get_tool_definitions()}


def get_tool_definitions() -> list[dict[str, Any]]:
    return crm.get_tool_definitions() + erp.get_tool_definitions()


def run_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    if name in CRM_TOOLS:
        return crm.run_crm_tool(name, arguments)
    if name in ERP_TOOLS:
        return erp.run_erp_tool(name, arguments)
    raise ValueError(f"Unknown tool: {name}")

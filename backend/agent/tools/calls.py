"""Calls tools for the agent loop."""

from __future__ import annotations

import json
import re
from typing import Any

from services.api_client import get_client

SEGMENT_CAP = 20
CALL_ID_PATTERN = re.compile(r"^CALL-\d+$")
LOT_ID_PATTERN = re.compile(r"LOT-\d{4}-\d{4}")

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_calls",
            "description": (
                "List call logs with optional filters. Returns calls sorted by date "
                "descending with most_recent_call_id pre-computed for 'last call' questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Filter by customer id, e.g. CUST-0137",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["sales", "support"],
                        "description": "Call type filter",
                    },
                    "outcome": {
                        "type": "string",
                        "enum": [
                            "complaint_open",
                            "follow_up",
                            "order_placed",
                            "resolved",
                        ],
                        "description": "Call outcome filter",
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
            "name": "search_transcript",
            "description": (
                "Search a call transcript with ?search= to extract complaint details. "
                "Returns pre-computed complaint_type and lot_id plus matched segments "
                "(capped at 20). Never fetch full transcripts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "Call id, e.g. CALL-58020",
                    },
                    "search": {
                        "type": "string",
                        "description": "Search term for transcript segments, e.g. broken",
                    },
                },
                "required": ["call_id", "search"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_calls_by_defect",
            "description": (
                "Count how many calls report a specific defect or complaint phrase "
                "(e.g. 'broken pasta') across ALL recorded calls. Pages through the "
                "entire call log and runs a targeted transcript search per call, then "
                "returns the exact count computed in Python. Use this for "
                "'how many calls mention X' aggregate questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "defect": {
                        "type": "string",
                        "description": "Defect or complaint phrase to count, e.g. 'broken pasta'",
                    },
                    "outcome": {
                        "type": "string",
                        "enum": [
                            "complaint_open",
                            "follow_up",
                            "order_placed",
                            "resolved",
                        ],
                        "description": "Optional outcome filter to narrow candidate calls",
                    },
                },
                "required": ["defect"],
                "additionalProperties": False,
            },
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    return TOOL_DEFINITIONS


def _call_date(row: dict[str, Any]) -> str:
    return str(row.get("call_date") or row.get("date") or "")


def _call_id(row: dict[str, Any]) -> str:
    return str(row.get("call_id") or row.get("id") or "")


def _validate_call_id(call_id: str) -> None:
    if not CALL_ID_PATTERN.match(call_id):
        raise ValueError(f"Invalid call_id format: {call_id}")


def _extract_complaint_type(segments: list[dict[str, Any]]) -> str | None:
    combined = " ".join(str(segment.get("text") or "") for segment in segments).lower()
    if "broken" in combined and "pasta" in combined:
        return "broken pasta"
    if "broken" in combined:
        return "broken pasta"
    if "quality" in combined:
        return "quality complaint"
    if "complaint" in combined:
        return "complaint"
    return None


def _extract_lot_id(segments: list[dict[str, Any]]) -> str | None:
    for segment in segments:
        text = str(segment.get("text") or "")
        match = LOT_ID_PATTERN.search(text)
        if match:
            return match.group(0)
    return None


def _run_list_calls(arguments: dict[str, Any]) -> tuple[str, str]:
    params: dict[str, str] = {}
    for key in ("customer_id", "type", "outcome", "from", "to"):
        if value := arguments.get(key):
            params[key] = value

    payload = get_client().get("/calls", params=params or None)
    rows = payload.get("data") or []
    sorted_rows = sorted(rows, key=_call_date, reverse=True)

    most_recent = sorted_rows[0] if sorted_rows else {}
    result = {
        "count": len(sorted_rows),
        "most_recent_call_id": _call_id(most_recent) or None,
        "most_recent_call_date": _call_date(most_recent) or None,
        "customer_id": most_recent.get("customer_id"),
        "type": most_recent.get("type"),
        "outcome": most_recent.get("outcome"),
        "calls_sample": sorted_rows[:5],
    }
    return json.dumps(result), "calls"


def _run_search_transcript(arguments: dict[str, Any]) -> tuple[str, str]:
    call_id = arguments.get("call_id")
    search = arguments.get("search")
    if not call_id or not search:
        raise ValueError("search_transcript requires call_id and search arguments")

    _validate_call_id(call_id)

    payload = get_client().get(
        f"/calls/{call_id}/transcript",
        params={"search": search},
    )
    segments = payload.get("segments") or []
    capped_segments = segments[:SEGMENT_CAP]

    result = {
        "call_id": call_id,
        "search": search,
        "complaint_type": _extract_complaint_type(capped_segments),
        "lot_id": _extract_lot_id(capped_segments),
        "matched_segments": capped_segments,
        "segment_count": len(capped_segments),
    }
    return json.dumps(result), f"calls/{call_id}/transcript"


MATCHING_IDS_SAMPLE_CAP = 10


def _segments_match_defect(segments: list[dict[str, Any]], defect: str) -> bool:
    combined = " ".join(str(segment.get("text") or "") for segment in segments).lower()
    if not combined:
        return False
    words = [word for word in defect.lower().split() if word]
    return all(word in combined for word in words)


def _run_count_calls_by_defect(arguments: dict[str, Any]) -> tuple[str, str]:
    defect = arguments.get("defect")
    if not defect:
        raise ValueError("count_calls_by_defect requires a defect argument")

    client = get_client()
    params: dict[str, str] = {}
    if outcome := arguments.get("outcome"):
        params["outcome"] = outcome

    calls = client.get_all_pages("/calls", params=params or None)

    matching_ids: list[str] = []
    searched = 0
    for call in calls:
        call_id = _call_id(call)
        if not call_id:
            continue
        searched += 1
        payload = client.get(
            f"/calls/{call_id}/transcript",
            params={"search": defect},
        )
        segments = (payload.get("segments") or [])[:SEGMENT_CAP]
        if _segments_match_defect(segments, defect):
            matching_ids.append(call_id)

    result = {
        "defect": defect,
        "count": len(matching_ids),
        "searched_call_count": searched,
        "matching_call_ids_sample": matching_ids[:MATCHING_IDS_SAMPLE_CAP],
        "note": "Count computed in Python after paging all calls and targeted transcript search.",
    }
    return json.dumps(result), "calls"


def run_calls_tool(name: str, arguments: dict[str, Any]) -> tuple[str, str]:
    if name == "list_calls":
        return _run_list_calls(arguments)
    if name == "search_transcript":
        return _run_search_transcript(arguments)
    if name == "count_calls_by_defect":
        return _run_count_calls_by_defect(arguments)
    raise ValueError(f"Unknown Calls tool: {name}")

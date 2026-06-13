"""Tool-calling agent loop for POST /ask."""

from __future__ import annotations

import json
import time
from typing import Any

from agent.artifacts import try_answer_artifact_preflight
from agent.correctness import try_answer_correctness_preflight
from agent.prompts import SYSTEM_PROMPT
from agent.tools import VALID_VERTICALI, get_tool_definitions, run_tool
from services.llm_client import get_llm_client, get_model

MAX_ITERATIONS = 5
LLM_MAX_RETRIES = 2
LLM_RETRY_BASE_SECONDS = 1.5
WALL_CLOCK_BUDGET_SECONDS = 24.0

_ANSWER_CACHE: dict[str, dict[str, Any]] = {}


def _deadline_exceeded(start: float) -> bool:
    return (time.monotonic() - start) >= WALL_CLOCK_BUDGET_SECONDS


def _timeout_answer(sources: list[str]) -> dict[str, Any]:
    return {
        "answer": (
            "I could not complete this answer within the time limit. "
            "Please try a more specific question or retry shortly."
        ),
        "sources": sources,
        "verticale": _infer_verticale(sources),
        "artifact_url": None,
    }


def _extract_message_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if content:
        return content.strip()
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        return reasoning.strip()
    return ""


def _infer_verticale(sources: list[str]) -> str:
    for source in sources:
        if source.startswith("crm/"):
            return "crm"
        if source.startswith("erp/"):
            return "erp"
        if source.startswith("calls"):
            return "calls"
        if source.startswith("DOC-"):
            return "kb"
    return "crm"


def _validate_verticale(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in VALID_VERTICALI:
        return normalized
    return "crm"


def _execute_tool(name: str, arguments: str) -> tuple[str, str]:
    args = json.loads(arguments) if arguments else {}
    return run_tool(name, args)


def _chat_completion(client: Any, **kwargs: Any) -> Any:
    last_error: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            if "429" not in message and "rate limit" not in message:
                raise
            if attempt == LLM_MAX_RETRIES - 1:
                break
            time.sleep(LLM_RETRY_BASE_SECONDS * (2**attempt))
    assert last_error is not None
    raise last_error


def run_agent(question: str) -> dict[str, Any]:
    normalized = question.strip()
    if normalized in _ANSWER_CACHE:
        return dict(_ANSWER_CACHE[normalized])

    preflight = try_answer_correctness_preflight(question)
    if preflight is not None:
        _ANSWER_CACHE[normalized] = preflight
        return preflight

    artifact = try_answer_artifact_preflight(question)
    if artifact is not None:
        _ANSWER_CACHE[normalized] = artifact
        return artifact

    sources: list[str] = []
    verticale = "crm"
    answer = ""
    started = time.monotonic()

    try:
        client = get_llm_client()
        model = get_model()
        tools = get_tool_definitions()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_ITERATIONS):
            if _deadline_exceeded(started):
                result = _timeout_answer(sources)
                _ANSWER_CACHE[normalized] = result
                return result

            response = _chat_completion(
                client,
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.function.name,
                                    "arguments": call.function.arguments,
                                },
                            }
                            for call in tool_calls
                        ],
                    }
                )
                submitted = False
                for call in tool_calls:
                    if _deadline_exceeded(started):
                        result = _timeout_answer(sources)
                        _ANSWER_CACHE[normalized] = result
                        return result
                    result, source = _execute_tool(
                        call.function.name,
                        call.function.arguments or "{}",
                    )
                    if call.function.name == "submit_answer":
                        payload = json.loads(result)
                        answer = str(payload.get("answer") or "").strip()
                        verticale = _validate_verticale(str(payload.get("verticale") or ""))
                        submitted = True
                    elif source and source not in sources:
                        sources.append(source)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": result,
                        }
                    )
                if submitted:
                    break
                continue

            answer = _extract_message_text(message)
            if answer:
                verticale = _infer_verticale(sources)
                break

        if not answer:
            answer = (
                "I could not produce an answer from the available tools. "
                "Please try rephrasing the question."
            )
            verticale = _infer_verticale(sources)

        result = {
            "answer": answer,
            "sources": sources,
            "verticale": verticale,
            "artifact_url": None,
        }
        _ANSWER_CACHE[normalized] = result
        return result
    except Exception as exc:
        result = {
            "answer": f"I cannot answer right now because of an error: {exc}",
            "sources": sources,
            "verticale": _infer_verticale(sources),
            "artifact_url": None,
        }
        return result

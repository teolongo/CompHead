"""Tool-calling agent loop for POST /ask."""

from __future__ import annotations

import json
import time
from typing import Any

from agent.prompts import SYSTEM_PROMPT
from agent.tools import VALID_VERTICALI, get_tool_definitions, run_tool
from services.llm_client import get_llm_client, get_model

MAX_ITERATIONS = 8
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_SECONDS = 2.0


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
    sources: list[str] = []
    verticale = "crm"
    answer = ""

    try:
        client = get_llm_client()
        model = get_model()
        tools = get_tool_definitions()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_ITERATIONS):
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

        return {
            "answer": answer,
            "sources": sources,
            "verticale": verticale,
            "artifact_url": None,
        }
    except Exception as exc:
        return {
            "answer": f"I cannot answer right now because of an error: {exc}",
            "sources": sources,
            "verticale": _infer_verticale(sources),
            "artifact_url": None,
        }

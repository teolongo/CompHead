"""Tool-calling agent loop for POST /ask."""

from __future__ import annotations

import json
from typing import Any

from agent.prompts import SYSTEM_PROMPT
from agent.tools import get_tool_definitions, run_tool
from services.llm_client import get_llm_client, get_model

MAX_ITERATIONS = 5


def _extract_message_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if content:
        return content.strip()
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        return reasoning.strip()
    return ""


def _execute_tool(name: str, arguments: str) -> tuple[str, str]:
    args = json.loads(arguments) if arguments else {}
    return run_tool(name, args)


def run_agent(question: str) -> dict[str, Any]:
    sources: list[str] = []
    verticale = "crm"

    try:
        client = get_llm_client()
        model = get_model()
        tools = get_tool_definitions()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        answer = ""
        for _ in range(MAX_ITERATIONS):
            response = client.chat.completions.create(
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
                for call in tool_calls:
                    result, source = _execute_tool(
                        call.function.name,
                        call.function.arguments or "{}",
                    )
                    if source not in sources:
                        sources.append(source)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": result,
                        }
                    )
                continue

            answer = _extract_message_text(message)
            if answer:
                break

        if not answer:
            answer = (
                "I could not produce an answer from the available tools. "
                "Please try rephrasing the question."
            )

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
            "verticale": verticale,
            "artifact_url": None,
        }

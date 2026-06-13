"""Frozen /ask contract tests (offline, no live env).

These tests pin the public POST /ask contract that the automated evaluator
depends on (AGENTS.md):

- Request body is a single ``{"question": str}`` object; nothing else required.
- Response is JSON with exactly the frozen keys ``answer``, ``sources``,
  ``verticale``, and ``artifact_url``.
- HTTP status is 200 for a normal answer, an honest "not available" answer,
  AND an exception fallback (never 4xx/5xx for "no info").
- No authentication header is required and the response is a single,
  non-streaming JSON object delivered in the first response.

They monkeypatch ``main.run_agent`` so they run fast and never touch the live
LLM or mock API services.
"""

from __future__ import annotations

import main
from fastapi.testclient import TestClient

SCHEMA_KEYS = {"answer", "sources", "verticale", "artifact_url"}
VALID_VERTICALI = {"crm", "erp", "calls", "kb"}

client = TestClient(main.app)


def _normal_result(question: str) -> dict:
    return {
        "answer": "Primato Supermercati S.p.A. has 4 open opportunities worth 740k.",
        "sources": ["crm/opportunities"],
        "verticale": "crm",
        "artifact_url": None,
    }


def _abstention_result(question: str) -> dict:
    return {
        "answer": "The profit margin is not available in the sources; ERP does not store it.",
        "sources": ["erp/production-orders"],
        "verticale": "erp",
        "artifact_url": None,
    }


def _raising_result(question: str) -> dict:
    raise RuntimeError("simulated provider outage")


def _assert_frozen_schema(payload: dict) -> None:
    assert set(payload.keys()) == SCHEMA_KEYS, payload
    assert isinstance(payload["answer"], str)
    assert isinstance(payload["sources"], list)
    assert all(isinstance(s, str) for s in payload["sources"])
    assert payload["verticale"] in VALID_VERTICALI
    assert payload["artifact_url"] is None or isinstance(payload["artifact_url"], str)


# --- Request shape -------------------------------------------------------


def test_ask_accepts_question_only(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _normal_result)
    response = client.post("/ask", json={"question": "How many open opportunities?"})
    assert response.status_code == 200
    _assert_frozen_schema(response.json())


def test_ask_rejects_missing_question() -> None:
    # An empty body is a client error (422), not a server error or a silent 200.
    response = client.post("/ask", json={})
    assert response.status_code == 422


def test_ask_ignores_extra_fields(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _normal_result)
    response = client.post(
        "/ask",
        json={"question": "How many open opportunities?", "stream": True, "token": "x"},
    )
    assert response.status_code == 200
    _assert_frozen_schema(response.json())


# --- HTTP 200 for every answer kind --------------------------------------


def test_normal_answer_is_200_with_frozen_schema(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _normal_result)
    response = client.post("/ask", json={"question": "How many open opportunities?"})
    assert response.status_code == 200
    payload = response.json()
    _assert_frozen_schema(payload)
    assert payload["verticale"] == "crm"
    assert payload["sources"] == ["crm/opportunities"]


def test_not_available_answer_is_200(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _abstention_result)
    response = client.post("/ask", json={"question": "What is the profit margin on lot LOT-1?"})
    assert response.status_code == 200
    payload = response.json()
    _assert_frozen_schema(payload)
    assert "not available" in payload["answer"].lower()


def test_exception_falls_back_to_200(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _raising_result)
    response = client.post("/ask", json={"question": "anything"})
    assert response.status_code == 200
    payload = response.json()
    _assert_frozen_schema(payload)
    assert payload["sources"] == []
    assert "cannot answer right now" in payload["answer"].lower()


# --- No auth, no streaming, single JSON object ---------------------------


def test_ask_requires_no_auth_header(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _normal_result)
    # No Authorization header is sent; the endpoint must still answer.
    response = client.post("/ask", json={"question": "How many open opportunities?"})
    assert response.status_code == 200
    assert "authorization" not in {k.lower() for k in response.request.headers}


def test_ask_returns_single_json_object_not_stream(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _normal_result)
    response = client.post("/ask", json={"question": "How many open opportunities?"})
    assert response.status_code == 200
    content_type = response.headers["content-type"]
    assert content_type.startswith("application/json")
    # A single parse yields the full object (no NDJSON / SSE chunks).
    payload = response.json()
    assert isinstance(payload, dict)


def test_ask_only_supports_post(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_agent", _normal_result)
    assert client.get("/ask").status_code == 405
    assert client.put("/ask", json={"question": "x"}).status_code == 405
